#=============================================================================
# Imports
#=============================================================================
import os
import sys
import traceback

import svn
import svn.fs

from evn.config import (
    Config,
)

from evn.repo import (
    RepositoryError,
    RepositoryRevOrTxn,
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
    requires_context,
    Pool,
    Dict,
    Options,
    DecayDict,
)

#=============================================================================
# Administrative Commands
#=============================================================================

class DoctestCommand(Command):
    def run(self):
        import doctest
        doctest.testmod()

class DumpDefaultConfigCommand(Command):
    def run(self):
        cf = Config()
        cf.write(self.ostream)

class DumpConfigCommand(Command):
    def run(self):
        self.conf.write(self.ostream)

class ShowConfigFileLoadOrderCommand(Command):
    def run(self):
        if not self.conf.files:
            raise CommandError('no configuration files are being loaded')
        self._warn(os.linesep.join(self.conf.files))

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

        for h in self.hook_files:
            if not h.needs_fixing:
                continue

            with FixHookCommand(self.ostream, self.estream) as fh:
                fh.path = self.path
                fh.conf = self.conf
                fh.options = self.options
                fh.hook_name = h.name
                fh.run()

        if not self.evn_hook_file.needs_fixing:
            return

        with FixEvnHookCommand(self.ostream, self.estream) as fh:
            fh.path = self.path
            fh.conf = self.conf
            fh.options = self.options
            fh.run()

class EnableCommand(FixHooksCommand):
    @requires_context
    def run(self):
        FixHooksCommand.run(self)

        for h in self.hook_files:
            if not h.is_enabled:
                h.enable()

class CreateRepoCommand(SubversionCommand):
    path = None
    @requires_context
    def run(self):
        assert self.path
        r = svn.repos.create(self.path, None, None, None, None, self.pool)
        assert r

        with Command.prime(self, EnableCommand) as command:
            command.path = self.path
            command.run()

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

        l = None
        if self.conf.get('errors', 'log-errors') == 'yes':
            import logging
            import logging.handlers
            l = logging.getLogger(self.conf.get('errors', 'log-name'))
            l.setLevel(self.conf.get('errors', 'log-level'))
            fn = self.conf.get('errors', 'log-filename')
            mb = int(self.conf.get('errors', 'log-max-mb')) * 1024 * 1024
            bc = int(self.conf.get('errors', 'log-backup-count'))
            k = dict(maxBytes=mb, backupCount=bc)
            h = logging.handlers.RotatingFileHandler(fn, **k)
            f = logging.Formatter(self.conf.get('errors', 'log-format'))
            h.setFormatter(f)
            l.addHandler(h)

        with RepositoryHook(**self.repo_kwds) as r:
            try:
                r.run_hook(self.hook_name, self.hook_args)
            except Exception as exc:
                if l is not None:
                    (exc_type, exc_value, exc_tb) = sys.exc_info()
                    m = "Repository %s hook failed (hook args: %s):%s%s"
                    args = ', '.join('%s' % repr(a) for a in self.hook_args)
                    e = ''.join(traceback.format_exception(*sys.exc_info()))
                    l.critical(m % (self.hook_name, args, os.linesep, e))
                if isinstance(exc, RepositoryError):
                    self._err(exc.args[0])
                    sys.exit(1)
                else:
                    raise

class AnalyzeRepoCommand(RepositoryCommand):
    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        rc0 = self.r0_revprop_conf

        last_rev = rc0.get('last_rev', None)
        start_rev = last_rev if last_rev is not None else 0
        end_rev = svn.fs.youngest_rev(self.fs)

        if last_rev is not None:
            if start_rev == end_rev:
                m = "Repository '%s' is up to date (r%d)."
                self._warn(m % (self.name, end_rev))
                return
            m = "Resuming analysis for repository '%s' from revision %d..."
            self._out(m % (self.name, start_rev))

        k = self.repo_kwds
        import gc
        gc.disable()
        try:
            for i in xrange(start_rev, end_rev+1):
                with RepositoryRevOrTxn(**k) as r:
                    r.process_rev_or_txn(i)
                    if i == 0:
                        continue
                    cs = r.changeset
                    self._out(str(i) + ':' + cs.analysis.one_liner)
        finally:
            gc.enable()

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

        c = FindMergesCommand(ostream, estream)

        c.revision = revision

        c.path    = path
        c.conf    = kwds.get('conf', Config())
        c.options = kwds.get('options', Options())

        k.assert_empty(cls)

        c.yield_values = True
        with c:
            c.run()
            return c

# vim:set ts=8 sw=4 sts=4 tw=78 et:
