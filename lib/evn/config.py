
#=============================================================================
# Imports
#=============================================================================
import os
import re
import sys
import stat

from os.path import abspath, dirname

from textwrap import dedent

from ConfigParser import (
    NoOptionError,
    NoSectionError,
    RawConfigParser,
)

from evn.path import join_path

#=============================================================================
# Classes
#=============================================================================
class ConfigError(Exception):
    pass

class Config(RawConfigParser):
    def __init__(self, repo_name=None):
        RawConfigParser.__init__(self)
        if repo_name is not None:
            assert isinstance(repo_name, str)
        self.__repo_name = repo_name

        d = dirname(abspath(__file__))
        f = join_path(d, 'admin', 'cli.py')
        self.__python_evn_module_dir = d
        self.__python_evn_admin_cli_file_fullpath = f

        self.__load_defaults()
        self.__multiline_pattern = re.compile(r'([^\s].*?)([\s]+\\)?')
        self.__validate()

    @property
    def python_evn_module_dir(self):
        return self.__python_evn_module_dir

    @property
    def python_evn_admin_cli_file_fullpath(self):
        return self.__python_evn_admin_cli_file_fullpath

    @property
    def repo_name(self):
        return self.__repo_name

    @repo_name.setter
    def repo_name(self, value):
        assert isinstance(value, str)
        self.__repo_name = value

    def load(self, filename=None):
        self.__filename = filename

        self.__files = [
            f for f in (
                '/etc/evn.conf',
                '/usr/local/etc/evn.conf',
                '/opt/etc/evn.conf',
                '/opt/local/etc/evn.conf',
                os.environ.get('EVN_CONF') or None,
                filename or None,
            ) if f
        ]
        self.read(self.files)
        self.__validate()

    def __validate(self):
        dummy = self.unix_hook_permissions

    @property
    def files(self):
        return self.__files

    def get_multiline_to_single_line(self, section, name):
        return (
            self.get(section, name)
                .replace(os.linesep, '')
                .replace('\\', '')
                .strip()
        )

    def get_multiline(self, section, name):
        # I'm sure there's a more efficient way of doing this.
        value = self.get(section, name)
        if not value:
            return

        output = list()
        lines = value.split(os.linesep)
        pattern = re.compile(r'(.+?)([\s]*\\)')
        for line in lines:
            if line.endswith('\\'):
                matches = pattern.findall(line)
                if matches:
                    output.append(matches[0][0])
            elif line:
                output.append(line)

        joined = '\n'.join(output)
        return joined

    def get_multiline_csv_as_list(self, section, name):
        return self._csv_as_list(
            self.get_multiline_to_single_line(section, name)
        )

    def get_csv_as_list(self, section, name):
        return self._csv_as_list(self.get(section, name))
        return [ n.strip() for n in csv.split(',') ]

    def _csv_as_list(self, csv):
        return [ n.strip() for n in csv.split(',') ]

    def __load_defaults(self):
        logfmt = "%(asctime)s:%(name)s:%(levelname)s:%(message)s"

        self.add_section('main')
        self.set('main', 'max-revlock-waits', '3')
        self.set('main', 'verbose', 'off')
        self.set('main', 'admins', '')
        self.set('main', 'python', sys.executable)
        self.set('main', 'propname-prefix', 'evn')
        self.set('main', 'remote-debug-host', 'localhost')
        self.set('main', 'remote-debug-port', '0')
        self.set('main', 'remote-debug-complete-key', 'tab')
        self.set('main', 'svn-hook-enabled-prefix', 'evn')
        self.set('main', 'svn-hook-remote-debug-suffix', 'remote-debug')
        self.set('main', 'svnadmin-create-flags', ''),

        self.set(
            'main',
            'hook-names',
            ','.join((
                'post-commit',
                'post-lock',
                'post-revprop-change',
                'post-unlock',
                'pre-commit',
                'pre-lock',
                'pre-revprop-change',
                'pre-unlock',
                'start-commit',
            )),
        )

        self.set(
            'main',
            'unix-hook-autoexpand-env-vars',
            ','.join((
                'HOME',
                'USER',
                'PATH',
                'SHELL',
                'OSTYPE',
                'INPUTRC',
                'EVN_CONF',
                'PYTHONPATH',
                'LDLIBRARYPATH',
            )),
        )

        self.set(
            'main',
            'unix-hook-force-env-vars',
            ','.join((
                'SVN_I_LOVE_CORRUPTED_WORKING_COPIES'
                '_SO_DISABLE_CHECK_FOR_WC_NG=yes',
            )),
        )
        self.set(
            'main',
            'unix-evn-hook-code-for-testing-if-svn-hook-is-enabled',
            '[ ! -f "$(dirname $0)/{0}-$1" ] && exit 0'
        )
        self.set(
            'main',
            'unix-evn-run-hook-code',
            '"{0}" "{1}" run-hook $*',
        )
        self.set(
            'main',
            'unix-svn-hook-syntax-for-invoking-evn-hook',
            '$(dirname "$0")/{0} $(basename "$0") $* || exit 1'
        )

        self.set('main', 'unix-hook-extension', '')
        self.set('main', 'unix-evn-hook-file-name', 'evn.sh')
        self.set(
            'main',
            'unix-svn-hook-code-empty',
            '#!/bin/sh \\\nexit 0\n'
        )
        self.set(
            'main',
            'unix-hook-permissions',
            dedent(""" \
                S_IRUSR | S_IWUSR | S_IXUSR |   # u=rwx (7)
                S_IRGRP | S_IXGRP |             # g=r-x (5)
                S_IROTH | S_IXOTH               # o=r-x (5)""")
        )

        # Windows hook stuff.
        self.set('main', 'windows-evn-hook-file-name', 'evn.bat')
        self.set('main', 'windows-svn-hook-code-empty', 'exit /b 0\n')
        self.set(
            'main',
            'windows-evn-hook-code-for-testing-if-svn-hook-is-enabled',
            'if not exist "%%~dp0{0}-%%1" exit /b 0'
        )
        self.set(
            'main',
            'windows-evn-run-hook-code',
            '"{0}" "{1}" run-hook %%*',
        )
        self.set(
            'main',
            'windows-svn-hook-syntax-for-invoking-evn-hook',
            'call "%%~dp0{0}" %%~n0 %%*'
        )

        self.add_section('hook-override')
        self.set('hook-override', 'enabled', 'yes')
        self.set('hook-override', 'authz-file', 'conf/authz')
        self.set('hook-override', 'authz-access-mask', '')

        self.set('hook-override', 'entitlements-filename', '')
        self.set('hook-override', 'group-name', '')

    def _g(self, name):
        return self.get('main', name)

    def get(self, _, option):
        if self.repo_name is not None:
            if self.repo_name == 'main':
                section = 'repo:main'
            else:
                section = self.repo_name
        else:
            section = 'main'

        try:
            return RawConfigParser.get(self, section, option)
        except (NoSectionError, NoOptionError):
            return RawConfigParser.get(self, 'main', option)

    def _get(self, section, option):
        return RawConfigParser.get(self, section, option)

    @property
    def propname_prefix(self):
        return self._g('propname-prefix')

    @property
    def remote_debug_host(self):
        return self._g('remote-debug-host')

    @property
    def remote_debug_port(self):
        return int(self._g('remote-debug-port'))

    @property
    def remote_debug_complete_key(self):
        return self._g('remote-debug-complete-key')

    @property
    def svn_hook_enabled_prefix(self):
        return self._g('svn-hook-enabled-prefix')

    @property
    def svn_hook_remote_debug_suffix(self):
        return self._g('svn-hook-remote-debug-suffix')

    @property
    def platform_prefix(self):
        return 'windows' if os.name == 'nt' else 'unix'

    def _p(self, n):
        return n % self.platform_prefix

    @property
    def evn_hook_code_for_testing_if_svn_hook_is_enabled(self):
        return self.get(
            'main',
            self._p('%s-evn-hook-code-for-testing-if-svn-hook-is-enabled')
        ).format(self.get('main', 'svn-hook-enabled-prefix'))

    @property
    def python(self):
        return self.get('main', 'python')

    @property
    def svn_hook_code_empty(self):
        return self.get_multiline(
            'main', self._p('%s-svn-hook-code-empty'),
        )

    @property
    def evn_run_hook_code(self):
        return self.get(
            'main', self._p('%s-evn-run-hook-code'),
        ).format(self.python, self.python_evn_admin_cli_file_fullpath)

    @property
    def svn_hook_syntax_for_invoking_evn_hook(self):
        return self.get(
            'main', self._p('%s-svn-hook-syntax-for-invoking-evn-hook')
        ).format(self.evn_hook_file_name)

    @property
    def evn_hook_file_name(self):
        return self.get('main', self._p('%s-evn-hook-file-name'))

    @property
    def hook_names(self):
        return set(self.get_csv_as_list('main', 'hook-names'))

    @property
    def unix_hook_permissions(self):
        text = self.get('main', 'unix-hook-permissions')
        names = re.findall('(S_[A-Z]+)', text)
        perms = None
        for n in names:
            try:
                p = getattr(stat, n)
            except AttributeError:
                raise ConfigError(
                    'main',
                    'unix-hook-permissions',
                    "invalid permission: '%s'" % p
                )
            if not perms:
                perms = p
            else:
                perms = (perms | p)

        return perms

    @property
    def svnadmin_create_flags(self):
        return self.get('main', 'svnadmin-create-flags')

# vim:set ts=8 sw=4 sts=4 tw=78 et:
