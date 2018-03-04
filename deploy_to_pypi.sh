#!/bin/bash

rm -r ./dist
virtualenv venv
source venv/bin/activate
pip install twine
python setup.py sdist bdist_wheel
twine upload dist/*
