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
    bulk_chargen,
)

from evn.config import (
    get_or_create_config,
)

from evn.test.dot import (
    dot,
)

from evn.constants import (
    format_file_exceeds_max_size_error,
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
        TestFileSizeUnderLimit,
        TestFileSizeAtLimit,
        TestFileSizeOverLimit,
    )

#===============================================================================
# Test Classes
#===============================================================================
class TestFileSizeUnderLimit(EnversionTest, unittest.TestCase):
    def test_01_under_limit(self):
        repo = self.create_repo()
        conf = repo.conf
        conf.set_max_file_size_in_bytes(1024)

        svn = repo.svn

        #evnadmin = repo.evnadmin
        #evnadmin.enable_remote_debug(repo.path, hook='pre-commit')

        dot()
        tree = {
            '1000-bytes.txt': bulk_chargen(1000),
            '1023-bytes.txt': bulk_chargen(1023),
        }
        repo.build(tree, prefix='trunk')

        with chdir(repo.wc):
            dot()
            svn.add('trunk/1000-bytes.txt')
            dot()
            svn.add('trunk/1023-bytes.txt')
            svn.ci('trunk', m='Adding files under limit...')

class TestFileSizeAtLimit(EnversionTest, unittest.TestCase):
    def test_01_at_limit(self):
        repo = self.create_repo()
        conf = repo.conf
        conf.set_max_file_size_in_bytes(1024)

        svn = repo.svn

        #evnadmin = repo.evnadmin
        #evnadmin.enable_remote_debug(repo.path, hook='pre-commit')

        dot()
        tree = { '1024-bytes.txt': bulk_chargen(1024) }
        repo.build(tree, prefix='trunk')

        error = format_file_exceeds_max_size_error(1024, 1024)
        with chdir(repo.wc):
            dot()
            svn.add('trunk/1024-bytes.txt')
            with ensure_blocked(self, error):
                svn.ci('trunk', m='At limit')

class TestFileSizeOverLimit(EnversionTest, unittest.TestCase):
    def test_01_over_limit(self):
        repo = self.create_repo()
        conf = repo.conf
        conf.set_max_file_size_in_bytes(1024)

        svn = repo.svn

        #evnadmin = repo.evnadmin
        #evnadmin.enable_remote_debug(repo.path, hook='pre-commit')

        dot()
        over = 1025
        tree = { 'over.txt': bulk_chargen(over) }
        repo.build(tree, prefix='trunk')

        error = format_file_exceeds_max_size_error(over, 1024)
        with chdir(repo.wc):
            dot()
            svn.add('trunk/over.txt')
            with ensure_blocked(self, error):
                svn.ci('trunk', m='Over limit')


def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
