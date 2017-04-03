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
    GET_FIRMWARE_VERSION = 0x82
    GET_LOGGING_CRITERION = 0x95
    SET_LOGGING_CRITERION = 0x96
    GET_HEADER = 0xAA
    GET_CURRENT_DATA = 0xAB
    GET_DATA_RANGE = 0xAC
    END_READ = 0xAD
    CLEAR_MEMORY = 0xAF


class Type(Enum):
    BL232 = 0xA2
    BLNET = 0xA3
    BL232_DLOGG_1DL = 0xA8
    BL232_DLOGG_2DL = 0xD1


class Mode(Enum):
    BL232 = 0xA2
    ONE_DL = 0xA8
    TWO_DL = 0xD1
    CAN = 0xDC


#class ControllerDeviceType(Enum):
#    UVR61_3 = 0x5A
#    UVR1611 = 0x76


class LoggingCriterion(object):
    def __init__(self, raw_data):
        self.raw = raw_data
        if 5 <= raw_data <= 120:
            self.temperature_difference_k = raw_data / 10.0
            self.time_interval_s = None
        elif 129 <= raw_data <= 248:
            self.temperature_difference_k = None
            self.time_interval_s = (raw_data - 128) * 20.0
        else:
            raise Exception("Invalid logging criterion")

    def __str__(self):
        if self.temperature_difference_k:
            return "{}K".format(self.temperature_difference_k)
        else:
            return "{}s".format(self.time_interval_s)


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
        self.timestamp_s = unpack("<I", raw_data[2:5] + bytearray([0]))[0] * 10
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
        str += "  identifier: 0x{:02X}\n".format(self.identifier)
        str += "  version:    0x{:02X}\n".format(self.version)
        str += "  timestamp:  {}s\n".format(self.timestamp_s)
        # str += "  length:     {}\n".format(self.length)
        str += "  start:      {}\n".format(self.start)
        str += "  end:        {}\n".format(self.end)
        str += "}"
        return str


class DateTime(object):
    def __init__(self, raw_data):
        self.seconds = raw_data[0]
        self.minutes = raw_data[1]
        self.hours = raw_data[2]
        self.day = raw_data[3]
        self.month = raw_data[4]
        self.year = 2000 + raw_data[5]

    def __str__(self):
        return "{}-{}-{}_{}:{}:{}".format(self.year, self.month, self.day,
                                          self.hours, self.minutes, self.seconds)


class InputData(object):
    def __init__(self, raw_data):
        self.type = raw_data[1] >> 4
        self.raw_value = (unpack("<h", raw_data)[0] & 0x0FFF)
        if self.type == 0:  # not used (?)
            self.value = 0
            self.unit = ""
        elif self.type == 2 or self.type == 7:  # temperature
            self.value = self.raw_value / 10.0
            self.unit = "°C"
        elif self.type == 10 or self.type == 15:  # minus temperature
            self.value = self.raw_value / -10.0
            self.unit = "°C"
        elif self.type == 3:  # volume per time
            self.value = self.raw_value * 4.0
            self.unit = "l/h"
        else:
            raise Exception("Unknown input type: {}".format(self.type))

    def __str__(self):
        # return "[{}] {} -> {}{}".format(self.type, self.raw_value, self.value, self.unit)
        return "{}{}".format(self.value, self.unit)


class PumpSpeed(object):
    def __init__(self, raw_data):
        self.value = raw_data & 0x1F
        self.unit = 'rpm'

    def __str__(self):
        return "{}{}".format(self.value, self.unit)


class Uvr1611Data(object):
    def __init__(self, raw_data):
        self.raw = bytearray(raw_data)
        self.inputs = list()
        for i in range(0, 16):
            self.inputs.append(InputData(raw_data[i*2:i*2+2]))
        self.outputs = list()
        for i in range(0, 13):
            self.outputs.append(True if unpack("<H", raw_data[32:34])[0] & 1 << i else False)
        self.pump_speeds = list()
        for i in range(0, 4):
            self.pump_speeds.append(PumpSpeed(raw_data[34+i]))
        # self.wmz_active = raw_data[38]
        # self.solar_1_power = unpack(">I", raw_data[39:43])
        # self.solar_1_kwh = unpack(">H", raw_data[43:45])
        # self.solar_1_mwh = unpack(">H", raw_data[45:47])
        # self.solar_2_power = unpack(">I", raw_data[47:51])
        # self.solar_2_kwh = unpack(">H", raw_data[51:53])
        # self.solar_2_mwh = unpack(">H", raw_data[53:55])
        self.datetime = DateTime(raw_data[55:61])
        self.timestamp_s = unpack("<I", raw_data[61:64] + bytearray([0]))[0] * 10
        checksum = raw_data[64]
        checksum_calc = sum(raw_data[0:64]) % 0x100
        if checksum != checksum_calc:
            raise IOError("Checksum mismatch in header")

    def __str__(self):
        str = "{\n"
        str += "  datetime:     {}\n".format(self.datetime)
        str += "  timestamp:    {}s\n".format(self.timestamp_s)
        str += "  inputs:       {}\n".format([x.value for x in self.inputs])
        str += "  outputs:      {}\n".format([x for x in self.outputs])
        str += "  pump_speeds:  {}\n".format([x.value for x in self.pump_speeds])
        # str += "  wmz_active: {}\n".format(self.wmz_active)
        # str += "  solar_1_power: {}\n".format(self.solar_1_power)
        # str += "  solar_1_kwh: {}\n".format(self.solar_1_kwh)
        # str += "  solar_1_mwh: {}\n".format(self.solar_1_mwh)
        # str += "  solar_2_power: {}\n".format(self.solar_2_power)
        # str += "  solar_2_kwh: {}\n".format(self.solar_2_kwh)
        # str += "  solar_2_mwh: {}\n".format(self.solar_2_mwh)
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
