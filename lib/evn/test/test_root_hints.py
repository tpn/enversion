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

class TestRootHints(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo(component_depth='-1')
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        evnadmin.disable(repo.name)

        dot()
        svn.mkdir(repo.ra('/head/'), m='Create head')

        dot()
        error = 'repo is not set readonly'
        with ensure_fails(self, error):
            evnadmin.add_root_hint(
                repo.name,
                path='/head/',
                revision='1',
                root_type='trunk',
            )

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/head/',
            revision='1',
            root_type='trunk',
        )

        dot()
        error = 'hint already exists'
        with ensure_fails(self, error):
            evnadmin.add_root_hint(
                repo.name,
                path='/head/',
                revision='1',
                root_type='trunk',
            )

        dot()
        evnadmin.enable(repo.name)

        dot()
        roots_r1_expected = {
            '/head/': {
                'copies': {},
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots, roots_r1_expected)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        svn.mkdir(repo.ra('/stable/'), m='mkdir')

        dot()
        svn.copy(repo.ra('/head/'), repo.ra('/stable/1/'), m="Branch")

        dot()
        roots_r1_expected = {
            '/head/': {
                'copies': {
                    2: [('/stable/1/', 3)]
                },
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots_at(1), roots_r1_expected)

        dot()
        roots_r2_expected = {
            '/head/': { 'created': 1 },
            '/stable/1/': {
                'copies': {},
                'created': 3,
                'copied_from': ('/head/', 2),
                'creation_method': 'copied',
                'errors': [],
            },
        }
        self.assertEqual(repo.roots, roots_r2_expected)

        dot()
        # r4
        svn.mkdir(repo.ra('/stable/2-broken/'), m='Create broken branch')

        dot()
        roots_r3_expected = {
            '/head/': { 'created': 1 },
            '/stable/1/': { 'created': 3 },
        }
        self.assertEqual(repo.roots, roots_r3_expected)

        dot()
        evnadmin.add_branches_basedir(repo.name, basedir='/stable/')

        dot()
        error = e.BranchDirectoryCreatedManually
        with ensure_blocked(self, error):
            svn.mkdir(repo.ra('/stable/2-blocked/'), m='Create broken branch')

        dot()
        # r5
        svn.copy(repo.ra('/head/'), repo.ra('/stable/2/'), m="Branch")

        dot()
        roots_r1_expected = {
            '/head/': {
                'copies': {
                    2: [('/stable/1/', 3)],
                    4: [('/stable/2/', 5)],
                },
                'created': 1,
                'creation_method': 'created',
            }
        }
        self.assertEqual(repo.roots_at(1), roots_r1_expected)

        dot()
        roots_r5_expected = {
            '/head/': { 'created': 1 },
            '/stable/1/': { 'created': 3 },
            '/stable/2/': {
                'copies': {},
                'created': 5,
                'copied_from': ('/head/', 4),
                'creation_method': 'copied',
                'errors': [],
            },
        }
        self.assertEqual(repo.roots_at(5), roots_r5_expected)

        dot()
        evnadmin.remove_branches_basedir(repo.name, basedir='/stable/')

        dot()
        # r6
        svn.mkdir(repo.ra('/stable/3-broken/'), m='Create broken branch')

        # r7
        dot()
        svn.mkdir(repo.ra('/releng/'), m='Create directory')

        dot()
        evnadmin.add_tags_basedir(repo.name, basedir='/releng/')
        error = 'unknown path copied to valid root path'
        with ensure_blocked(self, error):
            svn.copy(
                repo.ra('/stable/3-broken/'),
                repo.ra('/releng/3/'),
                m='Create broken tag',
            )

        dot()
        evnadmin.disable(repo.name)

        dot()
        evnadmin.remove_tags_basedir(repo.name, basedir='/releng/')
        # r8
        svn.copy(
            repo.ra('/stable/3-broken/'),
            repo.ra('/releng/3/'),
            m='Create broken tag',
        )

        dot()
        # r9
        svn.copy(
            repo.ra('/stable/3-broken/'),
            repo.ra('/releng/3-take2/'),
            m='Create another broken tag',
        )

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        args = ('/stable/3-broken/', 5)
        error = 'no such path %s in revision %d' % args
        with ensure_fails(self, error):
            evnadmin.add_root_hint(
                repo.name,
                path='/stable/3-broken/',
                revision='5',
                root_type='branch',
            )

        dot()
        args = ('/stable/3-broken/', 7)
        error = "path %s already existed in revision %d;" % args
        with ensure_fails(self, error):
            evnadmin.add_root_hint(
                repo.name,
                path='/stable/3-broken/',
                revision='7',
                root_type='branch',
            )

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/stable/3-broken/',
            revision='6',
            root_type='branch',
        )

        dot()
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='/releng/3-take2/',
        )

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evnadmin.enable(repo.name)

        dot()
        roots_r6_expected = {
            '/head/': { 'created': 1 },
            '/stable/1/': { 'created': 3 },
            '/stable/2/': { 'created': 5 },
            '/stable/3-broken/': {
                'created': 6,
                'creation_method': 'created',
                'copies': {
                    7: [('/releng/3/', 8)],
                    8: [('/releng/3-take2/', 9)]
                },
            },
        }
        self.assertEqual(repo.roots_at(6), roots_r6_expected)

        dot()
        roots_r7_expected = {
            '/head/': { 'created': 1 },
            '/stable/1/': { 'created': 3 },
            '/stable/2/': { 'created': 5 },
            '/stable/3-broken/': { 'created': 6 },
        }
        self.assertEqual(repo.roots_at(7), roots_r7_expected)

        dot()
        evn_props_r8_expected = {
            'notes': {
                '/releng/3/': [ 'known root path copied to unknown path' ],
            },
            'roots': {
                '/head/': { 'created': 1 },
                '/stable/1/': { 'created': 3 },
                '/stable/2/': { 'created': 5 },
                '/stable/3-broken/': { 'created': 6 },
                '/releng/3/': {
                    'errors': [],
                    'copies': {},
                    'created': 8,
                    'creation_method': 'copied',
                    'copied_from': ('/stable/3-broken/', 7),
                },
            },
        }
        self.assertEqual(repo.revprops_at(8)['evn'], evn_props_r8_expected)

        dot()
        evn_props_r9_expected = {
            'notes': {
                '/releng/3-take2/': [ 'known root path copied to unknown path' ],
            },
            'roots': {
                '/head/': { 'created': 1 },
                '/stable/1/': { 'created': 3 },
                '/stable/2/': { 'created': 5 },
                '/stable/3-broken/': { 'created': 6 },
                '/releng/3/': { 'created': 8 },
            },
        }
        self.assertEqual(repo.revprops_at(9)['evn'], evn_props_r9_expected)

    def test_02_root_hint_for_trunk_subdir(self):
        # Test cp /trunk/foo /branches/foo-1.x creates root when
        # /branches/foo-1.x/ has a root hint created for it.
        pass


class TestManualBranchCreationRootHint(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        error = e.BranchDirectoryCreatedManually
        with ensure_blocked(self, error):
            svn.mkdir(repo.ra('/branches/1.x/'), m='Create branch manually')

        dot()
        evnadmin.disable(repo.name)
        svn.mkdir(repo.ra('/branches/1.x/'), m='Create branch manually2')

        dot()
        evn_props_r2_expected = {
            'errors': {
                '/branches/1.x/': [ e.BranchDirectoryCreatedManually ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(2)['evn'], evn_props_r2_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)
        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/1.x/',
            revision='2',
            root_type='branch',
        )
        dot()
        evnadmin.unset_repo_readonly(repo.name)
        evnadmin.analyze(repo.name)

        dot()
        evn_props_r2_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/1.x/': {
                    'created': 2,
                    'copies': {},
                    'creation_method': 'created',
                },
            },
        }
        self.assertEqual(repo.revprops_at(2)['evn'], evn_props_r2_expected)

class TestManualTagCreationRootHint(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        error = e.TagDirectoryCreatedManually
        with ensure_blocked(self, error):
            svn.mkdir(repo.ra('/tags/1.x/'), m='Create tag manually')

        dot()
        evnadmin.disable(repo.name)
        svn.mkdir(repo.ra('/tags/1.x/'), m='Create tag manually2')

        dot()
        evn_props_r2_expected = {
            'errors': {
                '/tags/1.x/': [ e.TagDirectoryCreatedManually ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(2)['evn'], evn_props_r2_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/tags/1.x/',
            revision='2',
            root_type='tag',
        )
        evnadmin.analyze(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r2_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/tags/1.x/': {
                    'created': 2,
                    'copies': {},
                    'creation_method': 'created',
                },
            },
        }
        self.assertEqual(repo.revprops_at(2)['evn'], evn_props_r2_expected)

        dot()
        svn.up(repo.wc)

        dot()
        error = e.TagModified
        tagdir = join_path(repo.wc, 'tags/1.x')
        with chdir(tagdir):
            tree = { 'test.txt': bulk_chargen(100) }
            repo.build(tree, prefix='tags/1.x')
            dot()
            svn.add('test.txt')
            with ensure_blocked(self, error):
                dot()
                svn.ci('test.txt', m='Modifying tag')

        dot()
        error = e.TagRemoved
        with ensure_blocked(self, error):
            svn.rm(repo.ra('tags/1.x'), m='Deleting tag.')

        dot()
        error = e.TagRenamed
        with ensure_blocked(self, error):
            svn.mv(repo.ra('tags/1.x'), repo.ra('tags/2.x'), m='Renaming tag.')

        dot()
        error = e.TagCopied
        with ensure_blocked(self, error):
            svn.copy(repo.ra('tags/1.x'), repo.ra('tags/2.x'), m='Copying tag.')

class TestUnknownCopiedToValidRootViaHint(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo(component_depth='-1')
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        svn.mkdir(repo.ra('/dev/'), m='Create dev branches area')
        svn.mkdir(repo.ra('/foo/'), m='Create foo')

        dot()
        svn.copy(repo.ra('/foo/'), repo.ra('/dev/foo/'), m='Branching...')
        self.assertEqual(repo.roots_at(3), {})

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/dev/foo/',
            revision='3',
            root_type='branch',
        )

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evnadmin.analyze(repo.name)
        roots_r3_expected = {
            '/dev/foo/': {
                'copies': {},
                'created': 3,
                'creation_method': 'copied',
                'copied_from': ('/foo/', 2),
            },
        }
        self.assertEqual(repo.roots_at(3), roots_r3_expected)

class TestUnknownRenamedToValidRootViaHint(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo(component_depth='-1')
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        svn.mkdir(repo.ra('/dev/'), m='Create dev branches area')
        svn.mkdir(repo.ra('/foo/'), m='Create foo')

        dot()
        svn.mv(repo.ra('/foo/'), repo.ra('/dev/foo/'), m='Branching...')
        self.assertEqual(repo.roots_at(3), {})

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/dev/foo/',
            revision='3',
            root_type='branch',
        )

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.analyze(repo.name)
        roots_r3_expected = {
            '/dev/foo/': {
                'copies': {},
                'created': 3,
                'creation_method': 'renamed',
                'renamed_from': ('/foo/', 2),
            },
        }
        self.assertEqual(repo.roots_at(3), roots_r3_expected)

class TestKnownRootSubtreeCopiedToValidRootViaHint(EnversionTest,
                                                   unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        tree = { 'foo/bar.txt': bulk_chargen(100) }
        repo.build(tree, prefix='trunk')
        with chdir(repo.wc):
            # r2
            svn.add('trunk/foo')
            svn.ci('trunk', m='Initializing foo component.')

        dot()
        error = 'known root subtree path copied to valid root path'
        with ensure_blocked(self, error):
            svn.cp(repo.ra('/trunk/foo/'), repo.ra('/branches/foo/'),m='Branch')

        dot()
        evnadmin.disable(repo.path)
        # r3
        svn.cp(repo.ra('/trunk/foo/'), repo.ra('/branches/foo/'), m='Branch')

        dot()
        evn_props_r3_expected = {
            'errors': {
                '/branches/foo/': [ error ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/foo/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r3_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/foo/': {
                    'copies': {},
                    'created': 3,
                    'creation_method': 'copied',
                    'copied_from': ('/trunk/foo/', 2),
                },
            },
        }
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

class TestKnownRootSubtreeRenamedToValidRootViaHint(EnversionTest,
                                                    unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        dot()
        tree = { 'foo/bar.txt': bulk_chargen(100) }
        repo.build(tree, prefix='trunk')
        with chdir(repo.wc):
            # r2
            svn.add('trunk/foo')
            svn.ci('trunk', m='Initializing foo component.')

        dot()
        error = 'known root subtree path renamed to valid root path'
        with ensure_blocked(self, error):
            svn.mv(repo.ra('/trunk/foo/'), repo.ra('/branches/foo/'),m='Branch')

        dot()
        evnadmin.disable(repo.path)
        # r3
        svn.mv(repo.ra('/trunk/foo/'), repo.ra('/branches/foo/'), m='Branch')

        dot()
        evn_props_r3_expected = {
            'errors': {
                '/branches/foo/': [ error ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/foo/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r3_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/foo/': {
                    'copies': {},
                    'created': 3,
                    'creation_method': 'renamed',
                    'renamed_from': ('/trunk/foo/', 2),
                },
            },
        }
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

class TestValidRootCopiedToValidRootViaHint(EnversionTest,
                                            unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin
        evnadmin.disable(repo.path)

        dot()
        tree = { 'foo/bar.txt': bulk_chargen(100) }
        repo.build(tree, prefix='branches')
        with chdir(repo.wc):
            # r2
            svn.add('branches/foo')
            svn.ci('branches/foo', m='Initializing foo component.')

        dot()
        evnadmin.enable(repo.path)
        error = 'valid root path copied to valid root path'
        with ensure_blocked(self, error):
            svn.cp(repo.ra('/branches/foo/'),
                   repo.ra('/branches/bar/'),
                   m='Branch')

        dot()
        evnadmin.disable(repo.path)
        # r3
        svn.cp(repo.ra('/branches/foo/'),
               repo.ra('/branches/bar/'), m='Branch')

        dot()
        evn_props_r3_expected = {
            'errors': {
                '/branches/bar/': [ error ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/bar/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r3_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/bar/': {
                    'copies': {},
                    'created': 3,
                    'creation_method': 'copied',
                    'copied_from': ('/branches/foo/', 2),
                },
            },
        }
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

class TestValidRootRenamedToValidRootViaHint(EnversionTest,
                                             unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin
        evnadmin.disable(repo.path)

        dot()
        tree = { 'foo/bar.txt': bulk_chargen(100) }
        repo.build(tree, prefix='branches')
        with chdir(repo.wc):
            # r2
            svn.add('branches/foo')
            svn.ci('branches/foo', m='Initializing foo component.')

        dot()
        evnadmin.enable(repo.path)
        error = 'valid root path renamed to valid root path'
        with ensure_blocked(self, error):
            svn.mv(repo.ra('/branches/foo/'),
                   repo.ra('/branches/bar/'),
                   m='Branch')

        dot()
        evnadmin.disable(repo.path)
        # r3
        svn.mv(repo.ra('/branches/foo/'),
               repo.ra('/branches/bar/'), m='Branch')

        dot()
        evn_props_r3_expected = {
            'errors': {
                '/branches/bar/': [ error ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/bar/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r3_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/bar/': {
                    'copies': {},
                    'created': 3,
                    'creation_method': 'renamed',
                    'renamed_from': ('/branches/foo/', 2),
                },
            },
        }
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

class TestValidRootSubtreeCopiedToValidRootViaHint(EnversionTest,
                                                   unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin
        evnadmin.disable(repo.path)

        dot()
        tree = { 'foo/moo/bar.txt': bulk_chargen(100) }
        repo.build(tree, prefix='branches')
        with chdir(repo.wc):
            # r2
            svn.add('branches/foo')
            svn.ci('branches/foo', m='Initializing foo component.')

        dot()
        evnadmin.enable(repo.path)
        error = 'valid root subtree path copied to valid root path'
        with ensure_blocked(self, error):
            svn.cp(repo.ra('/branches/foo/moo'),
                   repo.ra('/branches/bar/'),
                   m='Branch')

        dot()
        evnadmin.disable(repo.path)
        # r3
        svn.cp(repo.ra('/branches/foo/moo'),
               repo.ra('/branches/bar/'), m='Branch')

        dot()
        evn_props_r3_expected = {
            'errors': {
                '/branches/bar/': [ error ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/bar/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r3_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/bar/': {
                    'copies': {},
                    'created': 3,
                    'creation_method': 'copied',
                    'copied_from': ('/branches/foo/moo/', 2),
                },
            },
        }
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

class TestValidRootSubtreeRenamedToValidRootViaHint(EnversionTest,
                                                    unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin
        evnadmin.disable(repo.path)

        dot()
        tree = { 'foo/moo/bar.txt': bulk_chargen(100) }
        repo.build(tree, prefix='branches')
        with chdir(repo.wc):
            # r2
            svn.add('branches/foo')
            svn.ci('branches/foo', m='Initializing foo component.')

        dot()
        evnadmin.enable(repo.path)
        error = 'valid root subtree path renamed to valid root path'
        with ensure_blocked(self, error):
            svn.mv(repo.ra('/branches/foo/moo'),
                   repo.ra('/branches/bar/'),
                   m='Branch')

        dot()
        evnadmin.disable(repo.path)
        # r3
        svn.mv(repo.ra('/branches/foo/moo/'),
               repo.ra('/branches/bar/'), m='Branch')

        dot()
        evn_props_r3_expected = {
            'errors': {
                '/branches/bar/': [ error ],
            },
            'roots': {
                '/trunk/': { 'created': 1 },
            },
        }
        evnadmin.enable(repo.name)
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

        dot()
        evnadmin.set_repo_readonly(repo.name)

        dot()
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/bar/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

        dot()
        evnadmin.unset_repo_readonly(repo.name)

        dot()
        evn_props_r3_expected = {
            'roots': {
                '/trunk/': { 'created': 1 },
                '/branches/bar/': {
                    'copies': {},
                    'created': 3,
                    'creation_method': 'renamed',
                    'renamed_from': ('/branches/foo/moo/', 2),
                },
            },
        }
        self.assertEqual(repo.revprops_at(3)['evn'], evn_props_r3_expected)

class TestKnownRootCopiedToWithoutRootExclusion(EnversionTest,
                                                unittest.TestCase):
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

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.cp('trunk', 'other/foobar')
            svn.cp('branches/1.x', 'other/1.x')
            svn.cp('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag copied',
                    'known root path copied to unknown path',
                ],
                '/other/1.x/': [ 'known root path copied to unknown path' ],
                '/other/foobar/': [ 'known root path copied to unknown path' ],
            },
            'roots': {
                '/branches/1.x/': { 'created': 3 },
                '/other/1.0/': {
                    'copied_from': ('/tags/1.0/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'copied',
                    'errors': [
                        'tag copied',
                        'known root path copied to unknown path',
                    ],
                },
                '/other/1.x/': {
                    'copied_from': ('/branches/1.x/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'copied',
                    'errors': ['known root path copied to unknown path'],
                },
                '/other/foobar/': {
                    'copied_from': ('/trunk/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'copied',
                    'errors': ['known root path copied to unknown path'],
                },
                '/tags/1.0/': { 'created': 4 },
                '/trunk/': { 'created': 1 }
            }
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)

class TestKnownRootCopiedWithRootExclusion(EnversionTest,
                                           unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='/other/',
        )

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.cp('trunk', 'other/foobar')
            svn.cp('branches/1.x', 'other/1.x')
            svn.cp('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag copied',
                    'known root path copied to unknown path',
                ],
                '/other/1.x/': [ 'known root path copied to unknown path' ],
                '/other/foobar/': [ 'known root path copied to unknown path' ],
            },
            'roots': {
                '/branches/1.x/': { 'created': 3 },
                '/tags/1.0/': { 'created': 4 },
                '/trunk/': { 'created': 1 }
            }
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)

        #svn.cp(repo.ra('/trunk/'), repo.ra('/other/foobar/'))
        #svn.cp(repo.ra('/branches/1.x/'), repo.ra('/other/1.x/'))
        #svn.cp(repo.ra('/tags/1.0/'), repo.ra('/other/1.0/'))

class TestKnownRootRenamedWithRootExclusion(EnversionTest,
                                            unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='/other/',
        )

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.mv('trunk', 'other/foobar')
            svn.mv('branches/1.x', 'other/1.x')
            svn.mv('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag renamed',
                    'known root path renamed to unknown path',
                ],
                '/other/1.x/': [
                    'known root path renamed to unknown path',
                    'branch renamed to unknown',
                ],
                '/other/foobar/': [
                    'known root path renamed to unknown path',
                    'trunk renamed to unknown path',
                ],
            },
            'roots': { }
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)

class TestKnownRootRenamedWithRootExclusionRegex1(EnversionTest,
                                                  unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='other',
        )

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.mv('trunk', 'other/foobar')
            svn.mv('branches/1.x', 'other/1.x')
            svn.mv('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag renamed',
                    'known root path renamed to unknown path',
                ],
                '/other/1.x/': [
                    'known root path renamed to unknown path',
                    'branch renamed to unknown',
                ],
                '/other/foobar/': [
                    'known root path renamed to unknown path',
                    'trunk renamed to unknown path',
                ],
            },
            'roots': {
                '/other/1.0/': {
                    'renamed_from': ('/tags/1.0/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'renamed',
                    'errors': [
                        'tag renamed',
                        'known root path renamed to unknown path',
                    ],
                },
                '/other/1.x/': {
                    'renamed_from': ('/branches/1.x/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'renamed',
                    'errors': [
                        'known root path renamed to unknown path',
                        'branch renamed to unknown',
                    ],
                },
                '/other/foobar/': {
                    'renamed_from': ('/trunk/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'renamed',
                    'errors': [
                        'known root path renamed to unknown path',
                        'trunk renamed to unknown path',
                    ],
                },
            },
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)

class TestKnownRootRenamedWithRootExclusionRegex2(EnversionTest,
                                                  unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='.*other/.*',
        )

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.mv('trunk', 'other/foobar')
            svn.mv('branches/1.x', 'other/1.x')
            svn.mv('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag renamed',
                    'known root path renamed to unknown path',
                ],
                '/other/1.x/': [
                    'known root path renamed to unknown path',
                    'branch renamed to unknown',
                ],
                '/other/foobar/': [
                    'known root path renamed to unknown path',
                    'trunk renamed to unknown path',
                ],
            },
            'roots': { }
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)

class TestKnownRootRenamedWithRootExclusionRegex3(EnversionTest,
                                                  unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='^/oth',
        )

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.mv('trunk', 'other/foobar')
            svn.mv('branches/1.x', 'other/1.x')
            svn.mv('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag renamed',
                    'known root path renamed to unknown path',
                ],
                '/other/1.x/': [
                    'known root path renamed to unknown path',
                    'branch renamed to unknown',
                ],
                '/other/foobar/': [
                    'known root path renamed to unknown path',
                    'trunk renamed to unknown path',
                ],
            },
            'roots': { }
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)

class TestKnownRootRenamedWithRootExclusionRegex4(EnversionTest,
                                                  unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        svn.mkdir(repo.ra('/other/'), m='Creating other directory')
        evnadmin.add_root_exclusion(
            repo.name,
            root_exclusion='/[abcdo]{1,1}the.*',
        )

        dot()
        evnadmin.enable(repo.path)
        svn.cp(repo.ra('/trunk/'), repo.ra('/branches/1.x/'), m='Branching')
        svn.cp(repo.ra('/branches/1.x/'), repo.ra('/tags/1.0/'), m='Tagging')

        # Lazy (quick) test of roots.
        dot()
        expected_roots = set(('/trunk/', '/branches/1.x/', '/tags/1.0/'))
        actual_roots = set(repo.roots.keys())
        self.assertEqual(expected_roots, actual_roots)

        # Add ourselves as a repo admin so that we can force through the next
        # commit.
        dot()
        evnadmin.add_repo_admin(repo.name, username=svn.username)
        expected = 'yes'
        actual = evnadmin.is_repo_admin(repo.name, username=svn.username)
        self.assertEqual(expected, actual)

        dot()
        with chdir(repo.wc):
            svn.up()
            svn.mv('trunk', 'other/foobar')
            svn.mv('branches/1.x', 'other/1.x')
            svn.mv('tags/1.0', 'other/1.0')
            svn.ci(m='IGNORE ERRORS')

        evn_props_r5_expected = {
            'errors': {
                '/other/1.0/': [
                    'tag renamed',
                    'known root path renamed to unknown path',
                ],
                '/other/1.x/': [
                    'known root path renamed to unknown path',
                    'branch renamed to unknown',
                ],
                '/other/foobar/': [
                    'known root path renamed to unknown path',
                    'trunk renamed to unknown path',
                ],
            },
            'roots': { }
        }
        self.assertEqual(repo.revprops_at(5)['evn'], evn_props_r5_expected)


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
