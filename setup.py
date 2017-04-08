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
from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='dlogg-driver',
    version='0.2.1',
    description='Unofficial library to read data from a Technische Alternative D-LOGG device.',
    long_description=long_description,
    url='https://github.com/ubruhin/python-dlogg-driver',
    author='U. Bruhin',
    author_email='python-dlogg@ubruhin.ch',
    license='GPLv3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='technische alternative, dlogg, d-logg, d logg',
    packages=['dlogg_driver'],
    install_requires=['enum34', 'pyserial'],
)
