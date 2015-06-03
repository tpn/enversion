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
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/1.x/',
            revision='2',
            root_type='branch',
        )
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
        evnadmin.add_root_hint(
            repo.name,
            path='/tags/1.x/',
            revision='2',
            root_type='tag',
        )
        evnadmin.analyze(repo.name)

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

class TestUnknownToValidRootViaHint(EnversionTest, unittest.TestCase):
    def test_01_copy(self):
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
        evnadmin.add_root_hint(
            repo.name,
            path='/dev/foo/',
            revision='3',
            root_type='branch',
        )

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

    def test_02_rename(self):
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
        evnadmin.add_root_hint(
            repo.name,
            path='/dev/foo/',
            revision='3',
            root_type='branch',
        )

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
    def test_01_copy(self):
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
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/foo/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

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
    def test_01_rename(self):
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
        evnadmin.add_root_hint(
            repo.name,
            path='/branches/foo/',
            revision='3',
            root_type='branch',
        )
        evnadmin.enable(repo.name)

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


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
