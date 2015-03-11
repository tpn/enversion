#===============================================================================
# Imports
#===============================================================================
import os
import datetime
import cStringIO as StringIO

import svn
import svn.repos

from glob import (
    iglob,
)

from pprint import (
    pformat,
)

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from evn.path import (
    join_path,
)

from evn.repo import (
    RepositoryRevOrTxn,
)

from evn.util import (
    add_linesep_if_missing,
    implicit_context,
    pid_exists,
    touch_file,
    DecayDict,
)

from evn.debug import (
    RemoteDebugSession,
    RemoteDebugSessionStatus,
)

#===============================================================================
# Classes
#===============================================================================
class RepositoryHook(RepositoryRevOrTxn):
    def __init__(self, **kwds):
        RepositoryRevOrTxn.__init__(self, **kwds)

        self.is_pre             = False
        self.is_post            = False
        self.is_lock            = False
        self.is_start           = False
        self.is_unlock          = False
        self.is_commit          = False
        self.is_revprop_change  = False

        self.tense      = None
        self.hook_args  = None
        self.hook_name  = None
        self.hook_type  = None
        self.rdb        = None # Remote Debugger

        self.custom_hook = self.conf.custom_hook_class()

    @property
    def is_repository_hook(self):
        return True

    @implicit_context
    def run_hook(self, hook_name, hook_args):
        self.hook_name = hook_name.replace('-', '_')
        self.hook_args = hook_args

        tokens = self.hook_name.split('_')
        # prefix will be one of: 'pre', 'post', 'start'
        (prefix, name) = (tokens[0], '_'.join(tokens[1:]))
        assert prefix in ('pre', 'post', 'start')
        assert name in ('commit', 'lock', 'unlock', 'revprop_change'), \
               "invalid name: %s" % name

        setattr(self, 'is_%s' % prefix, True)
        setattr(self, 'is_%s' % name,   True)
        self.tense = prefix
        self.hook_type = name

        getattr(self, self.hook_name)(*self.hook_args)
        if self.is_pre and self.error:
            self.die()

    def __repr__(self):
        return '<%s(tense=%s, type=%s, name=%s, args=%s)>' % (
            self.__class__.__name__,
            self.tense,
            self.hook_type,
            self.hook_name,
            repr(self.hook_args),
        )

    # Lock operations.
    def pre_lock(self, path, user, comment, steal, *args):
        #self.error = 'locking not permitted'
        pass

    def pre_unlock(self, path, user, token, _break, *args):
        pass

    def post_lock(self, user, *args):
        pass

    def post_unlock(self, user, *args):
        pass

    def pre_revprop_change(self, rev, user, propname, action, *args):
        # XXX TODO: when we introduce the new override facilities, make sure
        # log messages can't be changed to have confirmations added/removed.
        pn = svn.core.SVN_PROP_REVISION_LOG
        if propname == pn:
            if action == 'D':
                self.error = "deleting '%s' is not permitted" % pn
        elif not self.is_admin(user):
            self.error = (
                "modification of r%s's revision property '%s' is not "
                "permitted by user '%s' (action type: '%s')" % (
                    rev,
                    propname,
                    user,
                    action,
                )
            )

    def post_revprop_change(self, rev, user, propname, action, *args):
        pass

    def pre_unlock(self, path, user, *args):
        pass

    def start_commit(self, user, capabilities, *args):
        # XXX TODO: we should really do all of our repository sanity checks
        # regarding evn:* revprops at this point, so we can block the commit
        # at the earliest possible point if an error is detected.
        pass

    def post_commit(self, rev, *args):
        # XXX TODO: add support for txn_name if it's present.

        # The only thing we *have* to do during post-commit is to access the
        # changeset property (which automatically creates, analyses and then
        # post-processes it behind the scenes).
        self.process_rev_or_txn(rev)
        cs = self.changeset
        self.custom_hook.post_commit(self)

    def pre_commit(self, txn, *args):
        self.process_rev_or_txn(txn)
        self.custom_hook.pre_commit(self)

        ignore_errors = False
        ignore_warnings = False
        allowed_override = (
            self.is_allowed_override() or
            self.is_repo_admin() or
            self.is_admin()
        )
        if 'IGNORE ERRORS' in self.log_msg:
            if not allowed_override:
                self.error = (
                    "commits with errors can only be forced through by the "
                    "following repository admins: %s, or support staff: %s" % (
                        ', '.join(self.repo_admins),
                        ', '.join(self.admins),
                    )
                )
                return
            ignore_errors = True
            # Ignore errors implies ignore warnings, also.
            ignore_warnings = True

        if 'IGNORE WARNINGS' in self.log_msg:
            if not allowed_override:
                self.error = (
                    "commits with warnings can only be forced through by the "
                    "following repository admins: %s, or support staff: %s" % (
                        ', '.join(self.repo_admins),
                        ', '.join(self.admins),
                    )
                )
                return
            ignore_warnings = True

        # Note that we don't wrap the self.changeset in a try/except block
        # below -- as per the notes above, we want exceptions to propagate
        # all the way back to the user.
        cs = self.changeset
        if cs.has_errors and not ignore_errors:
            if allowed_override:
                errors = cs.errors_with_confirmation_instructions
            else:
                errors = cs.errors
            self.error += "errors:\n%s\n" % pformat(errors)

        if cs.has_warnings and not ignore_warnings:
            self.error += "warnings:\n%s\n" % pformat(cs.warnings)

        stuff_to_report = (
            (cs.has_errors and not ignore_errors) or
            (cs.has_warnings and not ignore_warnings)
        )
        if stuff_to_report:
            _admins = lambda a: ', '.join(a) if a else '<none>'
            self.error += (
                "\nCommits with errors or warnings can be forced through "
                "by the following repository admins: %s, or support staff: "
                "%s" % (_admins(self.repo_admins), _admins(self.admins))
            )

#===============================================================================
# Hook File
#===============================================================================
class HookFile(object):
    __metaclass__ = ABCMeta

    def __init__(self, repo, name, path):
        self.repo = repo
        self.name = name
        self.path = path
        self.conf = repo.conf
        self.pool = repo.pool
        self.options = repo.options
        self.ostream = repo.ostream
        self.estream = repo.estream

    @abstractmethod
    def create(self):
        raise NotImplementedError

    @property
    def exists(self):
        return os.path.exists(self.path) and os.path.isfile(self.path)

    @property
    def executable(self):
        if os.name == 'nt':
            return True

        return os.access(self.path, os.X_OK)

    @property
    def perms(self):
        return oct(os.stat(self.path).st_mode)[-4:]

    def fix_perms(self):
        if os.name == 'nt':
            return

        assert not self.executable
        os.chmod(self.path, self.conf.unix_hook_permissions)
        assert self.executable

    @property
    def is_empty(self):
        s = os.stat(self.path)
        return (s.st_size == 0)

    def read(self):
        assert self.exists
        with open(self.path, 'r+') as f:
            return f.read()

    @property
    def lines(self):
        return self.read().split(os.linesep)

    @property
    def comment_character(self):
        return 'rem' if os.name == 'nt' else '#'

    def _touch(self, path):
        touch_file(path)

    @abstractproperty
    def needs_fixing(self):
        raise NotImplementedError

class RepoHookFile(HookFile):
    def __init__(self, repo, name):
        method = name.replace('-', '_') + '_hook'
        path = getattr(svn.repos, method)(repo.repo, repo.pool)
        name = os.path.basename(path)
        HookFile.__init__(self, repo, name, path)
        dirname = os.path.dirname(self.path)
        prefix = self.conf.svn_hook_enabled_prefix
        p = join_path(dirname, '%s-%s' % (prefix, name))
        self.__enabler_path = p

        suffix = self.conf.svn_hook_remote_debug_suffix
        p = join_path(dirname, '%s-%s-%s' % (prefix, name, suffix))
        self.__remote_debug_path = p
        self.__remote_debug_session_glob = '%s-*.*' % p
        self._refresh_remote_debug_status()

    def _refresh_remote_debug_status(self):
        self.__remote_debug_host = None
        self.__remote_debug_port = None
        self.__remote_debug_enabled = False
        self.__remote_debug_sessions = list()
        self.__stale_remote_debug_sessions = list()
        self.__invalid_remote_debug_sessions = list()
        p = self.__remote_debug_path
        if os.path.exists(p):
            with open(p, 'r') as f:
                # [:-1] = strip trailing '\n'
                text = f.read()[:-1]
                (host, port) = text.split(':')
                port = int(port)
                assert port >= 0 and port <= 65535
                self.__remote_debug_host = host
                self.__remote_debug_port = port
                self.__remote_debug_enabled = True

        for f in iglob(self.__remote_debug_session_glob):
            pid = int(f[f.rfind('.')+1:])
            if not pid_exists(pid):
                self.__stale_remote_debug_sessions.append(f)
                continue

            session = RemoteDebugSessionStatus._load(f)
            self.__remote_debug_sessions.append(session)

    @property
    def has_invalid_remote_debug_sessions(self):
        return bool(self.__invalid_remote_debug_sessions)

    @property
    def has_stale_remote_debug_sessions(self):
        return bool(self.__stale_remote_debug_sessions)

    @property
    def invalid_remote_debug_sessions(self):
        return self.__invalid_remote_debug_sessions

    @property
    def stale_remote_debug_sessions(self):
        return self.__stale_remote_debug_sessions

    @property
    def remote_debug_sessions(self):
        return self.__remote_debug_sessions

    @property
    def is_remote_debug_enabled(self):
        return self.__remote_debug_enabled

    def refresh_remote_debug_status(self):
        self.__remote_debug_host = None
        self.__remote_debug_port = None
        self.__remote_debug_enabled = False
        p = self.__remote_debug_path
        if os.path.exists(p):
            with open(p, 'r') as f:
                # [:-1] = strip trailing '\n'
                text = f.read()[:-1]
                (host, port) = text.split(':')
                port = int(port)
                assert port > 1 and port <= 65535
                self.__remote_debug_host = host
                self.__remote_debug_port = port
                self.__remote_debug_enabled = True


    @property
    def remote_debug_host(self):
        #assert self.is_remote_debug_enabled
        return self.__remote_debug_host

    @property
    def remote_debug_port(self):
        #assert self.is_remote_debug_enabled
        return self.__remote_debug_port

    @property
    def is_enabled(self):
        if not self.exists or self.is_empty or not self.configured:
            return False

        return os.path.exists(self.__enabler_path)

    @property
    def needs_fixing(self):
        return not (
            self.exists and
            not self.is_empty and
            self.executable and
            self.configured
        )

    def enable(self):
        assert not self.is_enabled
        self._touch(self.__enabler_path)
        assert self.is_enabled

    def disable(self):
        if not self.is_enabled:
            return
        os.unlink(self.__enabler_path)

    def enable_remote_debug(self, host, port):
        assert not self.is_remote_debug_enabled
        (h, p) = (str(host), int(port))
        assert h != '' and p >= 0 and p <= 65535

        with open(self.__remote_debug_path, 'w') as f:
            f.write('%s:%d\n' % (h, p))
            f.flush()
            f.close()

        self._refresh_remote_debug_status()
        assert self.is_remote_debug_enabled

    def disable_remote_debug(self):
        assert self.is_remote_debug_enabled
        os.unlink(self.__remote_debug_path)
        self._refresh_remote_debug_status()
        assert not self.is_remote_debug_enabled

    def create(self):
        assert not self.exists or self.is_empty
        self._touch(self.path)
        assert self.exists
        self.configure_to_call_evn_hook()
        assert self.is_configured_to_call_evn_hook

    @property
    def is_configured_to_call_evn_hook(self):
        if not self.exists or self.is_empty:
            return False

        lines = self.lines
        if os.name != 'nt':
            has_shebang = False
            try:
                if lines[0].startswith('#!'):
                    has_shebang = True
            except:
                pass
            if not has_shebang:
                return False

        found = False
        expected = self.conf.svn_hook_syntax_for_invoking_evn_hook
        for line in lines:
            if line.startswith(self.comment_character):
                continue

            if line == expected:
                found = True
                break

        return found

    @property
    def configured(self):
        return self.is_configured_to_call_evn_hook

    def configure(self):
        self.configure_to_call_evn_hook()

    def configure_to_call_evn_hook(self):
        output = list()
        backup = None
        existing = None

        code = self.conf.svn_hook_syntax_for_invoking_evn_hook

        if self.exists and not self.is_empty:
            assert not self.is_configured_to_call_evn_hook
            existing = self.read()
            lines = existing.split(os.linesep)
        else:
            lines = self.conf.svn_hook_code_empty.split(os.linesep)

        if os.name != 'nt':
            insert_shebang = True
            try:
                if lines[0].startswith('#!'):
                    insert_shebang = False
            except:
                pass
            if insert_shebang:
                output.append('#!/bin/sh')

        first = True
        inserted = False
        for line in lines:

            if inserted:
                if line != code:
                    output.append(line)
            else:
                if line == code:
                    inserted = True
                    output.append(line)
                elif line.startswith(self.comment_character):
                    output.append(line)
                elif not line:
                    # Skip blank lines.
                    output.append(line)
                else:
                    if first and line.lower().startswith('@echo'):
                        # Special-case for `@echo off` first line on Windows.
                        output.append(line)
                        output.append(code)
                    else:
                        output.append(code)
                        output.append(line)
                    inserted = True

            if first:
                first = False

        assert inserted

        # Remove trailing empty lines.
        while not output[-1]:
            output.pop()

        if existing:
            suffix = datetime.datetime.now().strftime('%Y%m%d%H%M%S-%f')
            backup = self.path + '.bak.' + suffix
            assert not os.path.exists(backup)
            with open(backup, 'w+') as f:
                f.truncate(0)
                f.seek(0)
                f.write(existing)
                f.flush()
                f.close()

            assert os.path.exists(backup)
            with open(backup, 'r') as f:
                f.seek(0)
                assert (f.read() == existing)
                f.close()

        failed = True
        try:
            expected = add_linesep_if_missing(os.linesep.join(output))
            with open(self.path, 'w+') as f:
                f.truncate(0)
                f.seek(0)
                f.write(expected)
                f.flush()
                f.close()

            assert self.exists
            assert not self.is_empty
            with open(self.path, 'r') as f:
                f.seek(0)
                assert (f.read() == expected)
                f.close()

            failed = False
        finally:
            if not failed and backup is not None:
                os.unlink(backup)

class EvnHookFile(HookFile):
    def __init__(self, repo):
        name = repo.conf.evn_hook_file_name
        path = join_path(repo.hook_dir, name)
        HookFile.__init__(self, repo, name, path)

    def create(self):
        assert not self.exists or self.is_empty
        self.__create()

    def __create(self):
        with open(self.path, 'w+') as f:
            self.write(f)
        assert self.exists and not self.is_empty
        if not self.executable:
            self.fix_perms()

    @property
    def needs_fixing(self):
        return not (
            self.exists and
            not self.is_empty and
            self.executable and
            self.is_valid
        )

    @property
    def has_local_modifications(self):
        if not self.exists:
            return False

        return (self._actual == self._expected)

    @property
    def is_valid(self):
        # xxx fix
        return self.has_local_modifications

    @property
    def _expected(self):
        expected = StringIO.StringIO()
        self.write(expected)
        expected.flush()
        expected.seek(0)
        return expected.read()

    @property
    def _actual(self):
        if not self.exists:
            return ''

        actual = StringIO.StringIO()
        with open(self.path, 'r+') as f:
            actual.write(f.read())


        actual.flush()
        actual.seek(0)
        return actual.read()

    def fix_code(self):
        assert self.exists and not self.is_valid
        self.__create()

    def revert_local_modifications(self):
        # xxx todo
        self.fix_code()

    def write(self, ostream):
        ostream.truncate(0)
        ostream.seek(0)

        if os.name == 'nt':
            self.__write_windows_hook(ostream)
        else:
            self.__write_unix_hook(ostream)

        ostream.flush()

    def __write_windows_hook(self, ostream):
        # XXX TODO: this is blatantly broken, as is all the other Windows
        # stuff at the moment.
        lines  = [ '@echo off', ]
        lines += [
            self.conf.evn_hook_code_for_testing_if_svn_hook_is_enabled,
            self.conf.evn_run_hook_code
        ]

        ostream.write(add_linesep_if_missing(os.linesep.join(lines)))

        args = (sys.executable, self.conf.python_evn_admin_cli_file_fullpath)
        ostream.write('"%s" "%s" run-hook %%*\n' % args)

    def __write_unix_hook(self, ostream):
        env = os.environ
        args = ('main', 'unix-hook-autoexpand-env-vars')
        envvars = [
            '%s=%s' % (name, env[name]) for name in (
                self.conf.get_csv_as_list(*args)
            ) if name in env
        ]

        args = ('main', 'unix-hook-force-env-vars')
        envvars += self.conf.get_csv_as_list(*args)

        lines  = [ '#!/bin/sh', ]
        lines += envvars
        lines += [ 'export %s' % e.split('=')[0] for e in envvars ]
        lines += [
            self.conf.evn_hook_code_for_testing_if_svn_hook_is_enabled,
            self.conf.evn_run_hook_code
        ]

        ostream.write(add_linesep_if_missing(os.linesep.join(lines)))

#===============================================================================
# Status/Info Objects
#===============================================================================
class RepoHookFileStatus(object):
    def __init__(self, **kwds):
        k = DecayDict(**kwds)
        self.name                   = k.name
        self.exists                 = k.exists
        self.enabled                = k.get('enabled', False)
        self.configured             = k.get('configured', False)
        self.executable             = k.get('executable', False)
        self.remote_debug           = k.get('remote_debug', False)
        self.remote_debug_host      = k.get('remote_debug_host', None)
        self.remote_debug_port      = k.get('remote_debug_port', None)
        self.remote_debug_sessions  = k.get('remote_debug_sessions', [])

        self.stale_remote_debug_sessions = \
            k.get('stale_remote_debug_sessions', [])

        self.invalid_remote_debug_sessions = \
            k.get('invalid_remote_debug_sessions', [])

        k.assert_empty(k)

class EvnHookFileStatus(object):
    def __init__(self, **kwds):
        k = DecayDict(**kwds)
        self.name       = k.name
        self.exists     = k.exists
        self.valid      = k.get('valid', False)
        self.executable = k.get('executable', False)
        k.assert_empty(k)

class RepoHookFilesStatus(object):
    def __init__(self, **kwds):
        k = DecayDict(**kwds)
        self.name           = k.name
        self.path           = k.path
        self.hook_dir       = k.hook_dir
        self.hook_files     = k.hook_files
        self.evn_hook_file  = k.evn_hook_file
        k.assert_empty(k)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
