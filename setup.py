#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from setuptools import setup

with open("cmssw_interface/include/VERSION", "r") as f:
    version = f.read().strip()

setup(
    name          = 'cmssw_interface',
    version       = version,
    license       = 'BSD 3-Clause License',
    description   = 'Description text',
    url           = 'https://github.com/tklijnsma/cmssw_interface.git',
    author        = 'Thomas Klijnsma',
    author_email  = 'tklijnsm@gmail.com',
    packages      = ['cmssw_interface'],
    package_data  = {'cmssw_interface': ['include/*']},
    include_package_data = True,
    zip_safe      = False,
    scripts       = []
    )
