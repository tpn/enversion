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


def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
