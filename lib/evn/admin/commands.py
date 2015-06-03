#===============================================================================
# Imports
#===============================================================================
import os
import sys
import pprint
import traceback
import subprocess

import svn
import svn.fs

import cStringIO as StringIO

from evn.path import (
    format_dir,
)

from evn.config import (
    Config,
)

from evn.repo import (
    RepositoryError,
    RepositoryRevOrTxn,
    RepositoryRevisionConfig,
)

from evn.debug import (
    RemoteDebugSession,
)

from evn.command import (
    Command,
    CommandError,
    RepoHookCommand,
    SubversionCommand,
    RepositoryCommand,
    RepositoryRevisionCommand,
    RepositoryRevisionRangeCommand,
)

from evn.hook import (
    RepositoryHook,
    EvnHookFileStatus,
    RepoHookFileStatus,
    RepoHookFilesStatus,
)

from evn.change import (
    ChangeSet,
)

from evn.util import (
    chdir,
    literal_eval,
    requires_context,
    Pool,
    Dict,
    Options,
    DecayDict,
)

#===============================================================================
# Administrative Commands
#===============================================================================

class DoctestCommand(Command):
    def run(self):
        self._out("running doctests...")
        quiet = self.options.quiet
        import doctest
        import evn.path
        import evn.root
        import evn.util
        import evn.logic
        verbose = not quiet
        doctest.testmod(evn.path, verbose=verbose, raise_on_error=True)
        doctest.testmod(evn.root, verbose=verbose, raise_on_error=True)
        doctest.testmod(evn.util, verbose=verbose, raise_on_error=True)
        doctest.testmod(evn.logic, verbose=verbose, raise_on_error=True)

class UnittestCommand(Command):
    def run(self):
        with chdir(self.conf.selftest_base_dir):
            import evn.test
            evn.test.main(quiet=self.options.quiet)

class SelftestCommand(Command):
    tests = (
        DoctestCommand,
        UnittestCommand,
    )

    def run(self):
        quiet = self.options.quiet
        for test in self.tests:
            with Command.prime(self, test) as command:
                command.run()

class ListUnitTestClassnamesCommand(Command):
    def run(self):
        import evn.test

        # Whip up a little helper class to transform the 'module_name: class'
        # format to 'module_name.class'.
        class Writer:
            ostream = self.ostream
            def write(self, s):
                self.ostream.write(s.replace(': ', '.'))
        stream = Writer()
        for dummy in evn.test.suites(stream=stream, load=False):
            pass

class DumpDefaultConfigCommand(Command):
    def run(self):
        cf = Config()
        cf.write(self.ostream)

class DumpConfigCommand(Command):
    def run(self):
        self.conf.write(self.ostream)

class DumpRepoConfigCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        self.conf.write(self.ostream)

class DumpModifiedRepoConfigCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        from ..config import NoModificationsMade
        try:
            conf = self.conf.create_new_conf_from_modifications()
        except NoModificationsMade:
            raise CommandError(
                "repository '%s' has no custom configuration "
                "modifications made" % (self.conf.repo_name)
            )
        conf.write(self.ostream)

class ShowPossibleConfigFileLoadOrderCommand(Command):
    @requires_context
    def run(self):
        self._out(os.linesep.join(self.conf.possible_conf_filenames))

class ShowPossibleRepoConfigFileLoadOrderCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        self._out(os.linesep.join(self.conf.possible_repo_conf_filenames))

class ShowActualConfigFileLoadOrderCommand(Command):
    @requires_context
    def run(self):
        if not self.conf.actual_conf_filenames:
            raise CommandError('no configuration files are being loaded')
        self._out(os.linesep.join(self.conf.actual_conf_filenames))

class ShowActualRepoConfigFileLoadOrderCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        if not self.conf.actual_repo_conf_filenames:
            raise CommandError('no repo configuration files are being loaded')
        self._out(os.linesep.join(self.conf.actual_repo_conf_filenames))

class ShowWritableRepoOverrideConfigFilenameCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        self._out(self.conf.writable_repo_override_conf_filename)

class DumpHookCodeCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        h = self.evn_hook_file
        h.write(self.ostream)

class ShowRepoHookStatusCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        d = Dict()
        d.name = self.name
        d.path = self.path
        d.hook_dir = self.hook_dir

        t = dict()
        for hf in self.hook_files:
            assert hf.name not in t
            t[hf.name] = h = Dict()
            h.name = hf.name
            h.exists = hf.exists

            h.remote_debug      = hf.is_remote_debug_enabled
            h.remote_debug_host = hf.remote_debug_host
            h.remote_debug_port = hf.remote_debug_port

            h.remote_debug_sessions         = hf.remote_debug_sessions
            h.stale_remote_debug_sessions   = hf.remote_debug_sessions
            h.invalid_remote_debug_sessions = hf.invalid_remote_debug_sessions

            if not h.exists:
                continue

            h.executable = hf.executable
            h.configured = hf.configured
            if not h.configured:
                continue

            h.enabled = hf.is_enabled

        d.hook_files = [ RepoHookFileStatus(**k) for k in t.values() ]

        eh = self.evn_hook_file
        h = Dict()
        h.name   = eh.name
        h.exists = eh.exists
        if h.exists:
            h.valid = eh.is_valid
            h.executable = eh.executable

        d.evn_hook_file = EvnHookFileStatus(**h)

        self.result = RepoHookFilesStatus(**d)

class FixHookCommand(RepoHookCommand):
    @requires_context
    def run(self):
        RepoHookCommand.run(self)

        h = self.hook_file(self.hook_name)
        if not h.needs_fixing:
            raise CommandError(
                "Hook '%s' for repository '%s' "
                "does not need fixing." % (
                    self.hook_name,
                    self.name,
                )
            )

        self._out("Fixing repository hook '%s'..." % self.hook_name)
        if not h.exists or h.is_empty:
            self._out("    Creating new file.")
            h.create()

        if not h.executable:
            self._out("    Setting correct file permissions.")
            h.fix_perms()

        if not h.configured:
            self._out("    Configuring for use with Enversion.")
            h.configure()

        assert not h.needs_fixing
        self._out("Done!")

class FixEvnHookCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        h = self.evn_hook_file
        if not h.needs_fixing:
            raise CommandError(
                "Hook '%s' for repository '%s' "
                "does not need fixing." % (
                    h.name,
                    self.name,
                )
            )

        self._out(
            "Fixing hook '%s' for repository '%s'..." % (
                h.name,
                self.path,
            )
        )

        if not h.exists or h.is_empty:
            self._out("    Creating new file.")
            h.create()

        if not h.executable:
            self._out("    Setting correct file permissions.")
            h.fix_perms()

        if not h.is_valid:
            self._out("    Correcting hook code.")
            h.fix_code()

        assert not h.needs_fixing
        self._out("Done!")

class FixHooksCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        streams = (self.istream, self.ostream, self.estream)

        for h in self.hook_files:
            if not h.needs_fixing:
                continue

            with FixHookCommand(*streams) as fh:
                fh.path = self.path
                fh.conf = self.conf
                fh.options = self.options
                fh.hook_name = h.name
                fh.run()

        if not self.evn_hook_file.needs_fixing:
            return

        with FixEvnHookCommand(*streams) as fh:
            fh.path = self.path
            fh.conf = self.conf
            fh.options = self.options
            fh.run()

class EnableCommand(FixHooksCommand):
    @requires_context
    def run(self):
        self.options.quiet = True

        with Command.prime(self, AnalyzeCommand) as command:
            command.path = self.path
            command.run(from_enable=True)
            if not command.options.quiet:
                self.options.quiet = False

        FixHooksCommand.run(self)

        for h in self.hook_files:
            if not h.is_enabled:
                h.enable()

        self._out("Enabled Enversion for repository '%s'." % self.name)

class DisableCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        for h in self.hook_files:
            h.disable()

class CreateRepoCommand(SubversionCommand):
    path = None
    component_depth = None
    @requires_context
    def run(self):
        assert self.path
        passthrough = self.options.passthrough
        if not passthrough:
            passthrough = self.conf.svnadmin_create_flags

        if not passthrough:
            r = svn.repos.create(self.path, None, None, None, None, self.pool)
            assert r
        else:
            cmd = [
                'svnadmin',
                'create',
            ] + passthrough.split(' ') + [
                self.path,
            ]
            self._verbose(' '.join(cmd))
            subprocess.check_call(cmd)

        root_url = 'file://%s' % os.path.abspath(self.path)

        if self.options.verbose:
            stdout = subprocess.PIPE
        else:
            stdout = open('/dev/null', 'w')

        if not self.component_depth:
            no_svnmucc = self.options.no_svnmucc
            if not no_svnmucc:
                no_svnmucc = self.conf.no_svnmucc_after_evnadmin_create

            standard_layout = self.conf.standard_layout
            if not no_svnmucc and standard_layout:
                cmd = [
                    'svnmucc',
                    '-m',
                    '"Initializing repository."',
                    '--root-url',
                    root_url,
                ]
                for d in standard_layout:
                    cmd += [ 'mkdir', d ]

                self._verbose(' '.join(cmd))

                suppress_stdout = subprocess.check_call(cmd, stdout=stdout)

        with Command.prime(self, EnableCommand) as command:
            command.path = self.path
            command.options.quiet = True
            command.run()

        if self.component_depth not in (0, 1):
            return

        with Command.prime(self, SetRepoComponentDepthCommand) as command:
            command.path = self.path
            command.options.quiet = True
            command.component_depth = self.component_depth
            command.run()

class SetRepoComponentDepthCommand(RepositoryCommand):
    component_depth = None

    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        assert self.component_depth in (-1, 0, 1)

        out = self._out
        err = self._err

        rc0 = self.r0_revprop_conf

        cur_depth = rc0.get('component_depth', -1)
        if self.component_depth == -1:
            if cur_depth in (0, 1):
                out("Removing component depth from %s." % self.name)
                del rc0.component_depth
        else:
            args = (self.name, self.component_depth)
            if self.component_depth != cur_depth:
                out("Setting component depth for %s to %d." % args)
                rc0.component_depth = self.component_depth
            else:
                err("Component depth for %s is already %d." % args)

class GetRepoComponentDepthCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        rc0 = self.r0_revprop_conf
        out = self._out
        err = self._err
        if 'component_depth' not in rc0:
            out('-1 (none)')
        else:
            depth = rc0.component_depth
            if depth in (0, 1):
                out('%d (%s)' % (depth, { 0: 'single', 1: 'multi' }[depth]))
            else:
                err('Invalid depth: %s' % str(depth))

class SetRepoCustomHookClassCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        custom_hook_classname = self.options.custom_hook_classname
        self.conf.set_custom_hook_classname(custom_hook_classname)

class GetRepoCustomHookClassCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        self._out(self.conf.custom_hook_classname)

class VerifyPathMatchesBlockedFileExtensionsRegexCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        path = self.options.path
        conf = self.conf
        if conf.does_path_match_blocked_file_extensions_regex(path):
            return
        else:
            raise CommandError(
                "path '%s' does not match regex '%s'" % (
                    path,
                    conf.get('main', 'blocked-file-extensions-regex'),
                )
            )

class VerifyPathMatchesFileSizeExclusionRegexCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        path = self.options.path
        conf = self.conf
        if conf.does_path_match_file_size_exclusion_regex(path):
            return
        else:
            raise CommandError(
                "path '%s' does not match regex '%s'" % (
                    path,
                    conf.get('main', 'max-file-size-exclusion-regex'),
                )
            )

class SetRepoHookRemoteDebugCommand(RepoHookCommand):
    action = None

    @property
    def enable(self):
        return self.action == 'enable'

    @property
    def disable(self):
        return self.action == 'disable'

    @property
    def toggle(self):
        return self.action == 'toggle'

    def _invert(self, value):
        assert value in (True, False)
        return 'enable' if not value else 'disable'

    @requires_context
    def run(self):
        RepoHookCommand.run(self)

        assert self.action in ('enable', 'disable', 'toggle')

        h = self.hook_file(self.hook_name)

        if self.toggle:
            self.action = self._invert(h.is_remote_debug_enabled)

        if self.enable:
            host = self.options.remote_debug_host
            port = self.options.remote_debug_port

        if h.is_remote_debug_enabled:
            if self.enable:
                (rhost, rport) = (h.remote_debug_host, h.remote_debug_port)
                args = (h.name, host, port)
                if host != rhost or port != rport:
                    m = (
                        "Updating %s hook to listen on "
                        "%s:%d instead of %s:%d."
                    )
                    self._out(m % (h.name, host, port, rhost, rport))
                    h.disable_remote_debug()
                    h.enable_remote_debug(host, port)
                else:
                    m = "%s hook already configured to listen on %s:%d."
                    self._warn(m % (h.name, host, port))
            else:
                self._out("Disabling remote debug for %s hook." % h.name)
                h.disable_remote_debug()
        else:
            if self.enable:
                m = (
                    "Enabling remote debug for %s hook "
                    "(listening for connections on %s:%d)."
                )
                self._out(m % (h.name, host, port))
                h.enable_remote_debug(host, port)
            else:
                m = "Remote debug not enabled for %s hook." % h.name
                self._warn(m)

class RunHookCommand(RepoHookCommand):
    hook_args = None
    rdb = None

    @requires_context
    def run(self):
        RepoHookCommand.run(self)

        if self.hook.is_remote_debug_enabled:
            args = (
                self.hook.remote_debug_host,
                self.hook.remote_debug_port,
                self.hook_name,
                self.hook_dir,
                self.options,
                self.conf,
            )
            self.rdb = RemoteDebugSession(*args)
            self.rdb.set_trace()

        with RepositoryHook(**self.repo_kwds) as r:
            r.rdb = self.rdb
            try:
                r.run_hook(self.hook_name, self.hook_args)
            except Exception as exc:
                (exc_type, exc_value, exc_tb) = sys.exc_info()
                # XXX TODO: if it's a pre-commit, try extract info about the
                # incoming commit, i.e. svn log -v type output for the txn.

                if isinstance(exc, RepositoryError):
                    self._err(exc.args[0])
                    sys.exit(1)
                else:
                    m = "Repository %s hook failed (hook args: %s):%s%s"
                    args = ', '.join('%s' % repr(a) for a in self.hook_args)
                    e = ''.join(traceback.format_exception(*sys.exc_info()))
                    err = m % (self.hook_name, args, os.linesep, e)
                    sys.stderr.write(err)
                    raise exc

class AnalyzeCommand(RepositoryCommand):
    @requires_context
    def run(self, from_enable=False):
        RepositoryCommand.run(self)

        rc0 = self.r0_revprop_conf

        last_rev = rc0.get('last_rev', None)
        start_rev = last_rev if last_rev is not None else 0
        end_rev = svn.fs.youngest_rev(self.fs)

        if end_rev == 0 or from_enable:
            self.options.quiet = True

        if last_rev is not None:
            if start_rev == end_rev:
                m = "Repository '%s' is up to date (r%d)."
                self._out(m % (self.name, end_rev))
                return
            elif start_rev == 0:
                if from_enable:
                    self.options.quiet = False
                m = "Analyzing repository '%s'..." % self.name
                self._out(m)
            else:
                if from_enable:
                    self.options.quiet = False
                self._out(
                    "Resuming analysis for repository '%s' "
                    "from revision %d..." % (self.name, start_rev)
                )

        k = self.repo_kwds
        for i in xrange(start_rev, end_rev+1):
            with RepositoryRevOrTxn(**k) as r:
                r.process_rev_or_txn(i)
                if i == 0:
                    continue
                cs = r.changeset
                self._out(str(i) + ':' + cs.analysis.one_liner)

        self._out("Finished analyzing repository '%s'." % self.name)

class ShowRootsCommand(RepositoryRevisionCommand):
    @requires_context
    def run(self):
        RepositoryRevisionCommand.run(self)

        if self.rev == self.last_rev and self.rev < self.youngest_rev:
            m = (
                "Note: last analyzed revision of repository '%s' (r%d) lags "
                "behind HEAD (r%d)."
            )
            self._out(m % (self.name, self.last_rev, self.youngest_rev))

        k = dict(fs=self.fs, rev=self.rev, conf=self.conf)
        rc = RepositoryRevisionConfig(**k)
        roots = rc.roots

        if roots is None:
            m = "Repository '%s' has no roots defined at r%d."
            self._out(m % (self.name, self.rev))
        else:
            m = "Showing roots for repository '%s' at r%d:"
            self._out(m % (self.name, self.rev))
            pprint.pprint(roots, self.ostream)


class RootInfoCommand(RepositoryRevisionCommand):
    root_path = None
    @requires_context
    def run(self):
        RepositoryRevisionCommand.run(self)

        assert self.root_path and isinstance(self.root_path, str)
        p = format_dir(self.root_path)

        k = dict(fs=self.fs, rev=self.rev, conf=self.conf)
        rc = RepositoryRevisionConfig(**k)
        roots = rc.roots
        if not roots:
            m = "Repository '%s' has no roots defined at r%d"
            self._out(m % (self.name, self.rev))
            return

        root = roots.get(p)
        if not root:
            m = "No root named '%s' is present in repository '%s' at r%d."
            self._out(m % (p, self.name, self.rev))
            return

        created = root['created']
        m = "Found root '%s' in repository '%s' at r%d (created at r%d)."
        self._verbose(m % (p, self.name, self.rev, created))

        k = dict(fs=self.fs, rev=created, conf=self.conf)
        rc = RepositoryRevisionConfig(**k)
        roots = rc.roots
        assert roots
        root = roots[p]
        assert root
        m = "Displaying root info for '%s' from r%d:"
        self._verbose(m % (p, created))
        d = { p : root }

        if self.options.json:
            import json
            json.dump(d, self.ostream, sort_keys=True, indent=4)
            return

        buf = StringIO.StringIO()
        w = buf.write
        w("'%s': {\n" % p)
        if root['copies']:
            w("    'copies': {\n")

            copies = pprint.pformat(root['copies'])
            indent = ' ' * 8
            w(indent)
            w(copies[1:-1].replace('\n', '\n' + indent))
            w("\n    },\n")
        else:
            w("    'copies': { },\n")

        for (k, v) in root.items():
            if k == 'copies':
                continue
            w("    '%s': %s,\n" % (k, pprint.pformat(v)))
        w("}\n")

        buf.seek(0)
        self.ostream.write(buf.read())


class ChangeSetCommand(RepositoryCommand):
    rev_or_txn = None

    @property
    def changeset_kwds(self):
        k = ChangeSetCommand.get_changeset_kwds(self)
        k.fs   = self.fs
        #k.pool = self.pool
        k.root = self.root
        return k

    @classmethod
    def get_changeset_kwds(cls, obj):
        k = Dict()
        k.conf = obj.conf
        k.estream = obj.estream
        k.ostream = obj.ostream
        k.istream = obj.istream
        k.options = obj.options
        return k

    @classmethod
    def get_root_for_rev_or_txn(cls, fs, rev_or_txn, pool):
        try:
            rev = int(rev_or_txn)
            is_rev = True
            assert rev >= 0
        except:
            assert isinstance(rev_or_txn, str)
            is_rev = False
            txn_name = rev_or_txn
            txn = svn.fs.open_txn(fs, txn_name, pool)

        if is_rev:
            root = svn.fs.revision_root(fs, rev, pool)
        else:
            root = svn.fs.txn_root(txn, pool)

        return root

    @classmethod
    def get_changeset_kwds_for_rev_or_txn(cls, obj, rev_or_txn, pool):
        k = Dict()
        k.fs        = obj.fs
        #k.pool      = pool
        k.conf      = obj.conf
        k.estream   = obj.estream
        k.ostream   = obj.ostream
        k.istream   = obj.istream
        k.options   = obj.options

        #args = (k.fs, rev_or_txn, pool)
        args = (k.fs, rev_or_txn)
        k.root = ChangeSetCommand.get_root_for_rev_or_txn(*args)
        return k

    @requires_context
    def __init_rev_or_txn(self):
        assert self.rev_or_txn is not None

        #p = self.pool
        try:
            self.rev = int(self.rev_or_txn)
            self.is_rev = True
            assert self.rev >= 0
        except:
            assert isinstance(self.rev_or_txn, str)
            self.is_rev = False
            self.txn_name = self.rev_or_txn
            #self.txn = svn.fs.open_txn(self.fs, self.txn_name, p)
            self.txn = svn.fs.open_txn(self.fs, self.txn_name)

        if self.is_rev:
            #self.root = svn.fs.revision_root(self.fs, self.rev, p)
            self.root = svn.fs.revision_root(self.fs, self.rev)
        else:
            #self.root = svn.fs.txn_root(self.txn, p)
            self.root = svn.fs.txn_root(self.txn)

    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        self.__init_rev_or_txn()

        self.result = ChangeSet(**self.changeset_kwds)
        self.result.load()
        #with ChangeSet(**self.changeset_kwds) as cs:
        #    cs.load()
        #    self.result = cs

    @classmethod
    def get_changeset(cls, path, rev_or_txn, **kwds):
        k = DecayDict(**kwds)
        estream = k.get('estream', sys.stderr)
        ostream = k.get('ostream', sys.stdout)
        istream = k.get('istream', sys.stdout)

        c = ChangeSetCommand(ostream, estream)

        c.path    = path
        c.conf    = k.get('conf', Config())
        c.options = k.get('options', Options())
        c.rev_or_txn = rev_or_txn

        k.assert_empty(cls)

        with c:
            c.run()
            return c.result

class FindMergesCommand(RepositoryRevisionCommand):
    # XXX TODO: this is broken.
    """
    When set to True, run() will yield revisions that contain merges instead
    of printing them to stdout.  This functionality is used by the classmethod
    find_merges.
    """
    yield_values = False

    def __iter__(self):
        CSC = ChangeSetCommand

        revs = (self._start_rev, self._end_rev+1)
        for i in xrange(*revs):
            with Pool() as pool:
                k = CSC.get_changeset_kwds_for_rev_or_txn(self, i, pool)
                with ChangeSet(**k) as cs:
                    cs.load()
                    yield (i, cs.has_merges)

    def _find_merges(self):
        CSC = ChangeSetCommand

        revs = (self._start_rev, self._end_rev+1)
        for i in xrange(*revs):
            with Pool() as pool:
                k = CSC.get_changeset_kwds_for_rev_or_txn(self, i, pool)
                with ChangeSet(**k) as cs:
                    cs.load()
                    yield (i, cs.has_merges)

    @requires_context
    def run(self):
        RepositoryRevisionCommand.run(self)

        CSC = ChangeSetCommand

        if not self.yield_values:
            m = "Finding merges between revisions %d:%d..."
            self._err(m % (self._start_rev, self._end_rev))

            revs = (self._start_rev, self._end_rev+1)
            for i in xrange(*revs):
                with Pool(self.pool) as pool:
                    k = CSC.get_changeset_kwds_for_rev_or_txn(self, i, pool)
                    with ChangeSet(**k) as cs:
                        cs.load()

                        if cs.has_merges:
                            self.ostream.write('%d%s' % (i, os.linesep))
                            self._err('%d: merge' % i)

                        elif self._verbose:
                            self._err('%d' % i)

                self._flush()

    @requires_context
    def run_old(self):
        RepositoryRevisionCommand.run(self)

        if not self.yield_values:
            m = "Finding merges between revisions %d:%d..."
            self._err(m % (self._start_rev, self._end_rev))
            for (i, has_merges) in self:
                if has_merges:
                    self.ostream.write('%d%s' % (i, os.linesep))
                    self._err('%d: merge' % i)
                    self._flush()
                elif self._verbose:
                    self._err('%d' % i)
            self._flush()

    @classmethod
    def find_merges(cls, path, revision, **kwds):
        k = DecayDict(**kwds)
        estream = kwds.get('estream', sys.stderr)
        ostream = kwds.get('ostream', sys.stdout)
        istream = kwds.get('istream', sys.stdout)

        c = FindMergesCommand(istream, ostream, estream)

        c.revision = revision

        c.path    = path
        c.conf    = kwds.get('conf', Config())
        c.options = kwds.get('options', Options())

        k.assert_empty(cls)

        c.yield_values = True
        with c:
            c.run()
            return c

class PurgeEvnPropsCommand(RepositoryRevisionRangeCommand):
    @requires_context
    def run(self):
        RepositoryRevisionRangeCommand.run(self)

        fs = self.fs
        prefix = self.conf.propname_prefix
        revproplist = svn.fs.revision_proplist
        changerevprop = svn.fs.change_rev_prop
        for i in xrange(self._start_rev, self._end_rev+1):
            for key in revproplist(fs, i).keys():
                if key.startswith(prefix):
                    changerevprop(fs, i, key, None)
                    self._out('[%i]: deleting %s' % (i, key))

class ShowRevPropsCommand(RepositoryRevisionCommand):
    @requires_context
    def run(self):
        RepositoryRevisionCommand.run(self)

        fs = self.fs
        revproplist = svn.fs.revision_proplist
        d = revproplist(fs, self.rev)
        # Sample output:
        #   ipdb> svn.fs.revision_proplist(self.fs, 0)
        #   {'evn:version': '1', 'evn:component_depth': '0', 'evn:last_rev': '1', 'svn:date': '2015-03-23T20:36:45.498093Z'}
        #
        #   ipdb> svn.fs.revision_proplist(self.fs, 1)
        #   {'svn:log': '"Initializing repository."', 'evn:roots': "{'/trunk/': {'copies': {}, 'created': 1, 'creation_method': 'created'}}", 'svn:author': 'Trent', 'svn:date': '2015-03-23T20:36:45.522838Z'}

        r = {}
        for (key, value) in d.items():
            ix = key.find(':')
            try:
                v = literal_eval(value)
            except:
                v = value
            if ix != -1:
                prefix = key[:ix]
                suffix = key[ix+1:]
                if prefix not in r:
                    r[prefix] = {}
                r[prefix][suffix] = v
            else:
                r[key] = v

        m = "Showing revision properties for repository '%s' at r%d:"
        self._out(m % (self.name, self.rev))
        pprint.pprint(r, self.ostream)

class ShowBaseRevPropsCommand(ShowRevPropsCommand):
    @requires_context
    def run(self):
        self.rev_str = '0'
        ShowRevPropsCommand.run(self)

class IsRepoReadonlyCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        rc0 = self.r0_revprop_conf
        out = self._out
        err = self._err

        readonly = 'no'

        if 'readonly' in rc0:
            if rc0.get('readonly') == 1:
                readonly = 'yes'

        out(readonly)

class SetRepoReadonlyCommand(RepositoryCommand):
    message = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        message = self.options.message or self.conf.readonly_error_message

        rc0 = self.r0_revprop_conf
        rc0.readonly = 1
        if message:
            rc0.readonly_message = message

class UnsetRepoReadonlyCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        rc0 = self.r0_revprop_conf

        if 'readonly' not in rc0:
            return

        del rc0.readonly
        if 'readonly_message' in rc0:
            del rc0.readonly_message

class AddRootHintCommand(RepositoryRevisionCommand):
    root_path = None
    root_type = None

    @requires_context
    def run(self):
        RepositoryRevisionCommand.run(self)
        rev = self.rev
        root_path = format_dir(self.root_path)
        root_type = self.root_type
        assert root_type in ('tag', 'trunk', 'branch')

        rc0 = self.r0_revprop_conf

        if not rc0.get('root_hints'):
            rc0.root_hints = {}

        if not rc0['root_hints'].get(rev):
            rc0['root_hints'][rev] = {}

        hints = rc0['root_hints'][rev]
        if root_path in hints:
            msg = "hint already exists for %s@%d" % (root_path, rev)
            raise CommandError(msg)

        from evn.change import ChangeSet
        opts = Options()
        cs = ChangeSet(self.path, self.rev, opts)
        cs.load()

        import svn.fs
        from svn.core import (
            svn_node_dir,
            svn_node_file,
            svn_node_none,
            svn_node_unknown,
        )

        svn_root = cs._get_root(rev)
        node_kind = svn.fs.check_path(svn_root, root_path, self.pool)
        if node_kind == svn_node_none:
            msg = "no such path %s in revision %d"
            raise CommandError(msg % (root_path, rev))
        elif node_kind == svn_node_unknown:
            msg = "unexpected node type 'unknown' for path %s in revision %d"
            raise CommandError(msg % (root_path, rev))
        elif node_kind == svn_node_file:
            msg = "path %s was a file in revision %d, not a directory"
            raise CommandError(msg % (root_path, rev))
        else:
            assert node_kind == svn_node_dir, node_kind

        change = cs.get_change_for_path(root_path)
        if not change:
            msg = (
                "path %s already existed in revision %d; specify the revision "
                "it was created in when adding a root hint (tip: try running "
                "`svn log --stop-on-copy --limit 1 %s%s@%d` to get the "
                "correct revision to use)" % (
                    root_path,
                    rev,
                    self.uri,
                    root_path,
                    rev,
                )
            )
            raise CommandError(msg)

        if change.is_remove or change.is_modify:
            msg = (
                "path %s wasn't created in revision %d; you need to specify "
                "the revision it was created in when adding a root hint "
                "(tip: try running `svn log --stop-on-copy --limit 1 %s%s@%d`"
                " to get the correct revision to use)" % (
                    root_path,
                    rev,
                    self.uri,
                    root_path,
                    rev,
                )
            )
            raise CommandError(msg)

        hints[root_path] = root_type

        repo_name = self.conf.repo_name
        msg = 'Added root hint for %s@%d to %s.' % (root_path, rev, repo_name)
        self._out(msg)

        last_rev = rev-1
        rc0.last_rev = last_rev
        msg = (
            'Reset last rev to %d; run `evnadmin analyze %s` when ready to '
            'restart analysis from revision %d.' % (
                rev,
                repo_name,
                rev,
            )
        )
        self._out(msg)

class RemoveRootHintCommand(RepositoryRevisionCommand):
    root_path = None

    @requires_context
    def run(self):
        RepositoryRevisionCommand.run(self)
        root_path = format_dir(self.root_path)

        rev = self.rev

        rc0 = self.r0_revprop_conf

        if not rc0.get('root_hints'):
            raise CommandError("no such root hint: %s" % root_path)

        hints = rc0['root_hints'].get(rev)
        if not hints:
            msg = "no such root hint at r%d: %s" % (rev, root_path)
            raise CommandError(msg)

        if root_path not in hints:
            msg = "no such root hint at r%d: %s" % (rev, root_path)
            raise CommandError(msg)

        del hints[root_path]
        msg = "Removed root hint %r for r%d from %s."
        repo_name = self.conf.repo_name
        self._out(msg % (hint, rev, repo_name))

class AddRootExclusionCommand(RepositoryCommand):
    root_exclusion = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        root_exclusion = self.root_exclusion

        rc0 = self.r0_revprop_conf

        if not rc0.get('root_exclusions'):
            rc0.root_exclusions = []

        if root_exclusion in rc0.root_exclusions:
            msg = "root exclusion already exists for %s" % root_exclusion
            raise CommandError(msg)

        rc0.root_exclusions.append(root_exclusion)
        msg = 'Added root exclusion %s to %s.' % (
            root_exclusion,
            self.conf.repo_name,
        )
        self._out(msg)

class RemoveRootExclusionCommand(RepositoryCommand):
    root_exclusion = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        root_exclusion = self.root_exclusion

        rc0 = self.r0_revprop_conf

        if not rc0.get('root_exclusions'):
            raise CommandError('no root exclusions set')

        if root_exclusion not in rc0.root_exclusions:
            raise CommandError('no such root exclusion: %s' % root_exclusions)

        rc0.root_exclusions.remove(root_exclusion)
        msg = 'Removed root exclusion %s from %s.' % (
            root_exclusion,
            self.conf.repo_name,
        )
        self._out(msg)

class AddBranchesBasedirCommand(RepositoryCommand):
    branches_basedir = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        branches_basedir = format_dir(self.branches_basedir)

        rc0 = self.r0_revprop_conf

        if not rc0.get('branches_basedirs'):
            rc0.branches_basedirs = []

        basedirs = rc0.branches_basedirs
        if branches_basedir in basedirs:
            msg = "branches basedir already exists for %s" % branches_basedir
            raise CommandError(msg)

        basedirs.append(branches_basedir)
        repo_name = self.conf.repo_name
        msg = 'Added branches basedir %s to %s.' % (
            branches_basedir,
            self.conf.repo_name,
        )
        self._out(msg)

class RemoveBranchesBasedirCommand(RepositoryCommand):
    branches_basedir = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        branches_basedir = self.branches_basedir

        rc0 = self.r0_revprop_conf
        if not rc0.get('branches_basedirs'):
            raise CommandError('no branches basedirs present')

        basedirs = rc0.branches_basedirs
        if branches_basedir not in basedirs:
            msg = 'no such branches basedir: %s' % branches_basedir
            raise CommandError(msg)

        basedirs.remove(branches_basedir)
        msg = "Removed branches basedir %s from %s."
        self._out(msg % (branches_basedir, self.conf.repo_name))

class AddTagsBasedirCommand(RepositoryCommand):
    tags_basedir = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        tags_basedir = format_dir(self.tags_basedir)

        rc0 = self.r0_revprop_conf

        if not rc0.get('tags_basedirs'):
            rc0.tags_basedirs = []

        basedirs = rc0.tags_basedirs
        if tags_basedir in basedirs:
            msg = "tags basedir already exists for %s" % tags_basedir
            raise CommandError(msg)

        basedirs.append(tags_basedir)
        repo_name = self.conf.repo_name
        msg = 'Added tags basedir %s to %s.' % (tags_basedir, repo_name)
        self._out(msg)

class RemoveTagsBasedirCommand(RepositoryCommand):
    tags_basedir = None
    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        tags_basedir = self.tags_basedir

        rc0 = self.r0_revprop_conf
        if not rc0.get('tags_basedirs'):
            raise CommandError('no tags basedirs present')

        basedirs = rc0.tags_basedirs
        if tags_basedir not in basedirs:
            msg = 'no such tags basedir: %s' % tags_basedir
            raise CommandError(msg)

        basedirs.remove(tags_basedir)
        msg = "Removed tags basedir %s from %s."
        self._out(msg % (tags_basedir, self.conf.repo_name))

# vim:set ts=8 sw=4 sts=4 tw=78 et:
