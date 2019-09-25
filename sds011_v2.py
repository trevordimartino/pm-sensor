"""This module provides an abstraction for the SDS011 air partuclate densiry sensor.
Adapted from https://github.com/ikalchev/py-sds011/blob/master/sds011/__init__.py
"""

import logging
import serial


class SDS011(object):
    """Provides method to read from a SDS011 air particlate density sensor
    using UART.
    """

    HEAD = b'\xaa'
    CMD_ID = b'\xb4'
    TAIL = b'\xab'

    # Operation IDs
    REPORTING_MODE_SETTING = b'\x02'
    QUERY_DATA = b'\x04'
    SET_DEVICE_ID = b'\x05'
    SLEEP_SETTING = b'\x06'
    WORK_PERIOD_SETTING = b'\x08'

    READ_SETTING = b'\x00'
    WRITE_SETTING = b'\x01'

    # Settings for REPORTING_MODE_SETTING
    ACTIVE_MODE = b'\x00'
    QUERY_MODE = b'\x01'

    # Settings for SLEEP_SETTING
    SLEEP_MODE = b'\x00'
    WORK_MODE = b'\x01'

    # Settings for WORK_PERIOD_SETTING
    CONTINUOUS_MODE = b'\x00'

    # Response types
    SETTING_RESPONSE = b'\xc5'
    DATA_RESPONSE = b'\xc0'

    logger = logging.getLogger(__name__)

    def __init__(self, serial_port, baudrate=9600, timeout=2, use_query_mode=True, work_period=0):
        self.ser = serial.Serial(port=serial_port, baudrate=baudrate, timeout=timeout)
        self.ser.flush()
        self.default_timeout = timeout
        self.wake()
        self.work_period = work_period
        self.reporting_mode = self.QUERY_MODE if use_query_mode else self.ACTIVE_MODE

    def _execute(self, cmd, id1=b'\xff', id2=b'\xff'):
        """Writes a byte sequence to the serial."""

        cmd += id1 + id2
        checksum = bytes([sum(d for d in cmd) % 256])
        cmd_bytes = self.HEAD + self.CMD_ID + cmd + checksum + self.TAIL

        self.logger.debug(f'Command: {cmd_bytes}')
        self.ser.write(cmd_bytes)

    def _get_reply(self, op_id=None, timeout=None):
        """Read reply from device.
        kwarg `op_id` defaults to `None`, meaning we expect a data reply
        """

        if timeout:
            self.ser.timeout = timeout
        raw = self.ser.read(size=10)
        self.ser.timeout = self.default_timeout

        self.logger.debug(f'Reply: {raw}')
        if not raw:
            self.logger.warning('Device did not respond; try sending a .wake()?')
            return raw

        data = raw[2:8]
        if (sum(d for d in data) & 255) != raw[8]:
            raise IOError('Checksum invalid!')

        response_type = bytes([raw[1]])
        if response_type == self.DATA_RESPONSE:
            if not op_id:
                return self._decode_data(raw)
            # op_id was set, so we weren't expecting data; grab the next reply
            return self._get_reply(op_id=op_id)

        if response_type == self.SETTING_RESPONSE:
            if not op_id:
                self.logger.warning('Set the op_id when calling ._get_reply() for additional sanity checking.')
            if op_id and bytes([raw[2]]) != op_id:
                raise IOError('Response does not match operation!')

        return raw

    def _decode_data(self, raw):
        """Process a SDS011 data frame.
        Byte positions:
            0 - Header
            1 - Command ID
            2,3 - PM2.5 low/high bytes
            4,5 - PM10 low/high bytes
            6,7 - Device ID bytes
            8 - Checksum - low byte of sum of bytes 2-7
            9 - Tail
        """

        self.logger.debug(f'Processing frame: {raw}')
        pm25 = int.from_bytes(raw[2:4], byteorder='little') / 10.0
        pm10 = int.from_bytes(raw[4:6], byteorder='little') / 10.0
        return (pm25, pm10)

    @property
    def reporting_mode(self):
        cmd = self.REPORTING_MODE_SETTING + self.READ_SETTING + b'\x00' * 11
        self._execute(cmd)
        reply = self._get_reply(op_id=self.REPORTING_MODE_SETTING)
        self.logger.debug(f'Reporting mode read: {reply[4]}')
        if bytes([reply[4]]) == self.QUERY_MODE:
            return 'sensor.QUERY_MODE'
        return 'sensor.ACTIVE_MODE'

    @reporting_mode.setter
    def reporting_mode(self, mode):
        if mode != self.ACTIVE_MODE and mode != self.QUERY_MODE:
            raise ValueError('Reporting mode must either be 0 (.ACTIVE_MODE) or 1 (.QUERY_MODE).')

        cmd = self.REPORTING_MODE_SETTING + self.WRITE_SETTING + mode + b'\x00' * 10
        self._execute(cmd)
        reply = self._get_reply(op_id=self.REPORTING_MODE_SETTING)
        self.logger.debug(f'Reporting mode set: {reply[4]}')
        return reply[4]

    def query(self):
        """Query the sensor to read the data.
        @return: Air particulate density in micrograms per cubic meter.
        @rtype: tuple(float, float) -> (PM2.5, PM10)
        """
        cmd = self.QUERY_DATA + b'\x00' * 12
        self._execute(cmd)
        return self._get_reply()

    def _sleep(self, mode, write=True):
        cmd = self.SLEEP_SETTING + (self.WRITE_SETTING if write else self.READ_SETTING) + mode + b'\x00' * 10
        self._execute(cmd)
        return self._get_reply(op_id=self.SLEEP_SETTING)

    def sleep(self):
        return self._sleep(self.SLEEP_MODE)

    def wake(self):
        attempts = 0
        awake = self._sleep(self.WORK_MODE)
        if not awake and attempts < 5:
            attempts += 1
            self.logger.debug(f'Attempted to .wake() {attempts} time(s), trying again.')
            awake = self._sleep(self.WORK_MODE)
        elif not awake:
            self.logger.error('Device has not awoken after 5 attempts.')
            return

        return awake

    @property
    def work_period(self):
        cmd = self.WORK_PERIOD_SETTING + self.READ_SETTING + b'\x00' * 11
        self._execute(cmd)
        reply = self._get_reply(self.WORK_PERIOD_SETTING)
        self.logger.debug(f'Work period read: {reply[4]}')
        return reply[4]

    @work_period.setter
    def work_period(self, work_time):
        if work_time < 0:
            work_time = self.CONTINUOUS_MODE
        if work_time > 30:
            self.logger.warn(f'Maximum work period is 30 minutes; received {work_time}, setting to 30.')
            work_time = 30

        cmd = self.WORK_PERIOD_SETTING + self.WRITE_SETTING + bytes([work_time]) + b'\x00' * 10
        self._execute(cmd)
        reply = self._get_reply(self.WORK_PERIOD_SETTING)
        self.logger.debug(f'Work period set: {reply[4]}')
        return reply[4]

    def read(self):
        """Wait for sensor to report a reading; a passive .query()"""

        if self.reporting_mode == 'sensor.QUERY_MODE':
            return self.query()

        timeout = self.work_period * 60 + 1
        self.logger.debug(f'Waiting for a measurement for {timeout} seconds...')
        return self._get_reply(timeout=timeout)
