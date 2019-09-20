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
        self.reporting_mode(self.QUERY_MODE if use_query_mode else self.ACTIVE_MODE)

    def _execute(self, cmd):
        """Writes a byte sequence to the serial.
        """
        cmd_bytes = self._wrap_cmd(cmd)
        logging.debug(f'Command: {cmd_bytes}')
        self.ser.write(cmd_bytes)

    def _wrap_cmd(self, cmd, id1=b'\xff', id2=b'\xff'):
        """Get command header and command ID bytes.
        @rtype: list
        """
        cmd += id1 + id2
        checksum = bytes([sum(d for d in cmd) % 256])
        return self.HEAD + self.CMD_ID + cmd + checksum + self.TAIL

    def _get_reply(self, op_id=None):
        """Read reply from device."""
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

    def reporting_mode(self, mode, write=True):
        """Get sleep command. Does not contain checksum and tail.
        @rtype: list
        """
        cmd = self.REPORTING_MODE_SETTING + (self.WRITE_SETTING if write else self.READ_SETTING) + mode + b'\x00' * 10
        self._execute(cmd)
        return self._get_reply(op_id=self.REPORTING_MODE_SETTING)

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

    def work_period(self, work_time, write=True):
        """Get work period command. Does not contain checksum and tail.
        @rtype: list
        """
        if work_time < 0:
            work_time = self.CONTINUOUS_MODE
        if work_time > 30:
            raise ValueError('Working period must not be greater than 30 (minutes).')
        cmd = self.WORK_PERIOD_SETTING + (self.WRITE_SETTING if write else self.READ_SETTING) + bytes([work_time]) + b'\x00' * 10
        self._execute(cmd)
        return self._get_reply(self.WORK_PERIOD_SETTING)

    def read(self):
        """Read sensor data.
        @return: PM2.5 and PM10 concetration in micrograms per cude meter.
        @rtype: tuple(float, float) - first is PM2.5.
        """
        byte = 0
        while byte != self.HEAD:
            byte = self.ser.read(size=1)
            d = self.ser.read(size=10)
            if d[0:1] == b'\xc0':
                data = self._process_frame(byte + d)
                return data
