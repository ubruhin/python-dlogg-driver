#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# python-dlogg - Python package to read data from a USB D-LOGG module
# Copyright (C) 2017 U. Bruhin
# https://github.com/ubruhin/python-dlogg
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
log.setLevel(logging.DEBUG)


class DLoggModule(object):

    def __init__(self, port):
        self._port = port
        self._serial = serial.Serial(port=self._port, baudrate=115200, timeout=5.0)
        log.info("Opened port {}".format(self._port))
        mode = self.get_mode()
        log.info("Mode of connected module: {}".format(mode))
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
        data = self._transceive([0x20, 0x10, 0x18, 0x00, 0x00, 0x00, 0x00], 5, add_checksum=True)
        if data[0] != 0x21 or data[1] != 0x43:
            raise IOError("Unexpected response")
        return data[3]

    def get_mode(self):
        return Mode(self._transceive([Cmd.GET_MODE], 1)[0])

    def get_header(self):
        time.sleep(0.1)  # reading the header does not work without this...
        return OneDlHeader(self._transceive([Cmd.GET_HEADER], 13))

    # def get_current_data(self):
    #     data = self._transceive([Cmd.GET_CURRENT_DATA], 57)
    #     if data[0] != 0x80:
    #         raise IOError("Unexpected response")
    #     return data

    def fetch_data(self, address):
        tx_data = [Cmd.GET_DATA_RANGE]
        tx_data += address.array
        tx_data += [0x01]   # count of data frames to read(?)
        return Uvr1611Data(self._transceive(tx_data, 65, add_checksum=True))

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

    def clear_memory(self):
        data = self._transceive([Cmd.CLEAR_MEMORY], 1)
        if data[0] != Cmd.CLEAR_MEMORY:
            raise IOError("Unexpected response")
        log.debug("Memory cleared")

    def _transceive(self, tx_data, rx_len, add_checksum=False):
        if add_checksum:
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

    with DLoggModule("/dev/ttyUSB0") as device:
        log.info("Mode: {}".format(device.get_mode()))
        log.info("Type: {}".format(device.get_type()))
        header = device.get_header()
        log.info("Header: {}".format(header))
        log.info("Number of samples: {}".format(header.get_sample_count()))
        # log.info("Current data: {}".format(device.get_current_data()))
        log.info("Data 0: {}".format(device.fetch_data(header.start)))
        device.fetch_end()
        #device.clear_memory()
        # all_data = device.fetch_data_range(header.start, header.get_sample_count())
        # log.info("Fetched {} samples".format(header.get_sample_count()))
