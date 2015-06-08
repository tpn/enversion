#===============================================================================
# Imports
#===============================================================================
import sys
import unittest

from evn.test import (
    ensure_fails,
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
    EVN_ERROR_CONFIRMATIONS,
)
#===============================================================================
# Globals
#===============================================================================
conf = get_or_create_config()

#===============================================================================
# Helpers
#===============================================================================
def suite():
    module = sys.modules[__name__]
    return unittest.defaultTestLoader.loadTestsFromModule(module)

#===============================================================================
# Test Classes
#===============================================================================

class TestRepoAdmins(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.1/'), m='Tagging')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.2/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set((
            '/trunk/',
            '/branches/1.x/',
            '/tags/1.0/',
            '/tags/1.1/',
            '/tags/1.2/',
        ))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        is_repo_admin = lambda u: evnadmin.is_repo_admin(repo.name, u=u)
        add_repo_admin = lambda u: evnadmin.add_repo_admin(repo.name, u=u)
        show_repo_admins = lambda: evnadmin.show_repo_admins(repo.name)
        remove_repo_admin = lambda u: evnadmin.remove_repo_admin(repo.name, u=u)

        dot()
        username = svn.username
        self.assertEqual(is_repo_admin(username), 'no')
        self.assertEqual(is_repo_admin('laskdjflsdkjf'), 'no')

        dot()
        error = e.TagCopied
        with ensure_blocked(self, error):
            svn.cp(repo.ra('/tags/1.0/'), repo.ra('/other/1.0/'), m='Tagging')

        dot()
        error = 'commits with errors can only be forced through by'
        with ensure_blocked(self, error):
            svn.cp(repo.ra('/tags/1.0/'), repo.ra('/other/1.0/'),
                   m='IGNORE ERRORS')

        #dot()
        #error = e.TagCopied
        #with ensure_blocked(self, error):
        #    svn.cp(repo.ra('/tags/1.0/'), repo.ra('/other/1.0/'),
        #           m=EVN_ERROR_CONFIRMATIONS[e.TagCopied])

        dot()
        add_repo_admin(username)
        self.assertEqual(is_repo_admin(username), 'yes')

        # Make sure we're still blocked if we're an admin but we haven't
        # explicitly included IGNORE ERRORS.
        dot()
        error = e.TagCopied
        with ensure_blocked(self, error):
            svn.cp(repo.ra('/tags/1.0/'), repo.ra('/other/1.0/'), m='Tagging')

        dot()
        error = e.TagCopied
        svn.cp(repo.ra('/tags/1.0/'), repo.ra('/other/1.0/'),
                   m='IGNORE ERRORS')

        #dot()
        #error = e.TagRemoved
        #svn.rm(repo.ra('/tags/1.1/'), m=EVN_ERROR_CONFIRMATIONS[error])

        with chdir(repo.wc):
            svn.up()
            svn.cp('tags/1.2', 'other/1.2')
            svn.cp('trunk', 'other/foobar')
            svn.cp('branches/1.x', 'other/1.x')
            svn.ci(m='IGNORE ERRORS')

class TestRepoAdminConf(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        user1 = svn.username
        user2 = 'foobar'
        assert user1 != user2
        both = ','.join(sorted((user2, user1)))

        is_repo_admin = lambda u: evnadmin.is_repo_admin(repo.name, u=u)
        add_repo_admin = lambda u: evnadmin.add_repo_admin(repo.name, u=u)
        show_repo_admins = lambda: evnadmin.show_repo_admins(repo.name)
        remove_repo_admin = lambda u: evnadmin.remove_repo_admin(repo.name, u=u)

        dot()
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), '<none>')

        dot()
        add_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Trying to re-add will be ignored.
        dot()
        add_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Try to remove non-existent.
        dot()
        remove_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Remove first.
        dot()
        remove_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), '<none>')

        # Add one back.
        dot()
        add_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Add second.
        add_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), both)

        # Add second again (no-op).
        dot()
        add_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), both)

        # Remove second.
        dot()
        remove_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Remove second again.
        dot()
        remove_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Remove first.
        dot()
        remove_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), '<none>')

        # Re-start: add first, then second, then remove first.
        dot()
        add_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), user1)

        # Add second.
        dot()
        add_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), both)

        # Remove first.
        dot()
        remove_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), user2)

        # Remove first again.
        dot()
        remove_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), user2)

        # Remove second.
        dot()
        remove_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'no')
        self.assertEqual(show_repo_admins(), '<none>')

        # Add second then first, verify order is still as expected.
        dot()
        add_repo_admin(user2)
        self.assertEqual(is_repo_admin(user1), 'no')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), user2)

        dot()
        add_repo_admin(user1)
        self.assertEqual(is_repo_admin(user1), 'yes')
        self.assertEqual(is_repo_admin(user2), 'yes')
        self.assertEqual(show_repo_admins(), both)


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
