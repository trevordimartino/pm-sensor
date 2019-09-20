"""This module provides an abstraction for the SDS011 air partuclate densiry sensor.
Adapted from https://github.com/ikalchev/py-sds011/blob/master/sds011/__init__.py
"""

import logging
import struct
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

    logging.getLogger(__name__)

    def __init__(self, serial_port, baudrate=9600, timeout=2, use_query_mode=True):
        """Initialise and open serial port.
        """
        self.ser = serial.Serial(port=serial_port, baudrate=baudrate, timeout=timeout)
        self.ser.flush()
        self.default_timeout = timeout
        self.wake()
        self.reporting_mode = self.QUERY_MODE if use_query_mode else self.ACTIVE_MODE

    def _execute(self, cmd, id1=b'\xff', id2=b'\xff'):
        """Writes a byte sequence to the serial.
        """

        cmd += id1 + id2
        checksum = bytes([sum(d for d in cmd) % 256])
        cmd_bytes = self.HEAD + self.CMD_ID + cmd + checksum + self.TAIL

        logging.debug(f'Command: {cmd_bytes}')
        self.ser.write(cmd_bytes)

    def _get_reply(self, op_id=None, timeout=None):
        """Read reply from device."""

        if timeout:
            self.ser.timeout = timeout

        raw = self.ser.read(size=10)
        logging.debug(f'Reply: {raw}')
        if not raw:
            logging.warning('Device did not respond; try sending a .wake()?')
            return raw

        data = raw[2:8]
        if (sum(d for d in data) & 255) != raw[8]:
            raise IOError('Checksum did not match!')

        response_type = bytes([raw[1]])
        if response_type == self.DATA_RESPONSE:
            return self._decode_data(raw)

        if response_type == self.SETTING_RESPONSE:
            if not op_id:
                raise UserWarning('Set the op_id when calling ._get_reply() for additional sanity checking.')
            if op_id and bytes([raw[2]]) != op_id:
                raise IOError('Response does not match operation!')

        self.ser.timeout = self.default_timeout

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

        logging.debug(f'Processing frame: {raw}')
        pm25 = int.from_bytes(raw[2:4], byteorder='little') / 10.0
        pm10 = int.from_bytes(raw[4:6], byteorder='little') / 10.0
        return (pm25, pm10)

    @property
    def reporting_mode(self):
        cmd = self.REPORTING_MODE_SETTING + self.READ_SETTING + b'\x00' * 11
        self._execute(cmd)
        reply = self._get_reply(op_id=self.REPORTING_MODE_SETTING)
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
        return reply[4]

    def query(self):
        """Query the device and read the data.
        @return: Air particulate density in micrograms per cubic meter.
        @rtype: tuple(float, float) -> (PM2.5, PM10)
        """
        cmd = self.QUERY_DATA + b'\x00' * 12
        self._execute(cmd)
        return self._get_reply()

    def _sleep(self, mode, write=True):
        """Sleep/Wake up the sensor.
        @param sleep: Whether the device should sleep or work.
        @type sleep: bool
        """
        cmd = self.SLEEP_SETTING + (self.WRITE_SETTING if write else self.READ_SETTING) + mode + b'\x00' * 10
        self._execute(cmd)
        return self._get_reply(op_id=self.SLEEP_SETTING)

    def sleep(self):
        self._sleep(self.SLEEP_MODE)

    def wake(self):
        self._sleep(self.WORK_MODE)

    @property
    def work_period(self):
        cmd = self.WORK_PERIOD_SETTING + self.READ_SETTING + b'\x00' * 11
        self._execute(cmd)
        reply = self._get_reply(self.WORK_PERIOD_SETTING)
        return reply[4]

    @work_period.setter
    def work_period(self, work_time):
        """Get work period command. Does not contain checksum and tail.
        @rtype: list
        """
        if work_time < 0:
            work_time = self.CONTINUOUS_MODE
        if work_time > 30:
            logging.warn(f'Maximum work period is 30 minutes; received {work_time}, setting to 30.')
            work_time = 30

        cmd = self.WORK_PERIOD_SETTING + self.WRITE_SETTING + bytes([work_time]) + b'\x00' * 10
        self._execute(cmd)
        reply = self._get_reply(self.WORK_PERIOD_SETTING)
        return reply[4]

    def read(self):
        """Read sensor data.
        @return: PM2.5 and PM10 concetration in micrograms per cude meter.
        @rtype: tuple(float, float) - first is PM2.5.
        """
        timeout = self.work_period * 60 + 1
        return self._get_reply(timeout=timeout)
