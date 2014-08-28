#===============================================================================
# Imports
#===============================================================================
import unittest

from evn.test import (
    TestRepo,
    EnversionTest,
)

from evn.path import (
    join_path,
    format_dir,
)

from evn.util import (
    chdir,
)

from evn.config import (
    get_or_create_config,
)

from evn.test.dot import (
    dot,
)
#===============================================================================
# Globals
#===============================================================================
conf = get_or_create_config()

#===============================================================================
# Helpers
#===============================================================================
def suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSingleComponentRepo,
        TestMultiComponentRepo,
        TestNoComponentDepthRepo,
    )

class ensure_success(object):
    success = True
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        null_exc = (None, None, None)
        fn = self.obj.assertEqual
        if not self.success:
            fn = self.obj.assertNotEqual
        fn(null_exc, exc_info)

class ensure_failure(ensure_success):
    success = False

#===============================================================================
# Test Classes
#===============================================================================
class TestSingleComponentRepo(EnversionTest, unittest.TestCase):
    def test_01_basic(self):
        repo = self.create_repo()
        svn = repo.svn

        expected = conf.standard_layout
        raw = svn.ls(repo.uri)
        actual = frozenset(format_dir(l) for l in raw.splitlines())
        self.assertEqual(expected, actual)
        dot()

        with ensure_failure(self):
            with chdir(repo.wc):
                svn.mkdir('bar')
                svn.ci()
                dot()

    def test_02_no_svnmucc__commit_individually(self):
        repo = self.create_repo(no_svnmucc=True)
        svn = repo.svn

        actual = svn.ls(repo.uri)
        self.assertEqual('', actual)
        dot()

        for d in conf.standard_layout:
            with ensure_success(self):
                with chdir(repo.wc):
                    # Lop-off the leading '/'.
                    svn.mkdir(d[1:])
                    svn.ci()

    def test_03_no_svnmucc__commit_together(self):
        repo = self.create_repo(no_svnmucc=True)
        svn = repo.svn

        with ensure_success(self):
            with chdir(repo.wc):
                for d in conf.standard_layout:
                    # Lop-off the leading '/'.
                    svn.mkdir(d[1:])
                svn.ci()


class TestMultiComponentRepo(EnversionTest, unittest.TestCase):
    pass

class TestNoComponentDepthRepo(EnversionTest, unittest.TestCase):
    pass

def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
