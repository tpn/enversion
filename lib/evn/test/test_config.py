#===============================================================================
# Imports
#===============================================================================
import unittest
import os.path

from tempfile import (
    NamedTemporaryFile,
)

from textwrap import (
    dedent,
)

from evn.config import (
    Config,
)

from evn.test import (
    EnversionTest,
)

from evn.test.dot import (
    dot,
)

#===============================================================================
# Helper Methods
#===============================================================================
def suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestBasicManualRepoOverrideLogic,
        TestRepoOverride,
    )

#===============================================================================
# Test Classes
#===============================================================================
class TestBasicManualRepoOverrideLogic(EnversionTest, unittest.TestCase):
    """
    This was the first test ever implemented and it's definitely showing its
    age as it's barely useful anymore.
    """
    def create_conf(self, repo_name=None):
        text = dedent(
            """
            [main]
            verbose=1
            fallback=1

            [foo]
            verbose=foo

            [bar]
            verbose=bar

            [repo:main]
            verbose=main
            """
        )
        tmpfile = NamedTemporaryFile()
        with open(tmpfile.name, 'w') as f:
            f.write(text)
            f.flush()
            f.close()

        conf = Config()
        if repo_name:
            conf._repo_name = repo_name

        conf.load(tmpfile.name)
        return conf

    def test_repo_override(self):
        c = self.create_conf()

        self.assertEqual(c._g('verbose'), '1')

        c._repo_name = 'foo'
        self.assertEqual(c._g('verbose'), 'foo')

        c._repo_name = 'bar'
        self.assertEqual(c._g('verbose'), 'bar')

        c._repo_name = 'main'
        self.assertEqual(c._g('verbose'), 'main')

    def test_repo_override2(self):
        c = self.create_conf('foo')
        self.assertEqual(c._g('verbose'), 'foo')

        c._repo_name = 'bar'
        self.assertEqual(c._g('verbose'), 'bar')

        c._repo_name = 'main'
        self.assertEqual(c._g('verbose'), 'main')

        self.assertEqual(c._get('main', 'verbose'), '1')

    def test_repo_fallback(self):
        c = self.create_conf('bar')

        self.assertEqual(c._g('fallback'), '1')

class TestRepoOverride(EnversionTest, unittest.TestCase):
    def test_01_writable_override(self):
        repo = self.create_repo(checkout=False)
        conf = repo.conf

        self.assertEqual(conf.modifications, {})

        expected_mods = {
            'main': {
                'custom-hook-classname': 'FoobarCustomHook',
            }
        }

        conf.set('main', 'custom-hook-classname', 'FoobarCustomHook')
        self.assertEqual(conf.modifications, expected_mods)
        dot()

        conf.save()
        self.assertEqual(conf.modifications, expected_mods)
        dot()

        conf = repo.reload_conf()
        path = conf.actual_repo_conf_filenames[0]
        with open(path, 'r') as f:
            actual = f.read()
        expected = "[main]\ncustom-hook-classname = FoobarCustomHook\n\n"
        self.assertEqual(actual, expected)
        dot()

        # Make sure the modifications are still detected/preserved when
        # written to an explicit override file.
        self.assertEqual(conf.modifications, expected_mods)
        dot()

        expected_mods = {
            'main': {
                'foo': 'bar',
                'custom-hook-classname': 'FoobarCustomHook',
            }
        }

        conf.set('main', 'foo', 'bar')
        self.assertEqual(conf.modifications, expected_mods)
        dot()

        conf.save()
        self.assertEqual(conf.modifications, expected_mods)
        dot()

        conf = repo.reload_conf()
        path = conf.actual_repo_conf_filenames[0]
        with open(path, 'r') as f:
            actual = f.read()
        expected = (
            "[main]\n"
            "foo = bar\n"
            "custom-hook-classname = FoobarCustomHook\n"
            "\n"
        )
        self.assertEqual(actual, expected)
        dot()


def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
