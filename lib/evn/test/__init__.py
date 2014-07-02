#===============================================================================
# Imports
#===============================================================================
import os
import unittest

from os.path import (
    abspath,
    dirname,
)

from abc import ABCMeta

#===============================================================================
# Classes
#===============================================================================
class EnversionTest(object):
    __metaclass__ = ABCMeta

#===============================================================================
# Helpers
#===============================================================================
def test_module_names():
    path = abspath(__file__)
    base = dirname(path)
    return [
        'evn.test.%s' % f[:-len('.py')]
            for f in os.listdir(base) if (
                f.startswith('test_') and
                f.endswith('.py')
            )
    ]

def import_all(names):
    import importlib
    return [ importlib.import_module(name) for name in names ]

def all_test_classes():
    import_all(test_module_names())
    return EnversionTest.__subclasses__()

def suite():
    loader = unittest.defaultTestLoader
    return loader.loadTestsFromTestCase(*all_test_classes())

#===============================================================================
# Main
#===============================================================================
def main(quiet=None):
    runner = unittest.TextTestRunner()
    runner.run(suite())

# vim:set ts=8 sw=4 sts=4 tw=78 et:
