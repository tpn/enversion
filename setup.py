#!/usr/bin/env python

import sys
vi = sys.version_info
if vi.major != 2 or vi.minor not in (6, 7):
    raise Exception("Enversion requires either Python 2.6 or 2.7.")

try:
    from setuptools import setup
    has_setuptools = True
except ImportError:
    has_setuptools = False
    from distutils.core import setup

setup(
    name='Enversion',
    version='0.1',
    description='Enterprise Subversion Framework',
    author='Trent Nelson',
    author_email='trent@snakebite.org',
    url='http://www.enversion.org/',
    py_modules=['evn'],
)


# vim:set ts=8 sw=4 sts=4 tw=78 et:
