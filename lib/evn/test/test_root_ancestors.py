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

class TestRootAncestorRemoved(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        with chdir(repo.wc):
            svn.mkdir('other')
            svn.mkdir('keep')
            svn.ci()

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

        dot()
        error = e.RootAncestorRemoved
        with ensure_blocked(self, error):
            svn.rm(repo.ra('/other/'))

        dot()
        svn.rm(repo.ra('/other/'), m='IGNORE ERRORS')

        evn_props_r6_expected = {
            'errors': {
                '/other/': [
                    e.RootAncestorRemoved,
                    e.MultipleRootsAffectedByRemove,
                ],
            },
            'roots' : {
                '/branches/1.x/': {'created': 3},
                '/tags/1.0/': {'created': 4},
                '/trunk/': {'created': 1},
            }
        }
        self.assertEqual(repo.revprops_at(6)['evn'], evn_props_r6_expected)

        evn_brprops_expected_after_r6 = {
            'component_depth': 0,
            'last_rev': 6,
            'version': 1,
            'root_ancestor_actions': {
                '/other/': {
                    6: [
                        {
                            'action': 'removed',
                            'num_roots_removed': 3,
                        },
                    ],
                },
            },
        }
        self.assertEqual(
            repo.revprops_at(0)['evn'],
            evn_brprops_expected_after_r6,
        )

class TestRootAncestorReplacedWithMkdir(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        svnmucc = repo.svnmucc
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        with chdir(repo.wc):
            svn.mkdir('other')
            svn.mkdir('keep')
            svn.ci()

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

        dot()
        error = e.InvalidTopLevelRepoDirectoryCreated
        with ensure_blocked(self, error):
            svnmucc.rm(repo.ra('/other/'), 'mkdir', repo.ra('/other/'))

        dot()
        evnadmin.set_repo_component_depth(repo.name, component_depth='-1')

        dot()
        error = e.RootAncestorReplaced
        with ensure_blocked(self, error):
            svnmucc.rm(repo.ra('/other/'), 'mkdir', repo.ra('/other/'))

        dot()
        svnmucc.rm(repo.ra('/other/'), 'mkdir', repo.ra('/other/'),
                   m='IGNORE ERRORS')

        evn_props_r6_expected = {
            'errors': {
                '/other/': [ e.RootAncestorReplaced ],
            },
            'roots' : {
                '/branches/1.x/': {'created': 3},
                '/tags/1.0/': {'created': 4},
                '/trunk/': {'created': 1},
            }
        }
        self.assertEqual(repo.revprops_at(6)['evn'], evn_props_r6_expected)

        evn_brprops_expected_after_r6 = {
            'last_rev': 6,
            'version': 1,
            'root_ancestor_actions': {
                '/other/': {
                    6: [
                        {
                            'action': 'replaced',
                            'num_roots_removed': 3,
                        },
                    ],
                },
            },
        }
        self.assertEqual(
            repo.revprops_at(0)['evn'],
            evn_brprops_expected_after_r6,
        )

class TestRootAncestorReplacedWithAncestorCopyOfSelf(EnversionTest,
                                                     unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        svnmucc = repo.svnmucc
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        with chdir(repo.wc):
            svn.mkdir('other')
            svn.mkdir('keep')
            svn.ci()

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

        dot()
        error = e.InvalidTopLevelRepoDirectoryCreated
        with ensure_blocked(self, error):
            svnmucc.rm(repo.ra('/other/'), 'mkdir', repo.ra('/other/'))

        dot()
        evnadmin.set_repo_component_depth(repo.name, component_depth='-1')

        dot()
        error = 'root ancestor path copied via replace to root ancestor path'
        with ensure_blocked(self, error):
            svnmucc.rm(
                repo.ra('/other/'),
                'cp', '5', repo.ra('/other/'), repo.ra('/other/')
            )

        dot()
        svnmucc.rm(
            repo.ra('/other/'),
            'cp', '5', repo.ra('/other/'), repo.ra('/other/'),
            m='IGNORE ERRORS',
        )

        evn_props_r6_expected = {
            'errors': {
                '/other/': [ error, ]
            },
            'roots' : {
                '/other/1.0/': {
                    'copied_indirectly_from': ('/other/', '/other/'),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'copied_indirectly',
                    'errors': [ error ],
                },
                '/other/1.x/': {
                    'copied_indirectly_from': ('/other/', '/other/'),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'copied_indirectly',
                    'errors': [ error ],
                },
                '/other/foobar/': {
                    'copied_indirectly_from': ('/other/', '/other/'),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'copied_indirectly',
                    'errors': [ error ],
                },
                '/branches/1.x/': {'created': 3},
                '/tags/1.0/': {'created': 4},
                '/trunk/': {'created': 1},
            }
        }
        self.assertEqual(repo.revprops_at(6)['evn'], evn_props_r6_expected)

        evn_brprops_expected_after_r6 = {
            'last_rev': 6,
            'version': 1,
            'root_ancestor_actions': {
                '/other/': {
                    6: [
                        {
                            'action': 'replaced',
                            'num_roots_removed': 3,
                        },
                        {
                            'action': 'copied',
                            'copied_from': ('/other/', 5),
                            'num_origin_roots': 3,
                            'num_roots_created': 3,
                        },
                    ],
                },
            },
        }
        self.assertEqual(
            repo.revprops_at(0)['evn'],
            evn_brprops_expected_after_r6,
        )

class TestRootAncestorReplacedWithAncestorCopyOfBranches(EnversionTest,
                                                         unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        svnmucc = repo.svnmucc
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        with chdir(repo.wc):
            svn.mkdir('other')
            svn.mkdir('keep')
            svn.ci()

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

        dot()
        error = e.InvalidTopLevelRepoDirectoryCreated
        with ensure_blocked(self, error):
            svnmucc.rm(repo.ra('/other/'), 'mkdir', repo.ra('/other/'))

        dot()
        evnadmin.set_repo_component_depth(repo.name, component_depth='-1')

        dot()
        error = 'root ancestor path copied via replace to root ancestor path'
        with ensure_blocked(self, error):
            svnmucc.rm(
                repo.ra('/other/'),
                'cp', '5', repo.ra('/branches/'), repo.ra('/other/')
            )

        dot()
        svnmucc.rm(
            repo.ra('/other/'),
            'cp', '5', repo.ra('/branches/'), repo.ra('/other/'),
            m='IGNORE ERRORS',
        )

        evn_props_r6_expected = {
            'errors': {
                '/other/': [ error, ]
            },
            'roots' : {
                '/other/1.x/': {
                    'copied_indirectly_from': ('/branches/', '/other/'),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'copied_indirectly',
                    'errors': [ error ],
                },
                '/branches/1.x/': {'created': 3},
                '/tags/1.0/': {'created': 4},
                '/trunk/': {'created': 1},
            }
        }
        self.assertEqual(repo.revprops_at(6)['evn'], evn_props_r6_expected)

        evn_brprops_expected_after_r6 = {
            'last_rev': 6,
            'version': 1,
            'root_ancestor_actions': {
                '/other/': {
                    6: [
                        {
                            'action': 'replaced',
                            'num_roots_removed': 3,
                        },
                        {
                            'action': 'copied',
                            'copied_from': ('/branches/', 5),
                            'num_origin_roots': 1,
                            'num_roots_created': 1,
                        },
                    ],
                },
            },
        }
        self.assertEqual(
            repo.revprops_at(0)['evn'],
            evn_brprops_expected_after_r6,
        )


class TestRootAncestorRenamed(EnversionTest, unittest.TestCase):
    def test_01(self):
        repo = self.create_repo()
        svn = repo.svn
        evnadmin = repo.evnadmin

        # Disable so we can mkdir ^/other
        dot()
        evnadmin.disable(repo.path)
        with chdir(repo.wc):
            svn.mkdir('other')
            svn.mkdir('keep')
            svn.ci()

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

        dot()
        svn.mv(repo.ra('/other/'), repo.ra('/other.bak/'), m='IGNORE ERRORS')

        evn_props_r6_expected = {
            'errors': {
                '/other.bak/': ['root ancestor path renamed to unknown path'],
            },
            'roots' : {
                '/other.bak/1.0/': {
                    'renamed_indirectly_from': ('/other/', '/other.bak/'),
                    'renamed_from': ('/other/1.0/', 5),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'renamed_indirectly',
                    'errors': ['root ancestor path renamed to unknown path'],
                },
                '/other.bak/1.x/': {
                    'renamed_indirectly_from': ('/other/', '/other.bak/'),
                    'renamed_from': ('/other/1.x/', 5),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'renamed_indirectly',
                    'errors': ['root ancestor path renamed to unknown path'],
                },
                '/other.bak/foobar/': {
                    'renamed_indirectly_from': ('/other/', '/other.bak/'),
                    'renamed_from': ('/other/foobar/', 5),
                    'copies': {},
                    'created': 6,
                    'creation_method': 'renamed_indirectly',
                    'errors': ['root ancestor path renamed to unknown path'],
                },
                '/branches/1.x/': {'created': 3},
                '/tags/1.0/': {'created': 4},
                '/trunk/': {'created': 1},
            }
        }
        self.assertEqual(repo.revprops_at(6)['evn'], evn_props_r6_expected)

        evn_brprops_expected_after_r6 = {
            'component_depth': 0,
            'last_rev': 6,
            'version': 1,
            'root_ancestor_actions': {
                '/other.bak/': {
                    6: [
                        {
                            'action': 'renamed',
                            'renamed_from': '/other/',
                            'num_origin_roots': 3,
                            'num_roots_created': 3,
                            'num_roots_removed': 3,
                        },
                    ],
                },
            },
        }
        self.assertEqual(
            repo.revprops_at(0)['evn'],
            evn_brprops_expected_after_r6,
        )


def main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
