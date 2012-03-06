
#=============================================================================
# Commands
#=============================================================================
class CommandError(Exception):
    pass

class Command:
    __metaclass__ = ABCMeta

    def __init__(self, ostream, estream):
        self.ostream = ostream
        self.estream = estream

        self.conf = None
        self.args = None
        self.result = None
        self.options = None

        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        self._allocate()
        return self

    def __exit__(self, *exc_info):
        self.exited = True
        self._deallocate()

    def _flush(self):
        self.ostream.flush()
        self.estream.flush()

    def _err(self, msg):
        self.estream.write(add_linesep_if_missing(msg))

    def _allocate(self):
        pass

    def _deallocate(self):
        pass

    @property
    def _verbose(self):
        try:
            return (self.options.verbose == True)
        except AttributeError:
            return False

    def _out(self, msg):
        if not self._verbose:
            return
        self.ostream.write(add_linesep_if_missing(msg))

    def _warn(self, msg):
        self.ostream.write(add_linesep_if_missing(msg))

    @abstractmethod
    def run(self):
        raise NotImplementedError

    @classmethod
    def prime(cls, src, dst_class):
        c = dst_class(src.ostream, src.estream)
        c.conf = src.conf
        c.options = src.options
        return c


class SubversionCommand(Command):
    pool = None
    def _allocate(self):
        init_svn_libraries()
        self.pool = svn.core.Pool()

    def _deallocate(self):
        self.pool.destroy()


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

class RepositoryCommand(SubversionCommand):
    fs   = None
    rc0  = None
    uri  = None
    path = None
    name = None
    repo = None

    hook_dir   = None
    hook_names = None

    _hook_files = None
    _evn_hook_file = None
    _repo_hook_files = None

    @property
    def repo_kwds(self):
        k = Dict()
        k.fs   = self.fs
        k.uri  = self.uri
        k.conf = self.conf
        #k.pool = self.pool
        k.repo = self.repo
        k.path = self.path
        k.name = self.name
        k.estream = self.estream
        k.ostream = self.ostream
        k.options = self.options
        k.r0_revprop_conf = self.r0_revprop_conf
        return k

    @requires_context
    def run(self):
        assert self.path
        self.path = os.path.abspath(self.path)

        if not os.path.exists(self.path):
            m = "repository path does not exist: '%s'"
            raise CommandError(m % self.path)

        self.uri = 'file://%s' % self.path.replace('\\', '/')
        self.name = os.path.basename(self.path)
        self.hook_names = self.conf.hook_names

        #self.repo       = svn.repos.open(self.path, self.pool)
        self.repo       = svn.repos.open(self.path)
        self.fs         = svn.repos.fs(self.repo)
        self.hook_dir   = svn.repos.hook_dir(self.repo)

        #k = dict(fs=self.fs, rev=0, pool=self.pool)
        k = dict(fs=self.fs, rev=0, conf=self.conf)
        self.r0_revprop_conf = RepositoryRevisionConfig(**k)

    def hook_file(self, name):
        if self._repo_hook_files is None:
            self._repo_hook_files = dict()

        if name not in self._repo_hook_files:
            assert name in self.hook_names
            self._repo_hook_files[name] = RepoHookFile(self, name)
        return self._repo_hook_files[name]

    @property
    def hook_files(self):
        if self._hook_files is None:
            self._hook_files = [ self.hook_file(n) for n in self.hook_names ]
        return self._hook_files

    @property
    def evn_hook_file(self):
        if not self._evn_hook_file:
            self._evn_hook_file = EvnHookFile(self)
        return self._evn_hook_file

class RepoHookCommand(RepositoryCommand):
    hook_name = None
    hook = None

    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        assert self.hook_name in self.hook_names
        self.hook = self.hook_file(self.hook_name)

class RepositoryRevisionCommand(RepositoryCommand):
    revision = None

    _end_rev = None
    _start_rev = None
    _highest_rev = None

    @property
    def _minimum_rev(self):
        return 0

    @requires_context
    def run(self):
        RepositoryCommand.run(self)

        if not self.revision:
            self.revision = '%d:HEAD' % self._minimum_rev

        if ':' not in self.revision:
            self.revision += ':HEAD'

        if self.revision.endswith(':'):
            self.revision += ':HEAD'

        if self.revision.startswith(':'):
            self.revision = '%d%s' % (self._minimum_rev, self.revision)

        rev_t = svn.core.svn_opt_revision_t
        parse_rev = svn.core.svn_opt_parse_revision

        with Pool() as pool:
            self._highest_rev = svn.fs.youngest_rev(self.fs, pool)

            if self.revision.endswith('HEAD'):
                self.revision = self.revision[:-4] + str(self._highest_rev)

            (start, end) = (rev_t(), rev_t())
            start.set_parent_pool(pool)
            end.set_parent_pool(pool)
            result = parse_rev(start, end, self.revision, pool)
            assert result in (0, -1)
            if result == -1:
                raise CommandError("invalid revision: %s" % self.revision)

            if start.kind != svn.core.svn_opt_revision_number:
                raise CommandError("only numbers are supported for start rev")

            valid_end_kinds = (
                svn.core.svn_opt_revision_head,
                svn.core.svn_opt_revision_number
            )
            if end.kind not in valid_end_kinds:
                m = "end revision must be a number or 'HEAD'"
                raise CommandError(m)

            self._start_rev = start.value.number
            if self._start_rev > self._highest_rev:
                m = "start revision %d is too high (HEAD is at %d)"
                raise CommandError(m % (self._start_rev, self._highest_rev))

            if end.kind == svn.core.svn_opt_revision_head:
                self._end_rev = self._highest_rev
            else:
                self._end_rev = end.value.number
                if self._end_rev > self._highest_rev:
                    m = "end revision %d is too high (HEAD is at %d)"
                    raise CommandError(m % (self._end_rev, self._highest_rev))

            if self._start_rev > self._end_rev:
                raise CommandError("end rev must be higher than start rev")

