#===============================================================================
# Imports
#===============================================================================
import os
import sys
import unittest

from os.path import (
    abspath,
    dirname,
)

from collections import defaultdict

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

def all_tests():
    import_all(test_module_names())
    tests = defaultdict(list)
    for test_class in EnversionTest.__subclasses__():
        tests[test_class.__module__].append(test_class)

    return tests

def announce(stream, module_name, test_class):
    stream.write('%s: %s\n' % (module_name, test_class))

def suites(stream):
    loader = unittest.defaultTestLoader
    for (module_name, classes) in all_tests().items():
        for test_class in classes:
            announce(stream, module_name, test_class.__name__)
            yield loader.loadTestsFromTestCase(test_class)

#===============================================================================
# Main
#===============================================================================
def main(quiet=None):
    if quiet:
        stream = open('/dev/null', 'w')
    else:
        stream = sys.stdout

    verbosity = int(not quiet)
    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity)
    for suite in suites(stream):
        runner.run(suite)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
