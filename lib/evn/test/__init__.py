#===============================================================================
# Imports
#===============================================================================
import os
import sys
import inspect
import unittest

from os.path import (
    isdir,
    abspath,
    dirname,
    basename,
)

from collections import defaultdict

from abc import ABCMeta

from evn.path import (
    join_path,
    format_dir,
    build_tree,
)

from evn.util import (
    try_remove_dir,
    try_remove_dir_atexit,
)

#===============================================================================
# Classes
#===============================================================================
class TestRepo(object):
    def __init__(self, name):
        self.name = name
        self.path = abspath(name)
        self.uri  = 'file://%s' % self.path
        self.wc   = self.path + '.wc'

        from evn.exe import (
            svn,
            svnmucc,
            svnadmin,
            evnadmin,
        )

        self.svn = svn
        self.svn.username = 'test.user'
        self.svn.password = 'dummy_password'

        self.svnmucc = svnmucc
        self.svnadmin = svnadmin
        self.evnadmin = evnadmin


        from evn.test.dot import (
            dot,
            dash,
        )

        self.dot = dot
        self.dash = dash


    def create(self, **kwds):
        if isdir(self.name):
            try_remove_dir(self.name)
        self.evnadmin.create(self.name, **kwds)
        self.dot()
        try_remove_dir_atexit(self.path)

    def checkout(self):
        if isdir(self.wc):
            try_remove_dir(self.wc)
        self.svn.checkout(self.uri, self.wc)
        self.dot()
        try_remove_dir_atexit(self.wc)

    def build(self, tree, prefix=''):
        build_tree(tree, prefix=''.join((self.wc, prefix)))


class EnversionTest(object):
    __metaclass__ = ABCMeta

    def create_repo(self, checkout=True, **kwds):
        test_name = inspect.currentframe().f_back.f_code.co_name
        repo_name = '_'.join((self.__class__.__name__, test_name))
        repo = TestRepo(repo_name)
        repo.create(**kwds)
        if checkout:
            repo.checkout()
        return repo

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
    import evn.test.dot
    if quiet:
        stream = open('/dev/null', 'w')
    else:
        stream = sys.stdout

    evn.test.dot.stream = stream

    verbosity = int(not quiet)
    runner = unittest.TextTestRunner(
        stream=stream,
        failfast=True,
        verbosity=verbosity,
    )
    for suite in suites(stream):
        result = runner.run(suite)
        if not result.wasSuccessful():
            sys.exit(1)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
