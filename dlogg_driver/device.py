#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# python-dlogg-driver - Python package to read data from a D-LOGG device
# Copyright (C) 2017 U. Bruhin
# https://github.com/ubruhin/python-dlogg-driver
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import time
import serial
from definitions import *
import logging

log = logging.getLogger(__name__)


class DLoggDevice(object):

    def __init__(self, port):
        self._port = port
        self._serial = serial.Serial(port=self._port, baudrate=115200, timeout=1.0)
        self._serial.dtr = True
        self._serial.rts = False
        log.info("Opened port {}".format(self._port))
        mode = self.get_mode()
        log.info("Mode of connected device: {}".format(mode))
        if mode != Mode.ONE_DL:
            raise Exception("Mode is not supported")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._serial.close()
        log.info("Closed port {}".format(self._port))

    def get_type(self):
        data = self._transceive([0x20, 0x10, 0x18, 0x00, 0x00, 0x00, 0x00], 5, checksum=True)
        time.sleep(0.1)  # following commands will fail without this...
        if data[0] != 0x21 or data[1] != 0x43:
            raise IOError("Unexpected response")
        if sum(data[2:-1]) & 0xFF != data[-1]:
            raise IOError("Checksum mismatch")
        return Type(data[2])

    def get_firmware_version(self):
        data = self._transceive([Cmd.GET_FIRMWARE_VERSION], 1)
        return str(data[0] / 10.0)

    def get_mode(self):
        return Mode(self._transceive([Cmd.GET_MODE], 1)[0])

    def get_logging_criterion(self):
        data = self._transceive([Cmd.GET_LOGGING_CRITERION], 3)
        if data[0] != Cmd.GET_LOGGING_CRITERION:
            raise IOError("Unexpected response")
        return LoggingCriterion(data[1])

    def set_logging_criterion(self, criterion):
        data = self._transceive([Cmd.SET_LOGGING_CRITERION, criterion.raw], 1)
        if data[0] != criterion.raw:
            raise IOError("Unexpected response")

    def get_header(self):
        return OneDlHeader(self._transceive([Cmd.GET_HEADER], 13))

    def get_current_data(self):
        return Uvr1611CurrentData(self._transceive([Cmd.GET_CURRENT_DATA], 57))

    def fetch_data(self, address):
        tx_data = [Cmd.GET_DATA_RANGE]
        tx_data += address.array
        tx_data += [0x01]   # count of data frames to read
        return Uvr1611MemoryData(self._transceive(tx_data, 65, checksum=True))

    def fetch_data_range(self, start_addr, length):
        data = []
        for i in range(0, length):
            addr = OneDlAddress((start_addr.integer + i) % 8192)
            data.append(self.fetch_data(addr))
            log.debug("Fetched data from address {}".format(addr))
        return data

    def fetch_end(self):
        data = self._transceive([Cmd.END_READ], 1)
        if data[0] != Cmd.END_READ:
            raise IOError("Unexpected response")
        log.debug("Fetch end")

    def fetch_all_data(self):
        try:
            header = self.get_header()
            return self.fetch_data_range(header.start, header.get_sample_count())
        finally:
            self.fetch_end()

    def clear_memory(self):
        data = self._transceive([Cmd.CLEAR_MEMORY], 1)
        if data[0] != Cmd.CLEAR_MEMORY:
            raise IOError("Unexpected response")
        log.debug("Memory cleared")

    def _transceive(self, tx_data, rx_len, checksum=False):
        if checksum:
            tx_data += [sum(tx_data) % 0x100]
        self._serial.flushInput()
        self._serial.write(tx_data)
        rx_data = bytearray(self._serial.read(rx_len))
        log.debug("Transceive: {} --> {}".format([hex(c) for c in tx_data], [hex(c) for c in rx_data]))
        if len(rx_data) != rx_len:
            raise IOError("Received {} bytes instead of {}".format(len(rx_data), rx_len))
        return rx_data


if __name__ == "__main__":
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)

    with DLoggDevice("/dev/ttyUSB0") as device:
        log.info(u"Type: {}".format(device.get_type()))
        log.info(u"Firmware: {}".format(device.get_firmware_version()))
        log.info(u"Mode: {}".format(device.get_mode()))
        logging_criterion = device.get_logging_criterion()
        log.info(u"Logging criterion: {}".format(unicode(logging_criterion)))
        device.set_logging_criterion(logging_criterion)
        header = device.get_header()
        log.info(u"Header: {}".format(unicode(header)))
        log.info(u"Number of samples: {}".format(header.get_sample_count()))
        log.info(u"Current data: {}".format(unicode(device.get_current_data())))
        log.info(u"Data 0: {}".format(unicode(device.fetch_data(header.start))))
        # all_data = device.fetch_data_range(header.start, header.get_sample_count())
        # log.info(u"Fetched {} samples".format(header.get_sample_count()))
        device.fetch_end()
        # device.clear_memory()
