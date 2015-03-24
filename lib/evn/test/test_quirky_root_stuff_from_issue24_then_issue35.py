# https://github.com/enversion/enversion/issues/24
# This was fixed back in ..., but a client was seeing quirky corner cases not
# being hanlded correctly.  The issue24 branch was re-opened and this unit
# test file was authored to capture the actions causing the reported issues.

# ....and then I decided against that, closed issue24 again and created a new
# issue: https://github.com/enversion/enversion/issues/35

#===============================================================================
# Imports
#===============================================================================
import unittest

from evn.test import (
    ensure_blocked,
    expected_roots,
    expected_component_depth,

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

KnownRootPathCopiedToKnownRootSubtreePath = (
    'known root path copied to known root subtree path'
)
KnownRootPathRenamedToKnownRootSubtreePath = (
    'known root path renamed to known root subtree path'
)

#===============================================================================
# Helpers
#===============================================================================
def suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TrunkCopiedToTrunkSubtree,
        TrunkCopiedToTrunkSubtreePost,
        TrunkCopiedToTag,
        TrunkCopiedToTagPost,
        TestMultiTrunkCopiedToOtherMultiTrunkSubtree,
        TestMultiTrunkRenamedToOtherMultiTrunkSubtree,
    )


#===============================================================================
# Test Classes
#===============================================================================

class TrunkCopiedToTrunkSubtree(EnversionTest, unittest.TestCase):
    """
    svn cp ^/trunk ^/trunk/foo
        - This was resulting in the evn:roots for ^/trunk being blown away.
    """
    def test_01_wc_when_enabled(self):
        # This appears to be blocked by svn.exe with an error message along
        # the lines of:
        #   Cannot copy path '/trunk' into its own child '/trunk/foo'
        repo = self.create_repo()
        conf = repo.conf
        svn = repo.svn

        error = 'Cannot copy path'
        dot()
        with chdir(repo.wc):
            with ensure_blocked(self, error):
                svn.copy('trunk', 'trunk/foo')
                svn.ci('trunk', m='Copy trunk')

    def test_02_ra_when_enabled(self):
        repo = self.create_repo(checkout=False)
        conf = repo.conf
        svn = repo.svn

        dot()
        error = KnownRootPathCopiedToKnownRootSubtreePath
        with ensure_blocked(self, error):
            svn.copy(repo.ra('trunk'), repo.ra('trunk/foo'), m='Copy')

# Like the above, but disable Enversion, then re-enable after commit and test
# roots are updated correctly.
class TrunkCopiedToTrunkSubtreePost(EnversionTest,
                                    unittest.TestCase):
    def test_01_ra(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin


        # Make sure the roots on r1 are as we expect.
        dot()
        roots_r1_expected = {
            '/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots, roots_r1_expected)

        # Disable the hooks.
        dot()
        evnadmin.disable(repo.path)

        # Copy the path.
        dot()
        svn.copy(repo.ra('trunk'), repo.ra('trunk/foo'), m='Copy')

        # Re-enable the hooks.
        dot()
        evnadmin.enable(repo.path)

        # Check that the roots for r1 haven't changed.
        dot()
        roots_r1 = repo.roots_at(1)
        self.assertEqual(roots_r1, roots_r1_expected)

        # Check that the roots at r2 are as we expect.
        dot()
        roots_r2_expected = { '/trunk/': { 'created': 1 } }
        self.assertEqual(repo.roots, roots_r2_expected)
        self.assertEqual(repo.roots_at(2), roots_r2_expected)

        # Make sure the correct error was recorded.
        dot()
        errors = repo.revprops['evn']['errors']
        msg = KnownRootPathCopiedToKnownRootSubtreePath
        expected = { '/trunk/foo/': [msg] }
        self.assertEqual(errors, expected)

class TrunkCopiedToTag(EnversionTest, unittest.TestCase):
    """
    This one was particularly bad.  A tag had been created correctly:
        svn cp ^/trunk ^/tags/1.0

    All roots were correct.  Then somehow, this commit was permitted:
        svn cp ^/trunk ^/tags/1.0/trunk

    That should have been blocked as tags are immutable.  The evn:root for
    trunk was also removed (which is the same behavior the other cases were
    exhibiting).

    """
    @expected_roots({
        '/tags/1.0/': {
            'copied_from': ('/trunk/', 1),
            'copies': {},
            'created': 2,
            'creation_method': 'copied',
            'errors': [],
        },
        '/trunk/': {
            'created': 1
        }
    })
    def test_01_wc(self):
        repo = self.create_repo()
        conf = repo.conf
        svn = repo.svn

        dot()
        with chdir(repo.wc):
            svn.copy('trunk', 'tags/1.0')
            svn.ci('tags', m='Tag trunk')

        error = 'known root path copied to known root subtree path'
        with chdir(repo.wc):
            with ensure_blocked(self, error):
                svn.copy('trunk', 'tags/1.0')
                svn.ci('tags/1.0', m='Incorrect copy')

    @expected_roots({
        '/tags/1.0/': {
            'copied_from': ('/trunk/', 1),
            'copies': {},
            'created': 2,
            'creation_method': 'copied',
            'errors': [],
        },
        '/trunk/': {
            'created': 1
        }
    })
    def test_02_ra(self):
        repo = self.create_repo(checkout=False)
        svn = repo.svn

        dot()
        svn.copy(repo.ra('trunk'), repo.ra('tags/1.0'), m='Tagging 1.0')

        error = KnownRootPathCopiedToKnownRootSubtreePath
        dot()
        with ensure_blocked(self, error):
            svn.copy(repo.ra('trunk'), repo.ra('tags/1.0'), m='Tagging 1.0')

class TrunkCopiedToTagPost(EnversionTest, unittest.TestCase):
    def test_01_evn_disabled_at_r1(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin


        # Make sure the roots on r1 are as we expect.
        dot()
        roots_r1_expected = {
            '/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots, roots_r1_expected)

        # Disable the hooks.
        dot()
        evnadmin.disable(repo.path)

        # Copy the path.
        dot()
        svn.copy(repo.ra('trunk'), repo.ra('tags/1.0'), m='Copy')

        # And copy it again; second copy will end up under tags/1.0/trunk.
        dot()
        svn.copy(repo.ra('trunk'), repo.ra('tags/1.0'), m='Copy')

        # Re-enable the hooks.
        dot()
        evnadmin.enable(repo.path)

        # Check roots.
        dot()
        roots_r1_expected = {
            '/trunk/': {
                'copies': {
                    1: [('/tags/1.0/', 2)]
                },
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots_at(1), roots_r1_expected)

        roots_r2_expected = {
            '/tags/1.0/': {
                'copied_from': ('/trunk/', 1),
                'copies': {},
                'created': 2,
                'creation_method': 'copied',
                'errors': [],
            },
            '/trunk/': { 'created': 1 },
        }

        dot()
        roots_r2 = repo.roots_at(2)
        self.assertEqual(roots_r2, roots_r2_expected)

        dot()
        roots_r3_expected = {
            '/trunk/': { 'created': 1 },
            '/tags/1.0/': { 'created': 2 },
        }
        self.assertEqual(repo.roots, roots_r3_expected)
        self.assertEqual(repo.roots_at(2), roots_r2_expected)
        self.assertEqual(repo.roots_at(1), roots_r1_expected)

        # Make sure the correct error was recorded.
        dot()
        errors = repo.revprops['evn']['errors']
        msg = KnownRootPathCopiedToKnownRootSubtreePath
        expected = { '/tags/1.0/trunk/': [msg] }
        self.assertEqual(errors, expected)

    def test_02_evn_enabled(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Make sure the roots on r1 are as we expect.
        dot()
        roots_r1_expected = {
            '/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots, roots_r1_expected)

        # Copy the path.
        dot()
        svn.copy(repo.ra('trunk'), repo.ra('tags/1.0'), m='Copy')

        # Try copy it again; ensure it's blocked.
        dot()
        error = KnownRootPathCopiedToKnownRootSubtreePath
        with ensure_blocked(self, error):
            svn.copy(repo.ra('trunk'), repo.ra('tags/1.0'), m='Copy again')

        # Check roots.
        dot()
        roots_r1_expected = {
            '/trunk/': {
                'copies': {
                    1: [('/tags/1.0/', 2)]
                },
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots_at(1), roots_r1_expected)

        dot()
        roots_r2_expected = {
            '/tags/1.0/': {
                'copied_from': ('/trunk/', 1),
                'copies': {},
                'created': 2,
                'creation_method': 'copied',
                'errors': [],
            },
            '/trunk/': { 'created': 1 },
        }
        roots_r2 = repo.roots_at(2)
        self.assertEqual(roots_r2, roots_r2_expected)

def make_std_layout(repo, components=None):
    conf = repo.conf
    svn = repo.svn
    if not components:
        components = ('foo', 'bar')
    paths = [ p.replace('/', '') for p in conf.standard_layout ]
    with chdir(repo.wc):
        for component in components:
            svn.mkdir(component)
            for path in paths:
                dot()
                target = '/'.join((component, path))
                svn.mkdir(target)
            svn.ci(component)

class TestMultiTrunkCopiedToOtherMultiTrunkSubtree(EnversionTest,
                                                   unittest.TestCase):
    """
    svn cp ^/foo/trunk/ ^/bar/trunk/trunk/
    """
    @expected_component_depth(1)
    def test_01_evn_enabled(self):
        repo = self.create_repo(multi=True)
        conf = repo.conf
        svn = repo.svn

        dot()
        make_std_layout(repo)

        dot()
        self.assertEqual(repo.roots_at(1), {
            '/foo/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots_at(2), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots, {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })


        dot()
        error = KnownRootPathCopiedToKnownRootSubtreePath
        with ensure_blocked(self, error):
            svn.copy(repo.ra('/foo/trunk'), repo.ra('/bar/trunk'), m='cp')

        dot()
        self.assertEqual(repo.roots, {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })


    @expected_component_depth(1)
    def test_02_evn_disabled_at_r2(self):
        repo = self.create_repo(multi=True)
        conf = repo.conf
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        make_std_layout(repo)

        dot()
        self.assertEqual(repo.roots_at(1), {
            '/foo/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots_at(2), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })

        dot()
        evnadmin.disable(repo.path)

        # Copy again; will end up with /bar/trunk/trunk.
        dot()
        svn.copy(repo.ra('/foo/trunk'), repo.ra('/bar/trunk'), m='cp')

        dot()
        evnadmin.enable(repo.path)

        dot()
        self.assertEqual(repo.roots_at(1), {
            '/foo/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots_at(2), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots_at(3), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': { 'created': 2 },
        })

        # Make sure the correct error was recorded.
        dot()
        errors = repo.revprops['evn']['errors']
        msg = KnownRootPathCopiedToKnownRootSubtreePath
        expected = { '/bar/trunk/trunk/': [msg] }
        self.assertEqual(errors, expected)

class TestMultiTrunkRenamedToOtherMultiTrunkSubtree(EnversionTest,
                                                    unittest.TestCase):
    """
    svn mv ^/foo/trunk/ ^/bar/trunk/trunk/
    """
    @expected_component_depth(1)
    def test_01_evn_enabled(self):
        repo = self.create_repo(multi=True)
        conf = repo.conf
        svn = repo.svn

        dot()
        make_std_layout(repo)

        dot()
        self.assertEqual(repo.roots_at(1), {
            '/foo/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots_at(2), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots, {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })


        dot()
        error = KnownRootPathRenamedToKnownRootSubtreePath
        with ensure_blocked(self, error):
            svn.move(repo.ra('/foo/trunk'), repo.ra('/bar/trunk'), m='cp')

        dot()
        self.assertEqual(repo.roots, {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })


    @expected_component_depth(1)
    def test_02_evn_disabled_at_r2(self):
        repo = self.create_repo(multi=True)
        conf = repo.conf
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        make_std_layout(repo)

        dot()
        self.assertEqual(repo.roots_at(1), {
            '/foo/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            },
        })

        dot()
        self.assertEqual(repo.roots_at(2), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })

        dot()
        evnadmin.disable(repo.path)

        # Rename /foo/trunk to /bar/trunk/trunk.
        dot()
        svn.move(repo.ra('/foo/trunk'), repo.ra('/bar/trunk'), m='mv')

        dot()
        evnadmin.enable(repo.path)

        # Test for correct removal of /foo/trunk root at r1.
        dot()
        self.assertEqual(repo.roots_at(1), {
            '/foo/trunk/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
                'removal_method': 'removed_indirectly_via_rename',
                'removed': 3,
            },
        })

        dot()
        self.assertEqual(repo.roots_at(2), {
            '/foo/trunk/': { 'created': 1 },
            '/bar/trunk/': {
                'copies': {},
                'created': 2,
                'creation_method': 'created',
            },
        })

        # Make sure /foo/trunk no longer exists as a root.
        dot()
        self.assertEqual(repo.roots_at(3), {
            '/bar/trunk/': { 'created': 2 },
        })

        # Make sure the correct error was recorded.
        dot()
        errors = repo.revprops['evn']['errors']
        msg = KnownRootPathRenamedToKnownRootSubtreePath
        expected = { '/bar/trunk/trunk/': [msg] }
        self.assertEqual(errors, expected)

def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
