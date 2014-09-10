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
        TestSimpleBranching,
    )


#===============================================================================
# Test Classes
#===============================================================================
class TestSimpleBranching(EnversionTest, unittest.TestCase):
    def test_01_basic(self):
        """
        Make sure trunk can't be re-copied within a branch.
        Reported by: @jamieechlin
        """
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        roots_r1 = {
            '/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(roots_r1, repo.roots)

        dot()
        with chdir(repo.wc):
            svn.cp('trunk', 'branches/1.x')
            svn.ci(m='Branching 1.x.')

        roots_r2 = {
            '/trunk/': { 'created': 1 },
            '/branches/1.x/': {
                'copied_from': ('/trunk/', 1),
                'copies': {},
                'created': 2,
                'creation_method': 'copied',
                'errors': []
            },
        }
        self.assertEqual(roots_r2, repo.roots)

        dot()
        error = 'known root path copied to known root subtree path'
        with chdir(repo.wc):
            svn.cp('trunk', 'branches/1.x')
            with ensure_blocked(self, error):
                svn.ci('branches/1.x', m='Copying trunk to branches/1.x.')


def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
