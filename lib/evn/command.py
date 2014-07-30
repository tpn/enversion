#===============================================================================
# Imports
#===============================================================================
import os

import svn
import svn.fs
import svn.core
import svn.repos

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from evn.repo import (
    RepositoryRevisionConfig,
)

from evn.hook import (
    EvnHookFile,
    RepoHookFile,
)

from evn.util import (
    add_linesep_if_missing,
    prepend_error_if_missing,
    prepend_warning_if_missing,
    implicit_context,
    Dict,
    Pool,
    ImplicitContextSensitiveObject,
)

#===============================================================================
# Commands
#===============================================================================
class CommandError(Exception):
    pass

class Command(ImplicitContextSensitiveObject):
    __metaclass__ = ABCMeta

    def __init__(self, istream, ostream, estream):
        self.istream = istream
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

    def _allocate(self):
        """
        Called by `__enter__`.  Subclasses should implement this method if
        they need to do any context-sensitive allocations.  (`_deallocate`
        should also be implemented if this method is implemented.)
        """
        pass

    def _deallocate(self):
        """
        Called by `__exit__`.  Subclasses should implement this method if
        they've implemented `_allocate` in order to clean up any resources
        they've allocated once the context has been left.
        """
        pass

    def _verbose(self, msg):
        """
        Writes `msg` to output stream if '--verbose'.

        Does not prepend anything to `msg`.
        Adds trailing linesep to `msg` if there's not one already.
        """
        if self.options.verbose:
            self.ostream.write(add_linesep_if_missing(msg))

    def _out(self, msg):
        """
        Write `msg` to output stream if not '--quiet'.

        Does not prepend anything to `msg`.
        Adds trailing linesep to `msg` if there's not one already.
        """
        if not self.options.quiet:
            self.ostream.write(add_linesep_if_missing(msg))

    def _warn(self, msg):
        """
        Write `msg` to output stream regardless of '--quiet'.

        Prepends 'warning: ' to `msg` if it's not already present.
        Adds trailing linesep to `msg` if there's not one already.
        """
        self.ostream.write(prepend_warning_if_missing(msg))

    def _err(self, msg):
        """
        Write `msg` to error stream regardless of '--quiet'.


        Prepends 'error: ' to `msg` if it's not already present.
        Adds trailing linesep to `msg` if there's not one already.
        """
        self.estream.write(prepend_error_if_missing(msg))

    @abstractmethod
    def run(self):
        raise NotImplementedError

    @classmethod
    def prime(cls, src, dst_class):
        c = dst_class(src.istream, src.ostream, src.estream)
        c.conf = src.conf
        c.options = src.options
        return c


class SubversionCommand(Command):
    pool = None
    def _allocate(self):
        self.pool = svn.core.Pool()

    def _deallocate(self):
        self.pool.destroy()

class RepositoryCommand(SubversionCommand):
    fs   = None
    rc0  = None
    uri  = None
    path = None
    name = None
    repo = None

    hook_dir   = None
    hook_names = None

    last_rev = None
    youngest_rev = None

    _hook_files = None
    _evn_hook_file = None
    _repo_hook_files = None

    @property
    def repo_kwds(self):
        k = Dict()
        k.fs   = self.fs
        k.uri  = self.uri
        k.conf = self.conf
        k.repo = self.repo
        k.path = self.path
        k.name = self.name
        k.istream = self.istream
        k.ostream = self.ostream
        k.estream = self.estream
        k.options = self.options
        k.r0_revprop_conf = self.r0_revprop_conf
        return k

    @implicit_context
    def run(self):
        assert self.path
        self.path = os.path.abspath(self.path)

        if not os.path.exists(self.path):
            m = "repository path does not exist: '%s'"
            raise CommandError(m % self.path)

        self.uri = 'file://%s' % self.path.replace('\\', '/')
        self.name = os.path.basename(self.path)
        self.conf.load_repo(self.path)
        self.hook_names = self.conf.hook_names

        self.repo       = svn.repos.open(self.path, self.pool)
        self.fs         = svn.repos.fs(self.repo)
        self.hook_dir   = svn.repos.hook_dir(self.repo, self.pool)

        self.youngest_rev = svn.fs.youngest_rev(self.fs, self.pool)

        k = dict(fs=self.fs, rev=0, conf=self.conf)
        rc0 = self.r0_revprop_conf = RepositoryRevisionConfig(**k)
        last_rev_str = rc0.get('last_rev', None)
        if last_rev_str is not None:
            self.last_rev = int(last_rev_str)

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

    @implicit_context
    def run(self):
        RepositoryCommand.run(self)
        assert self.hook_name in self.hook_names
        self.hook = self.hook_file(self.hook_name)

class RepositoryRevisionCommand(RepositoryCommand):
    """
    Subclass of RepositoryCommand that supports a single revision argument.

    ``rev_str`` should be set to a string-representation of the revision
    argument prior to calling ``run()`` by the calling class (this is taken
    care of by ``evn.cli.CommandLine``).  It will be validated and the
    resulting revision integer placed in ``rev``.

    If ``rev_str`` is None, evn:last_rev is looked up and used, if defined and
    valid.  If not, HEAD is used.
    """
    rev_str = None
    rev = None

    @implicit_context
    def run(self):
        RepositoryCommand.run(self)

        if self.rev_str is None:
            if self.last_rev is None:
                self.rev_str = 'HEAD'
            else:
                self.rev_str = self.last_rev

        if self.rev_str == 'HEAD':
            r = self.youngest_rev
        else:
            try:
                r = int(self.rev_str)
            except ValueError:
                raise CommandError("invalid revision: '%s'" % self.rev_str)

        if r < 1:
            raise CommandError("invalid revision: '%d'" % r)

        if r > self.youngest_rev:
            m = "revision '%d' is too high, repository is only at r%d"
            raise CommandError(m % (r, self.youngest_rev))

        self.rev = r



class RepositoryRevisionRangeCommand(RepositoryCommand):
    revision_range = None

    _end_rev = None
    _start_rev = None
    _highest_rev = None

    @property
    def _minimum_rev(self):
        return 0

    def _parse_rev_range(self, start_rev_str, end_rev_str):
        pass


    @implicit_context
    def run(self):
        RepositoryCommand.run(self)

        if not self.revision_range:
            self.revision_range = '%d:HEAD' % self._minimum_rev

        if ':' not in self.revision_range:
            self.revision_range += ':HEAD'

        if self.revision_range.endswith(':'):
            self.revision_range += ':HEAD'

        if self.revision_range.startswith(':'):
            self.revision_range = '%d%s' % (
                self._minimum_rev,
                self.revision_range
            )

        rev_t = svn.core.svn_opt_revision_t
        parse_rev = svn.core.svn_opt_parse_revision

        with Pool() as pool:
            self._highest_rev = svn.fs.youngest_rev(self.fs, pool)

            if self.revision_range.endswith('HEAD'):
                self.revision_range = (
                    self.revision_range[:-4] +
                    str(self._highest_rev)
                )

            (start, end) = (rev_t(), rev_t())
            start.set_parent_pool(pool)
            end.set_parent_pool(pool)
            result = parse_rev(start, end, self.revision_range, pool)
            assert result in (0, -1)
            if result == -1:
                m = "invalid revision: %s" % self.revision_range
                raise CommandError(m)

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

# vim:set ts=8 sw=4 sts=4 tw=78 et:
