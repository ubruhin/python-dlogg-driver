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
from dlogg import DLoggModule
from dlogg.definitions import *
from binascii import hexlify
import MySQLdb as mdb
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class DLoggDbUpload(object):

    def __init__(self, db_host, db_port, db_name, db_user, db_pw):
        self._db = mdb.connect(host=db_host, port=db_port, user=db_user,
                               passwd=db_pw, db=db_name, charset='utf8')
        log.info("Opened database {} on host {}".format(db_name, db_host))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._db.close()
        log.info("Closed database")

    def create_tables(self):
        with self._db:
            cur = self._db.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS data '
                        '(`id` INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL) '
                        'DEFAULT CHARACTER SET = utf8 COLLATE = utf8_bin')
            cur.execute('ALTER TABLE data ADD IF NOT EXISTS inserted DATETIME DEFAULT CURRENT_TIMESTAMP')
            cur.execute('ALTER TABLE data ADD IF NOT EXISTS raw BLOB NOT NULL')
            cur.execute('ALTER TABLE data ADD IF NOT EXISTS datetime DATETIME')
            cur.execute('ALTER TABLE data ADD IF NOT EXISTS timestamp INTEGER')
            for i in range(0, 16):
                cur.execute("ALTER TABLE data ADD IF NOT EXISTS input_{} DOUBLE".format(i + 1))
                cur.execute("ALTER TABLE data ADD IF NOT EXISTS input_unit_{} TEXT".format(i + 1))
            for i in range(0, 13):
                cur.execute("ALTER TABLE data ADD IF NOT EXISTS output_{} BOOLEAN".format(i + 1))
            for i in range(0, 4):
                cur.execute("ALTER TABLE data ADD IF NOT EXISTS pump_speed_{} DOUBLE".format(i + 1))
                cur.execute("ALTER TABLE data ADD IF NOT EXISTS pump_speed_unit_{} TEXT".format(i + 1))
        log.info("Database tables created/updated")

    def insert_data(self, data):
        with self._db:
            cur = self._db.cursor()
            for item in data:
                log.info("Data: {}".format(item))
                self._insert_data(item, cur)
        log.info("Added {} samples to database".format(len(data)))

    @staticmethod
    def _insert_data(data, cur):
        columns = []
        values = []
        dt = data.datetime
        columns.append("raw")
        values.append("'{}'".format(hexlify(data.raw)))
        columns.append("datetime")
        values.append("'{}-{}-{} {}:{}:{}'".format(dt.year, dt.month, dt.day, dt.hours, dt.minutes, dt.seconds))
        columns.append("timestamp")
        values.append("'{}'".format(data.timestamp_s))
        for i in range(0, 16):
            columns.append("input_{}".format(i + 1))
            values.append("'{}'".format(data.inputs[i].value))
            columns.append("input_unit_{}".format(i + 1))
            values.append("'{}'".format(data.inputs[i].unit))
        for i in range(0, 13):
            columns.append("output_{}".format(i + 1))
            values.append("{}".format(data.outputs[i]))
        for i in range(0, 4):
            columns.append("pump_speed_{}".format(i + 1))
            values.append("'{}'".format(data.pump_speeds[i].value))
            columns.append("pump_speed_unit_{}".format(i + 1))
            values.append("'{}'".format(data.pump_speeds[i].unit))
        sql = "INSERT INTO data ({}) VALUES ({})".format(", ".join(columns), ", ".join(values))
        log.debug("SQL: {}".format(sql))
        cur.execute(sql)


if __name__ == "__main__":
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)

    with DLoggModule("/dev/ttyUSB0") as device:
        header = device.get_header()
        log.info("Number of samples: {}".format(header.get_sample_count()))
        data = device.fetch_data_range(header.start, 10)
        device.fetch_end()
        log.info("Data 0: {}".format(data[0]))
        with DLoggDbUpload('staging-server', 3306, 'dlogg', 'dlogg', 'dlogg') as upload:
            upload.create_tables()
            upload.insert_data(data)
