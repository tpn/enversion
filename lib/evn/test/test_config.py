#=============================================================================
# Imports
#=============================================================================
import unittest

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

#=============================================================================
# Helper Methods
#=============================================================================
def suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(
        TestConfig,
    )

#=============================================================================
# Test Classes
#=============================================================================
class TestConfig(EnversionTest, unittest.TestCase):
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

def main():
    runner = unittest.TextTestRunner()
    runner.run(suite())

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
