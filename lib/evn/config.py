#===============================================================================
# Imports
#===============================================================================
import os
import re
import sys
import copy
import stat

from os.path import (
    isdir,
    abspath,
    dirname,
    expanduser,
)

from itertools import chain

from textwrap import dedent

from ConfigParser import (
    NoOptionError,
    NoSectionError,
    RawConfigParser,
)

from evn.util import (
    chdir,
    try_int,
    memoize,
    load_class,
    file_exists_and_not_empty,
    first_writable_file_that_preferably_exists,
)

from evn.path import (
    join_path,
    format_dir,
)

#===============================================================================
# Globals
#===============================================================================
CONFIG = None

#===============================================================================
# Exceptions
#===============================================================================
class ConfigError(BaseException):
    pass

class NoConfigObjectCreated(BaseException):
    pass

class RepositoryNotSet(BaseException):
    pass

class NoModificationsMade(BaseException):
    pass

#===============================================================================
# Helpers
#===============================================================================
def get_config():
    global CONFIG
    if not CONFIG:
        raise NoConfigObjectCreated()
    return CONFIG

def get_or_create_config():
    global CONFIG
    if not CONFIG:
        CONFIG = Config()
        CONFIG.load()
    return CONFIG

def clear_config_if_already_created():
    global CONFIG
    if CONFIG:
        CONFIG = None

#===============================================================================
# Classes
#===============================================================================
class ConfigError(Exception):
    pass

class Config(RawConfigParser):
    def __init__(self):
        RawConfigParser.__init__(self)
        self.__repo_path = None
        self._repo_name = None

        d = dirname(abspath(__file__))
        f = join_path(d, 'admin', 'cli.py')
        self.__python_evn_module_dir = d
        self.__python_evn_admin_cli_file_fullpath = f

        self.__load_defaults()
        self._default_sections_copy = copy.deepcopy(self._sections)
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
        return self._repo_name

    @property
    def repo_path(self):
        return self.__repo_path

    @property
    @memoize
    def default_repo_conf_filename(self):
        if not self.repo_path:
            raise RepositoryNotSet()
        return join_path(self.repo_path, 'conf/evn.conf')

    @property
    @memoize
    def possible_conf_filenames(self):
        return [
            f for f in (
                os.path.expanduser('~/.evnrc'),
                join_path(sys.exec_prefix, 'etc', 'evn.conf'),
                join_path(sys.exec_prefix, 'evn.conf'),
                '/etc/evn.conf',
                '/usr/local/etc/evn.conf',
                '/opt/etc/evn.conf',
                '/opt/local/etc/evn.conf',
                os.environ.get('EVN_CONF') or None,
                self.__filename or None,
            ) if f
        ]

    @property
    @memoize
    def possible_repo_conf_filenames(self):
        files =  [ self.default_repo_conf_filename ]
        files += [
            f.replace('evn.conf', '%s.conf' % self.repo_name)
                for f in self.possible_conf_filenames
                    if f.endswith('evn.conf')
        ]
        return files

    def _actual_files(self, files):
        return filter(None, [ file_exists_and_not_empty(f) for f in files ])

    @property
    @memoize
    def actual_conf_filenames(self):
        return self._actual_files(self.possible_conf_filenames)

    @property
    @memoize
    def actual_repo_conf_filenames(self):
        return self._actual_files(self.possible_repo_conf_filenames)

    @property
    def writable_repo_override_conf_filename(self):
        """
        Returns the most suitable path for writing the repo override config
        file.  Suitable in this instance means the returned path will try and
        respect the standard configuration file resolution rules -- basically,
        it should be able to figure out if you're using the '<reponame>.conf'
        pattern (where that file lives next to wherever evn.conf was found),
        or the '<repopath>/conf/evn.conf' pattern, which will be the default
        if no custom evn.conf was found.

        The most relevant path that can be written to will be returned or a
        runtime error will be raised -- this ensures calling code will be
        guaranteed to get a writable file name if available.

        This method (and the supporting (possible|actual)_conf_filenames glue)
        was introduced in order to better support dynamic repo configuration
        overrides for unit tests -- however, it could also be used for
        programmatic repo configuration.
        """
        assert self.repo_path

        files = chain(
            self.actual_repo_conf_filenames,
            self.possible_repo_conf_filenames,
        )

        return first_writable_file_that_preferably_exists(files)

    def load(self, filename=None, repo_path=None):
        self.__filename = filename
        self.read(self.actual_conf_filenames)
        self.__validate()
        if repo_path:
            self.load_repo(repo_path)

    @property
    def modifications(self):
        """
        Return a dict of dicts representing the sections/options that have
        been modified from their default value.
        """
        current = self._sections
        default = self._default_sections_copy
        modified = {}
        for (section, options) in current.items():
            if section not in default:
                modified[section] = options
                continue

            for (option, value) in options.items():
                include = False
                if option not in default[section]:
                    include = True
                elif value != default[section][option]:
                    include = True

                if include:
                    if section not in modified:
                        modified[section] = {}
                    modified[section][option] = value

        return modified

    def create_new_conf_from_modifications(self):
        """
        Return a new RawConfigParser instance that has been created from the
        non-default modifications returned by the `modifications` property
        above.
        """
        # This is a bit hacky as the underlying config classes don't really
        # support the notion of "only write out sections/options that have
        # changed since we loaded the defaults".
        if not self.repo_path:
            raise RepositoryNotSet()

        mods = self.modifications
        if not mods:
            raise NoModificationsMade()

        filename = self.writable_repo_override_conf_filename
        conf = RawConfigParser()
        conf.read(filename)
        for (section, options) in mods.items():
            conf.add_section(section)
            for (option, value) in options.items():
                conf.set(section, option, value)

        return conf

    def write_repo_conf(self):
        """
        Write any changes made to the repo's configuration file.  (The actual
        file is determined by the `writable_repo_override_conf_filename`
        property.)
        """
        conf = self.create_new_conf_from_modifications()
        filename = self.writable_repo_override_conf_filename

        with open(filename, 'w') as f:
            conf.write(f)

    def save(self):
        """
        Persist any non-default configuration changes that have been made.
        """
        if not self.repo_path:
            # I haven't implemented logic for writing override conf values
            # when the repo hasn't been set yet (as it hasn't been needed).
            raise NotImplementedError()
        else:
            self.write_repo_conf()

    def __validate(self):
        dummy = self.unix_hook_permissions

    def load_repo(self, repo_path):
        self.__repo_path = repo_path
        self._repo_name = os.path.basename(repo_path)

        assert self.repo_path
        assert self.repo_name

        self.read(self.actual_repo_conf_filenames)
        self.__validate()

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

        #import ipdb
        #ipdb.set_trace()
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
        self.set('main', 'svnadmin-create-flags', '')
        self.set('main', 'max-file-size-in-bytes', '26214400') # 25MB
        self.set('main', 'max-file-size-exclusion-regex', '')
        self.set('main', 'standard-layout', 'branches,tags,trunk')
        self.set('main', 'no-svnmucc-after-evnadmin-create', '')
        self.set('main', 'selftest-base-dir', '~/tmp/evn-test')

        self.set(
            'main',
            'custom-hook-classname',
            'evn.custom_hook.DummyCustomHook'
        )

        self.set(
            'main',
            'blocked-file-extensions-regex',
            '\.(com|ocx|mdb|dll|war|jar|so|exe|o|bin|iso|zip|tar|tgz|dat|tar\.gz|msi|msp|7z|pkg|rpm|nupkg|deb|dmg)$'
        )

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

    @property
    def no_svnmucc_after_evnadmin_create(self):
        return bool(self.get('main', 'no-svnmucc-after-evnadmin-create'))

    @property
    def max_file_size_in_bytes(self):
        i = try_int(self.get('main', 'max-file-size-in-bytes')) or 0
        if i < 0:
            i = 0
        return i

    def set_max_file_size_in_bytes(self, size):
        self.set('main', 'max-file-size-in-bytes', size)
        self.save()

    @property
    def standard_layout(self):
        layout = self.get('main', 'standard-layout')
        if not layout:
            return
        dirs = layout.split(',')
        return frozenset(format_dir(d) for d in dirs)

    @property
    @memoize
    def selftest_base_dir(self):
        """
        The base temp directory used when running unit tests via the `evnadmin
        selftest` command.  Defaults to ~/tmp/evn-test.  If the directory does
        not exist, it is created.
        """
        d = expanduser(self.get('main', 'selftest-base-dir'))
        if not isdir(d):
            os.makedirs(d)
        return d

    @staticmethod
    def verify_custom_hook_classname(classname):
        # Don't wrap the load_class() in a try/except block; just let the
        # error propagate back to the caller such that they're given the
        # maximum amount of information to assist in debugging.
        from .custom_hook import CustomHook
        cls = load_class(classname)
        if not isinstance(cls(), CustomHook):
            raise CommandError(
                "custom hook class '%s' does not derive from "
                "evn.custom_hook.CustomHook" % classname
            )

    @property
    def custom_hook_classname(self):
        return self.get('main', 'custom-hook-classname')

    def set_custom_hook_classname(self, classname):
        Config.verify_custom_hook_classname(classname)
        self.set('main', 'custom-hook-classname', classname)
        self.save()

    @property
    def custom_hook_class(self):
        return load_class(self.custom_hook_classname)

    @staticmethod
    def verify_blocked_file_extensions_regex(regex):
        pattern = re.compile(regex)

    def set_blocked_file_extensions_regex(self, regex):
        Config.verify_blocked_file_extensions_regex(regex)
        self.set('main', 'blocked-file-extensions-regex', regex)
        self.save()

    @property
    @memoize
    def blocked_file_extensions_regex(self):
        pattern = self.get('main', 'blocked-file-extensions-regex')
        if not pattern:
            return
        else:
            return re.compile(pattern, re.IGNORECASE)

    def is_blocked_file(self, filename):
        pattern = self.blocked_file_extensions_regex
        if not pattern:
            return False

        match = pattern.search(filename)
        return bool(match)

    def does_path_match_blocked_file_extensions_regex(self, path):
        pattern = self.blocked_file_extensions_regex
        if not pattern:
            msg = "config parameter 'blocked-file-extension-regex' not set"
            raise CommandError(msg)

        match = pattern.search(path)
        return bool(match)

    @staticmethod
    def verify_max_file_size_exclusion_regex(regex):
        pattern = re.compile(regex)

    def set_max_file_size_exclusion_regex(self, regex):
        Config.verify_max_file_size_exclusion_regex(regex)
        self.set('main', 'max-file-size-exclusion-regex', regex)
        self.save()

    @property
    @memoize
    def max_file_size_exclusion_regex(self):
        pattern = self.get('main', 'max-file-size-exclusion-regex')
        if not pattern:
            return
        else:
            return re.compile(pattern, re.IGNORECASE)

    def is_file_excluded_from_size_limits(self, path, size):
        max_size = self.max_file_size_in_bytes
        if not max_size:
            return True

        if size < max_size:
            return True

        pattern = self.max_file_size_exclusion_regex
        if not pattern:
            return False

        return self.does_path_match_file_size_exclusion_regex(path)

    def is_change_excluded_from_size_limits(self, change):
        return self.is_file_excluded_from_size_limits(
            change.path,
            change.filesize,
        )

    def does_path_match_file_size_exclusion_regex(self, path):
        pattern = self.max_file_size_exclusion_regex
        if not pattern:
            msg = "config parameter 'max-file-size-exclusion-regex' not set"
            raise CommandError(msg)

        match = pattern.search(path)
        return bool(match)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
