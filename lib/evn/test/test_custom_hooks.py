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
        TestChangeSetPropertyStuffViaCustomHook,
    )

#===============================================================================
# Test Classes
#===============================================================================
class TestChangeSetPropertyStuffViaCustomHook(EnversionTest, unittest.TestCase):
    classname = 'evn.test.custom_hook.ChangeSetPropertyTesterCustomHook'
    def test_01_tag_and_branch_creation_detection(self):
        repo = self.create_repo()
        conf = repo.conf
        conf.set_custom_hook_classname(self.classname)
        svn = repo.svn

        #evnadmin = repo.evnadmin
        #evnadmin.enable_remote_debug(repo.path, hook='pre-commit')

        error = 'is_branch_create: /branches/1.x/'
        with chdir(repo.wc):
            svn.cp('trunk', 'branches/1.x')
            with ensure_blocked(self, error):
                svn.ci('branches/1.x', m='Branching...')

        dot()
        error = 'is_tag_create: /tags/1.1/'
        with chdir(repo.wc):
            svn.cp('trunk', 'tags/1.1')
            with ensure_blocked(self, error):
                svn.ci('tags/1.1', m='Tagging...')

    def test_02_tag_and_branch_removal_detection(self):
        repo = self.create_repo()
        conf = repo.conf
        svn = repo.svn

        with chdir(repo.wc):
            svn.cp('trunk', 'branches/1.x')
            svn.ci('branches/1.x', m='Branching...')

        dot()
        with chdir(repo.wc):
            svn.cp('trunk', 'tags/1.1')
            svn.ci('tags/1.1', m='Tagging...')

        dot()
        svn.up()

        dot()
        conf.set_custom_hook_classname(self.classname)
        svn = repo.svn

        #evnadmin = repo.evnadmin
        #evnadmin.enable_remote_debug(repo.path, hook='pre-commit')

        dot()
        error = 'is_branch_remove: /branches/1.x/'
        with chdir(repo.wc):
            svn.rm('branches/1.x')
            with ensure_blocked(self, error):
                svn.ci('branches/1.x', m='Removing branch...')

        dot()
        error = 'is_tag_remove: /tags/1.1/'
        with chdir(repo.wc):
            svn.rm('tags/1.1')
            with ensure_blocked(self, error):
                svn.ci('tags/1.1', m='Removing tag...')

        conf = repo.conf
        conf.set_custom_hook_classname(self.classname)

def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
