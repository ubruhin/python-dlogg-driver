#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# python-dlogg - Python package to read data from a D-LOGG module
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
from enum import Enum
from struct import unpack
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Cmd(int):
    GET_MODE = 0x81
    GET_HEADER = 0xAA
    GET_CURRENT_DATA = 0xAB
    GET_DATA_RANGE = 0xAC
    END_READ = 0xAD
    CLEAR_MEMORY = 0xAF


class Mode(Enum):
    ONE_DL = 0xA8
    TWO_DL = 0xD1
    CAN = 0xDC


class UvrType(Enum):
    UVR61_3 = 0x5A
    UVR1611 = 0x76


class OneDlAddress(object):  # TODO is the conversion between byte array and integer really correct?!
    def __init__(self, addr):
        if isinstance(addr, int):
            self.array = [(addr << 6) & 0xFF, (addr >> 1) & 0xFE, (addr >> 9) & 0xFF]
            self.integer = addr
        else:
            self.array = addr
            self.integer = (addr[0] >> 6) + (addr[1] << 1) + (addr[2] << 9)

    def __str__(self):
        return str(self.integer)

    @staticmethod
    def calc_length(start, end):
        if end.integer >= start.integer:
            return end.integer - start.integer + 1
        else:
            return end.integer - start.integer + 8192 + 1


class OneDlHeader(object):
    def __init__(self, raw_data):
        self.identifier = raw_data[0]
        self.version = raw_data[1]
        self.timestamp = unpack("<I", raw_data[2:5] + bytearray([0]))[0]
        # self.length = raw_data[5]
        self.start = OneDlAddress(raw_data[6:9])
        self.end = OneDlAddress(raw_data[9:12])
        checksum = raw_data[12]
        checksum_calc = sum(raw_data[0:12]) % 0x100
        if checksum != checksum_calc:
            raise IOError("Checksum mismatch in header")

    def get_sample_count(self):
        return OneDlAddress.calc_length(self.start, self.end)

    def __str__(self):
        str = "{\n"
        str += "  identifier: {}\n".format(self.identifier)
        str += "  version:    {}\n".format(self.version)
        str += "  timestamp:  {}\n".format(self.timestamp)
        # str += "  length:     {}\n".format(self.length)
        str += "  start:      {}\n".format(self.start)
        str += "  end:        {}\n".format(self.end)
        str += "}"
        return str


if __name__ == "__main__":
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)

    for i in range(0, 8192):
        addr_1 = OneDlAddress(i)
        addr_2 = OneDlAddress(addr_1.array)
        if addr_2.integer != addr_1.integer:
            raise Exception("Integer mismatch at {}: {} != {}".format(i, addr_1.integer, addr_2.integer))
        if addr_2.array != addr_1.array:
            raise Exception("Array mismatch at {}: {} != {}".format(i, addr_1.array, addr_2.array))

    def next_address_of_old_algorithm(addr):
        next_addr = list(addr)
        if next_addr[0] <= 0x80:
            next_addr[0] += 0x40
        else:
            next_addr[0] = 0x00
            if next_addr[1] != 0xFE:
                next_addr[1] += 0x02
            else:
                next_addr[1] = 0x00
                next_addr[2] += 0x01
                if next_addr[2] > 0x0F:
                    next_addr = [0x00, 0x00, 0x00]
        return next_addr

    addr = [0x80, 0xCE, 0x00]
    for i in range(0, 8192):
        old = next_address_of_old_algorithm(addr)
        new = OneDlAddress(OneDlAddress(addr).integer + 1).array
        if new == old:
            log.info("{}: {} --> {}".format(i, addr, new))
        else:
            raise Exception("Address mismatch at {}: {} != {}".format(i, new, old))
