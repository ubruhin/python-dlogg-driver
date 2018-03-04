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
from enum import Enum
from struct import unpack
import logging

log = logging.getLogger(__name__)


class Cmd(int):
    GET_MODE = 0x81
    GET_FIRMWARE_VERSION = 0x82
    GET_LOGGING_CRITERION = 0x95  # requires firmware version >= 2.9!
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

    def __unicode__(self):
        if self.temperature_difference_k:
            return u"{}K".format(self.temperature_difference_k)
        else:
            return u"{}s".format(self.time_interval_s)


class OneDlAddress(object):  # TODO is the conversion between byte array and integer really correct?!
    def __init__(self, addr):
        if isinstance(addr, int):
            self.array = bytearray([(addr << 6) & 0xFF, (addr >> 1) & 0xFE, (addr >> 9) & 0xFF])
            self.integer = addr
        else:
            self.array = addr
            self.integer = (addr[0] >> 6) + (addr[1] << 1) + (addr[2] << 9)

    def __unicode__(self):
        return unicode(self.integer)

    @staticmethod
    def calc_length(start, end):
        if end.array == start.array == bytearray([0xFF, 0xFF, 0xFF]):
            return 0
        elif end.integer >= start.integer:
            return end.integer - start.integer + 1
        else:
            return end.integer - start.integer + 8192 + 1


class OneDlHeader(object):
    def __init__(self, raw_data):
        self.raw = bytearray(raw_data)
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

    def __unicode__(self):
        text = u"{\n"
        text += u"  identifier: 0x{:02X}\n".format(self.identifier)
        text += u"  version:    0x{:02X}\n".format(self.version)
        text += u"  timestamp:  {}s\n".format(self.timestamp_s)
        # text += u"  length:     {}\n".format(self.length)
        text += u"  start:      {}\n".format(self.start)
        text += u"  end:        {}\n".format(self.end)
        text += u"}"
        return text


class DateTime(object):
    def __init__(self, raw_data):
        self.seconds = raw_data[0]
        self.minutes = raw_data[1]
        self.hours = raw_data[2]
        self.day = raw_data[3]
        self.month = raw_data[4]
        self.year = 2000 + raw_data[5]

    def __unicode__(self):
        return u"{}-{}-{}_{}:{}:{}".format(self.year, self.month, self.day,
                                           self.hours, self.minutes, self.seconds)


class InputDataSignalType(Enum):
    UNUSED = 0
    DIGITAL = 1
    TEMPERATURE = 2
    MASSFLOW = 3
    SUNLOAD = 6
    ROOM_TEMPERATURE = 7


class InputData(object):
    def __init__(self, raw_data):
        self.type = raw_data[1] >> 4
        word = unpack("<h", raw_data)[0]
        self.type = InputDataSignalType((word & 0x7000) >> 12)
        if self.type == InputDataSignalType.UNUSED:
            self.value = 0
            self.unit = u""
        elif self.type == InputDataSignalType.DIGITAL:
            self.value = 1 if word & 0x8000 else 0
            self.unit = u""
        elif self.type == InputDataSignalType.TEMPERATURE:
            if word & 0x8000:
                self.value = (((word & 0x0FFF) ^ 0x0FFF) + 0x01) / -10.0
            else:
                self.value = (word & 0x0FFF) / 10.0
            self.unit = u"°C"
        elif self.type == InputDataSignalType.ROOM_TEMPERATURE:
            self.room = (word & 0x600) >> 9
            if word & 0x8000:
                self.value = (((word & 0x01FF) ^ 0x01FF) + 0x01) / -10.0
            else:
                self.value = (word & 0x01FF) / 10.0
            self.unit = u"°C"
        elif self.type == InputDataSignalType.MASSFLOW:
            if word & 0x8000:
                self.value = (((word & 0x0FFF) ^ 0x0FFF) + 0x01) * -4.0
            else:
                self.value = (word & 0x0FFF) * 4.0
            self.unit = u"l/h"
        elif self.type == InputDataSignalType.SUNLOAD:
            if word & 0x8000:
                self.value = -(((word & 0x0FFF) ^ 0x0FFF) + 0x01)
            else:
                self.value = (word & 0x0FFF)
            self.unit = u"W/m²"
        else:
            raise Exception("Unknown input type: {}".format(self.type))

    def __unicode__(self):
        return u"{}{}".format(self.value, self.unit)


class PumpSpeed(object):
    def __init__(self, raw_data):
        self.controller_active = False if raw_data & 0x80 else True  # TODO: is this correct?!
        self.value = raw_data & 0x1F
        self.unit = u'rpm'

    def __unicode__(self):
        return u"[{}] {}{}".format(self.controller_active, self.value, self.unit)


class Uvr1611Data(object):
    def __init__(self, raw_data, offset):
        self.raw = bytearray(raw_data)
        data = raw_data[offset:]
        self.inputs = list()
        for i in range(0, 16):
            self.inputs.append(InputData(data[i*2:i*2+2]))
        self.outputs = list()
        for i in range(0, 13):
            self.outputs.append(True if unpack("<H", data[32:34])[0] & 1 << i else False)
        self.pump_speeds = list()
        for i in range(0, 4):
            self.pump_speeds.append(PumpSpeed(data[34+i]))
        # self.wmz_active = raw_data[38]
        # self.solar_1_power = unpack(">I", raw_data[39:43])
        # self.solar_1_kwh = unpack(">H", raw_data[43:45])
        # self.solar_1_mwh = unpack(">H", raw_data[45:47])
        # self.solar_2_power = unpack(">I", raw_data[47:51])
        # self.solar_2_kwh = unpack(">H", raw_data[51:53])
        # self.solar_2_mwh = unpack(">H", raw_data[53:55])
        checksum = raw_data[-1]
        checksum_calc = sum(raw_data[0:-1]) & 0xFF
        if checksum != checksum_calc:
            raise IOError("Checksum mismatch in header")

    def __unicode__(self):
        text = u"{\n"
        text += u"  inputs:       {}\n".format(u", ".join([unicode(x) for x in self.inputs]))
        text += u"  outputs:      {}\n".format(u", ".join([unicode(x) for x in self.outputs]))
        text += u"  pump_speeds:  {}\n".format(u", ".join([unicode(x) for x in self.pump_speeds]))
        # text += u"  wmz_active: {}\n".format(self.wmz_active)
        # text += u"  solar_1_power: {}\n".format(self.solar_1_power)
        # text += u"  solar_1_kwh: {}\n".format(self.solar_1_kwh)
        # text += u"  solar_1_mwh: {}\n".format(self.solar_1_mwh)
        # text += u"  solar_2_power: {}\n".format(self.solar_2_power)
        # text += u"  solar_2_kwh: {}\n".format(self.solar_2_kwh)
        # text += u"  solar_2_mwh: {}\n".format(self.solar_2_mwh)
        return text


class Uvr1611CurrentData(Uvr1611Data):
    def __init__(self, raw_data):
        Uvr1611Data.__init__(self, raw_data, offset=1)
        if raw_data[0] != 0x80:
            raise IOError("Unexpected data")


class Uvr1611MemoryData(Uvr1611Data):
    def __init__(self, raw_data):
        Uvr1611Data.__init__(self, raw_data, offset=0)
        self.datetime = DateTime(raw_data[55:61])
        self.timestamp_s = unpack("<I", raw_data[61:64] + bytearray([0]))[0] * 10

    def __unicode__(self):
        text = Uvr1611Data.__unicode__(self)
        text += u"  datetime:     {}\n".format(self.datetime)
        text += u"  timestamp:    {}s\n".format(self.timestamp_s)
        text += u"}"
        return text


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
