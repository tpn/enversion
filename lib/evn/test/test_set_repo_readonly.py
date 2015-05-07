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
    bulk_chargen,
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
        TestSetRepoReadonly,
    )

#===============================================================================
# Test Classes
#===============================================================================
class TestSetRepoReadonly(EnversionTest, unittest.TestCase):
    def test_01_is_repo_readonly(self):
        repo = self.create_repo()
        evnadmin = repo.evnadmin
        is_repo_readonly = evnadmin.is_repo_readonly

        expected = 'no'
        actual = is_repo_readonly(repo.path)
        self.assertEqual(expected, actual)

    def test_02_set_repo_readonly(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        is_repo_readonly = evnadmin.is_repo_readonly
        set_repo_readonly = evnadmin.set_repo_readonly
        unset_repo_readonly = evnadmin.unset_repo_readonly

        dot()
        expected = 'no'
        actual = is_repo_readonly(repo.path)
        self.assertEqual(expected, actual)

        tree = { 'test1.txt': bulk_chargen(100) }
        repo.build(tree, prefix='trunk')

        dot()
        with chdir(repo.wc):
            dot()
            svn.add('trunk/test1.txt')
            dot()
            svn.ci('trunk', m='Adding test1.txt')

        dot()
        set_repo_readonly(repo.path)

        dot()
        expected = 'yes'
        actual = is_repo_readonly(repo.path)
        self.assertEqual(expected, actual)

        dot()
        tree = { 'test2.txt': bulk_chargen(200), }
        repo.build(tree, prefix='trunk')

        error = 'This repository cannot be committed to at the present time'
        with ensure_blocked(self, error):
            with chdir(repo.wc):
                dot()
                svn.add('trunk/test2.txt')
                dot()
                svn.ci('trunk', m='Adding test2.txt')

        dot()
        unset_repo_readonly(repo.path)

        dot()
        expected = 'no'
        actual = is_repo_readonly(repo.path)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            dot()
            dot()
            svn.ci('trunk', m='Adding test2.txt')

def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
