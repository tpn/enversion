#===============================================================================
# Imports
#===============================================================================
import unittest

from evn.test import (
    ensure_blocked,
    expected_roots,

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
        TestSimpleRoots,
        TestSingleComponentRepo,
        TestMultiComponentRepo,
        TestNoComponentDepthRepo,
    )


#===============================================================================
# Test Classes
#===============================================================================
class TestSimpleRoots(EnversionTest, unittest.TestCase):
    @expected_roots({
        '/trunk/': {
            'copies': {},
            'created': 1,
            'creation_method': 'created',
        }
    })
    def test_01_basic(self):
        """
        Simple test to ensure the @expected_roots() logic works.
        """
        repo = self.create_repo()

class TestSingleComponentRepo(EnversionTest, unittest.TestCase):
    @expected_roots({
        '/trunk/': {
            'copies': {},
            'created': 1,
            'creation_method': 'created',
        }
    })
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

    def test_04_rm_standard_layout(self):
        """
        Given:
            /trunk/
            /tags/
            /branches/
        Make sure we can't rmdir any of the paths.
        """
        repo = self.create_repo()
        svn = repo.svn

        expected = conf.standard_layout
        raw = svn.ls(repo.uri)
        actual = frozenset(format_dir(l) for l in raw.splitlines())
        self.assertEqual(expected, actual)
        dot()

        error = e.TopLevelRepoDirectoryRemoved
        paths = [ p.replace('/', '') for p in conf.standard_layout ]
        with chdir(repo.wc):
            for path in paths:
                dot()
                svn.rm(path)
                with ensure_blocked(self, error):
                    svn.ci(path)

class TestMultiComponentRepo(EnversionTest, unittest.TestCase):
    def test_01_creation(self):
        """
        Create a multi-component repo via `evnadmin create --multi`.  The
        resulting repository should be empty.
        """
        repo = self.create_repo(multi=True)
        svn = repo.svn

        actual = svn.ls(repo.uri)
        self.assertEqual('', actual)

    def test_02_standard_layout_blocked(self):
        """
        Ensure top-level standard layout directories can't be created.
        """
        repo = self.create_repo(multi=True)
        svn = repo.svn

        actual = svn.ls(repo.uri)
        self.assertEqual('', actual)

        error = e.StandardLayoutTopLevelDirectoryCreatedInMultiComponentRepo
        paths = [ p.replace('/', '') for p in conf.standard_layout ]
        with chdir(repo.wc):
            for path in paths:
                dot()
                svn.mkdir(path)
                with ensure_blocked(self, error):
                    svn.ci(path)

    def test_03_component_standard_layout_allowed(self):
        """
        Ensure top-level standard layout directories can be created if they're
        housed under a component.
        """
        repo = self.create_repo(multi=True)
        svn = repo.svn

        paths = [ p.replace('/', '') for p in conf.standard_layout ]
        with chdir(repo.wc):
            for component in ('foo', 'bar'):
                svn.mkdir(component)
                for path in paths:
                    dot()
                    target = '/'.join((component, path))
                    svn.mkdir(target)
                svn.ci(component)

    def test_04_block_two_deep_non_standard_dirs(self):
        """
        Prevent any two-level deep directories from being created if they're
        not a standard directory.
        """
        repo = self.create_repo(multi=True)
        svn = repo.svn

        error = e.InvalidTopLevelRepoComponentDirectoryCreated
        paths = [ p.replace('/', '') for p in conf.standard_layout ]
        with chdir(repo.wc):
            dot()
            svn.mkdir('foo')
            svn.ci()

            dot()
            svn.mkdir('foo/bar')
            with ensure_blocked(self, error):
                svn.ci()

    def test_05_block_n_deep_non_standard_dirs(self):
        """
        Prevent any > two-level deep directories from being created if they're
        not a standard directory.
        """
        repo = self.create_repo(multi=True)
        svn = repo.svn

        error = e.InvalidTopLevelRepoComponentDirectoryCreated
        paths = [ p.replace('/', '') for p in conf.standard_layout ]
        with chdir(repo.wc):
            dot()
            svn.mkdir('foo')
            svn.ci()

            dot()
            svn.mkdir('foo/bar')
            svn.mkdir('foo/bar/tmp')
            with ensure_blocked(self, error):
                svn.ci()

            dot()
            svn.mkdir('viper')
            svn.mkdir('viper/eagle')
            svn.mkdir('viper/eagle/tomcat')
            with ensure_blocked(self, error):
                svn.ci('viper')

            dot()
            svn.mkdir('fulcrum')
            svn.mkdir('fulcrum/flanker')
            svn.mkdir('fulcrum/flanker/foxbat')
            svn.mkdir('fulcrum/flanker/foxbat/tags')
            svn.mkdir('fulcrum/flanker/foxbat/trunk')
            svn.mkdir('fulcrum/flanker/foxbat/branches')
            with ensure_blocked(self, error):
                svn.ci('fulcrum')

class TestNoComponentDepthRepo(EnversionTest, unittest.TestCase):
    @expected_roots({
        '/trunk/': {'created': 3},
        '/branches/foo-1.x/': { 'created': 6 },
        '/foo/trunk/': { 'created': 5 },
        '/fulcrum/flanker/foxbat/trunk/': {
            'copies': {},
            'created': 8,
            'creation_method': 'created',
        },
    })
    def test_01_creation(self):
        """
        Create a repository with component-depth support disabled, then create
        various levels of directories that would be blocked by simple/multi
        component layouts.
        """
        repo = self.create_repo(component_depth='-1')
        svn = repo.svn

        actual = svn.ls(repo.uri)
        self.assertEqual('', actual)
        dot()

        paths = [ p.replace('/', '') for p in conf.standard_layout ]
        with chdir(repo.wc):
            for path in paths:
                dot()
                svn.mkdir(path)
                svn.ci(path)

            dot()
            svn.mkdir('foo')
            svn.mkdir('foo/bar')
            svn.ci('foo')

            dot()
            svn.mkdir('foo/trunk')
            svn.ci('foo/trunk')

            dot()
            svn.up()
            svn.cp('foo/trunk', 'branches/foo-1.x')
            svn.ci(m='Branching 1.x')
            svn.ci()

            dot()
            svn.mkdir('viper')
            svn.mkdir('viper/eagle')
            svn.mkdir('viper/eagle/tomcat')
            svn.ci('viper')

            dot()
            svn.mkdir('fulcrum')
            svn.mkdir('fulcrum/flanker')
            svn.mkdir('fulcrum/flanker/foxbat')
            svn.mkdir('fulcrum/flanker/foxbat/tags')
            svn.mkdir('fulcrum/flanker/foxbat/trunk')
            svn.mkdir('fulcrum/flanker/foxbat/branches')
            svn.ci('fulcrum')

def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
