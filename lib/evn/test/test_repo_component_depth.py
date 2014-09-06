#===============================================================================
# Imports
#===============================================================================
import unittest

from evn.test import (
    ensure_blocked,

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

from evn.constants import (
    e, # Errors
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


#===============================================================================
# Test Classes
#===============================================================================
class TestSingleComponentRepo(EnversionTest, unittest.TestCase):
    def test_01_basic(self):
        """
        Given:
            /trunk/
            /tags/
            /branches/
        Make sure we can't create:
            /bar/
        """
        repo = self.create_repo()
        svn = repo.svn

        expected = conf.standard_layout
        raw = svn.ls(repo.uri)
        actual = frozenset(format_dir(l) for l in raw.splitlines())
        self.assertEqual(expected, actual)
        dot()

        expected = e.InvalidTopLevelRepoDirectoryCreated
        with chdir(repo.wc):
            svn.mkdir('bar')
            with ensure_blocked(self, expected):
                svn.ci()
                dot()

    def test_02_no_svnmucc__commit_individually(self):
        """
        Create an empty repo via `evnadmin create --no-svnmucc`, then issue
        three individual mkdirs then commits for:
            /trunk/
            /tags/
            /branches/
        """
        repo = self.create_repo(no_svnmucc=True)
        svn = repo.svn

        actual = svn.ls(repo.uri)
        self.assertEqual('', actual)
        dot()

        for d in conf.standard_layout:
            with chdir(repo.wc):
                # Lop-off the leading '/'.
                svn.mkdir(d[1:])
                svn.ci()
                dot()

    def test_03_no_svnmucc__commit_together(self):
        """
        Create an empty repo via `evnadmin create --no-svnmucc`, then issue
        three mkdirs followed by a single commit for:
            /trunk/
            /tags/
            /branches/
        """
        repo = self.create_repo(no_svnmucc=True)
        svn = repo.svn

        with chdir(repo.wc):
            for d in conf.standard_layout:
                # Lop-off the leading '/'.
                svn.mkdir(d[1:])
            svn.ci()
            dot()


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
