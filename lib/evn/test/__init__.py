#===============================================================================
# Imports
#===============================================================================
import os
import sys
import shutil
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

from functools import (
    partial,
)

from evn.path import (
    join_path,
    format_dir,
    build_tree,
)

from evn.util import (
    literal_eval,
    try_remove_dir,
    try_remove_dir_atexit,
)

from evn.config import (
    Config,
)

from evn.exe import (
    SubversionClientException,
)

#===============================================================================
# Classes
#===============================================================================
class TestRepo(object):
    keep = False

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
        self.conf = None

    def reload_conf(self):
        conf = Config()
        conf.load()
        conf.load_repo(self.path)
        self.conf = conf
        return conf

    def create(self, **kwds):
        if isdir(self.path):
            shutil.rmtree(self.path)
        self.evnadmin.create(self.name, **kwds)
        self.dot()
        if not self.keep:
            try_remove_dir_atexit(self.path)
        self.reload_conf()

    def checkout(self):
        if isdir(self.wc):
            shutil.rmtree(self.wc)
        self.svn.checkout(self.uri, self.wc)
        self.dot()
        if not self.keep:
            try_remove_dir_atexit(self.wc)

    def build(self, tree, prefix=''):
        build_tree(tree, prefix='/'.join((self.wc, prefix)))

    @property
    def roots(self):
        return literal_eval(self.evnadmin.show_roots(self.name, quiet=True))

    @property
    def component_depth_full(self):
        return self.evnadmin.get_repo_component_depth(self.name)

    @property
    def component_depth(self):
        return int(self.component_depth_full.split(' ')[0])

class EnversionTest(object):
    __metaclass__ = ABCMeta

    repo = None

    @property
    def repo_name(self):
        # Helper method; can be called from derived classes for a convenient
        # way to get at the repo name without needing to create the repo.
        test_name = inspect.currentframe().f_back.f_code.co_name
        repo_name = '_'.join((self.__class__.__name__, test_name))
        return repo_name

    @property
    def repo_path(self):
        # As above but for the repo path.
        test_name = inspect.currentframe().f_back.f_code.co_name
        repo_name = '_'.join((self.__class__.__name__, test_name))
        return abspath(self.repo_name)

    def create_repo(self, checkout=True, **kwds):
        test_name = inspect.currentframe().f_back.f_code.co_name
        repo_name = '_'.join((self.__class__.__name__, test_name))
        repo = TestRepo(repo_name)
        repo.create(**kwds)
        if checkout:
            repo.checkout()
        self.repo = repo
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

def suites(stream, single=None, load=True):
    loader = unittest.defaultTestLoader
    for (module_name, classes) in all_tests().items():
        for test_class in classes:
            classname = test_class.__name__
            if single and not classname.endswith(single):
                continue
            announce(stream, module_name, classname)
            if load:
                tests = loader.loadTestsFromTestCase(test_class)
            else:
                tests = None
            yield tests

def crude_error_message_test(actual, expected):
    ix = expected.find('%')
    if ix == -1:
        return expected in actual

    if len(actual) < len(expected):
        return False

    return expected[:ix] in actual

class ensure_blocked(object):
    def __init__(self, obj, expected):
        self.obj = obj
        self.expected = expected

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        (exc_type, exc_val, exc_tb) = exc_info
        obj = self.obj
        obj.assertEqual(exc_type, SubversionClientException)
        actual = exc_val.args[1]
        if not crude_error_message_test(actual, self.expected):
            if '\n' in actual:
                sys.stderr.write('\n'.join(('ACTUAL:', actual)))
            if '\n' in self.expected:
                sys.stderr.write('\n'.join(('EXPECTED:', expected)))
            obj.assertEqual(actual, self.expected)
        return True

class ensure_fails(object):
    # Slight modification of the ensure_blocked decorator above that is
    # intended to be called against general ProcessWrapper RuntimeErrors.
    def __init__(self, obj, expected):
        self.obj = obj
        self.expected = expected

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        (exc_type, exc_val, exc_tb) = exc_info
        obj = self.obj
        obj.assertEqual(exc_type, RuntimeError)
        actual = exc_val.args[1]
        if not crude_error_message_test(actual, self.expected):
            if '\n' in actual:
                sys.stderr.write('\n'.join(('ACTUAL:', actual)))
            if '\n' in self.expected:
                sys.stderr.write('\n'.join(('EXPECTED:', expected)))
            obj.assertEqual(actual, self.expected)
        return True


#===============================================================================
# Decorators
#===============================================================================
class expected_roots(object):
    """
    Helper decorator for automatically testing evn:roots values after a test
    has run, based on the roots dict passed in as the first argument to the
    decorator, e.g.:

        class TestSimpleRoots(EnversionTest, unittest.TestCase):
            @expected_roots({
                '/trunk/': {
                    'copies': {},
                    'created': 1,
                    'creation_method': 'created',
                }
            })
            def test_01_basic(self):
                repo = self.create_repo()


    The roots can be accessed via class.func.roots, i.e. for the example
    above, the dict would be accessible from TestSimpleRoots.test_basic.roots.
    """
    def __init__(self, roots):
        self.func = None
        self.roots = roots

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kwds):
        if not self.func:
            self.func = args[0]
            return self

        self.func(*args, **kwds)

        obj = args[0]
        obj.repo.dot()
        obj.assertEqual(self.roots, obj.repo.roots)

class expected_component_depth(object):
    """
    Helper decorator for automatically testing evn:component_depth after a test
    has run, e.g.:

        class TestSimple(EnversionTest, unittest.TestCase):
            @expected_component_depth(0)
            def test_01_single(self):
                repo = self.create_repo(single=True)

            @expected_component_depth(1)
            def test_02_multi(self):
                repo = self.create_repo(multi=True)

            @expected_component_depth(-1)
            def test_03_none(self):
                repo = self.create_repo(component_depth=-1)
    """
    def __init__(self, component_depth):
        self.func = None
        self.component_depth = component_depth

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kwds):
        if not self.func:
            self.func = args[0]
            return self

        self.func(*args, **kwds)

        obj = args[0]
        obj.repo.dot()
        obj.assertEqual(self.component_depth, obj.repo.component_depth)

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
        verbosity=verbosity,
    )
    failed = 0

    single = None
    if len(sys.argv) == 3:
        single = sys.argv[-1]
        TestRepo.keep = True

    for suite in suites(stream, single):
        result = runner.run(suite)
        if not result.wasSuccessful():
            failed += 1

    if failed:
        sys.stderr.write('\n*** FAILURES: %d ***\n' % failed)
        sys.exit(1)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
