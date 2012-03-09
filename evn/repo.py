#=============================================================================
# Imports
#=============================================================================
import os
import sys
import time
import logging
import datetime
import itertools
import cStringIO as StringIO

from pprint import pformat

import ConfigParser as configparser
ConfigParser = configparser.RawConfigParser

import svn
import svn.fs
import svn.core

from svn.core import (
    svn_node_dir,
    svn_node_file,

    svn_mergeinfo_parse,

    SVN_PROP_MERGEINFO,
    SVN_PROP_REVISION_LOG,
    SVN_PROP_REVISION_AUTHOR,
)

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from evn.path import (
    join_path,
    format_dir,
    PathMatcher,
)

from evn.root import (
    Roots,
    RootDetails,
    RootPathMatcher,
    SimpleRootMatcher,
    AbsoluteRootDetails,
)

from evn.change import (
    ChangeSet,
    ChangeType,
    PropertyChangeType,
    ExtendedPropertyChangeType,
)

from evn.util import (
    literal_eval,
    requires_context,
    Pool,
    Dict,
    DecayDict,
    ConfigDict,
    UnexpectedCodePath,
)

from evn.constants import (
    EVN_BRPROPS_SCHEMA,
    EVN_BRPROPS_SCHEMA_VERSION,
    EVN_RPROPS_SCHEMA,
    EVN_RPROPS_SCHEMA_VERSION,
    EVN_ERROR_CONFIRMATIONS,
    n,  # Notes
    w,  # Warnings
    e,  # Errors
)

#=============================================================================
# Repository-related Configuration Classes
#=============================================================================

class AbstractRepositoryConfig(dict):
    __metaclass__ = ABCMeta

    def __init__(self, **kwds):
        k = DecayDict(kwds)
        self.__conf = k.conf
        k.assert_empty(self)

    @property
    def conf(self):
        return self.__conf

    @abstractmethod
    def _write(self, name, value):
        raise NotImplementedError()

    @abstractmethod
    def _read(self, name):
        raise NotImplementedError()

    @abstractmethod
    def _proplist(self):
        raise NotImplementedError()

    def __repr__(self):
        return object.__repr__(self)

    def __delattr__(self, name):
        if name.startswith('_'):
            return dict.__delattr__(name)
        else:
            return self._del(name)

    def __delitem__(self, name):
        if name.startswith('_'):
            return dict.__delitem__(name)
        else:
            return self._del(name)

    def __getattr__(self, name):
        if name.startswith('_'):
            return dict.__getattribute__(self, name)
        else:
            return self.__getitem__(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            dict.__setattr__(self, name, value)
        else:
            self._set(name, value)

    def __setitem__(self, name, value):
        if name.startswith('_'):
            dict.__setattr__(self, name, value)
        else:
            self._set(name, value)

    def _del(self, name, default=False, skip_reload=False):
        # Deleting a property is done by propset'ing a None value.
        self._set(name, None, default=default, skip_reload=skip_reload)

    def __contains__(self, key):
        return self._format_propname(key) in self._proplist

    def _format_propname(self, name):
        assert name and name[0] != '_'
        propname_prefix = self.conf.propname_prefix
        if not name.startswith(propname_prefix + ':'):
            return ':'.join((propname_prefix, name))
        else:
            return name

    def _unformat_propname(self, name):
        propname_prefix = self.conf.propname_prefix + ':'
        if name and name.startswith(propname_prefix):
            name = name[len(propname_prefix):]

        assert name and name[0] != '_'
        return name

    def _save(self, name, value):
        self._set(name, value, skip_reload=True)

    def _stub(self, name):
        if name not in self:
            dict.__setitem__(self, name, None)

    def _set(self, name, value, default=False, skip_reload=False):
        name = self._format_propname(name)

        value = self._try_convert(value, name, itertools.count(0))
        self._write(name, value)

        if not skip_reload:
            self._reload()

    def _try_convert(self, orig_value, propname, attempts):
        c = itertools.count(0)

        eval_value = None
        conv_value = None

        last_attempt = False

        attempt = attempts.next()

        try:
            if attempt == c.next():
                assert orig_value == literal_eval(orig_value)
                return orig_value

            if attempt == c.next():
                conv_value = pformat(orig_value)
                eval_value = literal_eval(conv_value)
                assert eval_value == orig_value
                return conv_value

            if attempt == c.next():
                conv_value = '"""%s"""' % pformat(orig_value)
                eval_value = literal_eval(conv_value)
                assert eval_value == orig_value
                return conv_value

            if attempt == c.next():
                conv_value = repr(orig_value)
                eval_value = literal_eval(conv_value)
                assert eval_value == orig_value
                return conv_value

            if attempt == c.next():
                conv_value = str(orig_value)
                eval_value = literal_eval(conv_value)
                assert eval_value == orig_value
                return conv_value

            last_attempt = True

        except:
            if not last_attempt:
                return self._try_convert(orig_value, propname, attempts)
            else:
                m = e.PropertyValueConversionFailed % (propname, orig_value)
                raise ValueError(m)

    @abstractproperty
    def readonly(self):
        raise NotImplementedError()

    @abstractproperty
    def _proplist(self):
        raise NotImplementedError()

    def _reload_value(self, name, value):
        v = value
        if isinstance(v, dict):
            v = ConfigDict(self, name, v)
        if isinstance(v, list):
            v = ConfigList(self, name, v)
        return v

    def _reload_complete(self, data):
        pass

    def _reload(self):
        d = dict()
        prefix = self.conf.propname_prefix + ':'
        for (key, value) in self._proplist.items():
            if not key.startswith(prefix):
                continue

            try:
                v = literal_eval(value)
            except:
                m = e.PropertyValueLiteralEvalFailed % (key, value)
                raise ValueError(m)

            v = self._reload_value(key, v)
            d[self._unformat_propname(key)] = v

        self._reload_complete(d)
        self.clear()
        self.update(d)

class RepositoryRevisionConfig(AbstractRepositoryConfig):
    def __init__(self, **kwds):
        k = DecayDict(kwds)
        AbstractRepositoryConfig.__init__(self, conf=k.conf)
        self.__fs = k.fs
        self.__rev = k.get('rev')
        self.__readonly = False
        if self.rev is None:
            self.__rev = k.base_rev
            self.__readonly = True
        k.assert_empty(self)

        assert self.rev >= 0

        self._reload()

    @property
    def rprop_schema_version(self):
        return 1

    @property
    def brprop_schema_version(self):
        return 1

    @property
    def pool(self):
        return Pool()

    @property
    def fs(self):
        return self.__fs

    @property
    def rev(self):
        return self.__rev

    @property
    def readonly(self):
        return self.__readonly

    def _reload_value(self, name, value):
        if self.rev == 0:
            return self.__reload_brprop_value(name, value)
        elif self.rev > 0:
            return self.__reload_rprop_value(name, value)
        else:
            raise UnexpectedCodePath()

    def __reload_brprop_value(self, name, value):
        args = (self, name, value)
        if self.brprop_schema_version == 1:
            return AbstractRepositoryConfig._reload_value(*args)
        else:
            raise UnexpectedCodePath()

    def __reload_rprop_value(self, name, value):
        args = (self, name, value)
        if self.rprop_schema_version == 1:
            if name == self._format_propname('roots'):
                return Roots(self, value)
            else:
                return AbstractRepositoryConfig._reload_value(*args)
        else:
            raise UnexpectedCodePath()

    def _reload_complete(self, d):
        if self.rev == 0:
            default = EVN_BRPROPS_SCHEMA[self.brprop_schema_version]
        else:
            default = EVN_RPROPS_SCHEMA[self.rprop_schema_version]
        keys = (self._unformat_propname(k) for k in default.keys())
        d.update((k, None) for k in keys if k not in d)

    @property
    def _proplist(self):
        with self.pool as pool:
            return svn.fs.revision_proplist(self.fs, self.rev, pool)

    def _write(self, name, value):
        if not self.readonly:
            with self.pool as pool:
                svn.fs.change_rev_prop(self.fs, self.rev, name, value, pool)

    def _read(self, name):
        with self.pool as pool:
            return svn.fs.revision_prop(self.fs, self.rev, name, pool)

#=============================================================================
# Classes
#=============================================================================
class RepositoryError(Exception):
    pass

class RepositoryRevOrTxn(object):
    def __init__(self, **kwds):
        k = DecayDict(**kwds)

        self.fs                 = k.fs
        self.uri                = k.uri
        self.conf               = k.conf
        self.name               = k.name
        self.path               = k.path
        self.repo               = k.repo
        self.estream            = k.estream
        self.ostream            = k.ostream
        self.options            = k.options
        self.r0_revprop_conf    = k.r0_revprop_conf

        k.assert_empty(self)

        self.entered = False
        self.exited  = False

        self.error                              = str()

        self._changes_by_root_details           = dict()
        self._root_details                      = dict()
        self._rootmatchers                      = dict()
        self.__absolute_root_details            = None
        self.__roots                            = None

        self.__conf                             = None
        self.__conf_initialised                 = False

        self.__revprop_conf                     = None
        self.__revprop_conf_initialised         = False

        self.__r0_revprop_conf                  = None
        self.__r0_revprop_conf_initialised      = False

        self.__base_revprop_conf                = None
        self.__base_revprop_conf_initialised    = False

        self.__changeset                        = None
        self.__changeset_initialised            = False

        self.__rootchangeset                    = None
        self.__rootchangeset_initialised        = False

        self.__rootchangesets                   = list()
        self.__rootchangesets_initialised       = False

        self.__last_rev                         = int()
        self.__revlock_file                     = str()
        self.__base_revlock_file                = str()
        self.__base_rev_roots                   = dict()

        self.__closed                           = False

        self.__evn_dir                          = str()
        self.__evn_db_dir                       = str()
        self.__evn_logs_dir                     = str()
        self.__evn_locks_dir                    = str()

        self.__admins                           = None

        self.authz_conf                         = ConfigParser()
        self.authz_admins                       = set()
        self.authz_groups                       = dict()
        self.authz_overrides                    = set()


    def __enter__(self):
        assert self.entered is False
        self.entered = True
        self.pool = svn.core.Pool()
        return self

    def __exit__(self, *exc_info):
        if self.__changeset_initialised:
            self.__changeset.destroy()
            self.__changeset = None
        self.pool.destroy()
        self.exited = True

    @requires_context
    def process_rev_or_txn(self, rev_or_txn):
        self.rev_or_txn = rev_or_txn
        assert self.rev_or_txn is not None

        p = self.pool
        try:
            self.__rev = int(self.rev_or_txn)
            self.__is_rev = True
            assert self.rev >= 0
        except:
            assert isinstance(self.rev_or_txn, str)
            self.__is_rev = False
            self.__txn_name = self.rev_or_txn
            self.__txn = svn.fs.open_txn(self.fs, self.txn_name, p)
            #self._init_hook_file()

        if self.is_rev:
            self.root     = svn.fs.revision_root(self.fs, self.rev, p)
            self.revprops = svn.fs.revision_proplist(self.fs, self.rev, p)
            self.base_rev = self.rev-1
        else:
            self.root     = svn.fs.txn_root(self.txn, p)
            self.revprops = svn.fs.txn_proplist(self.txn, p)
            self.base_rev = svn.fs.txn_base_revision(self.txn)

        self._init_evn()

        self._copies_processed = set()
        self._creates_processed = set()
        self._renames_processed = set()
        self._modifies_processed = set()
        self._removals_processed = set()

        self._change_type_to_processed_set = {
            ChangeType.Copy     : self._copies_processed,
            ChangeType.Create   : self._creates_processed,
            ChangeType.Rename   : self._renames_processed,
            ChangeType.Remove   : self._removals_processed,
            ChangeType.Modify   : self._modifies_processed,
        }

        self._replacements_processed = set()

        self._init_authz_conf()
        self.pathmatcher = RootPathMatcher()

    @property
    def log_msg(self):
        return self.revprops.get(SVN_PROP_REVISION_LOG)

    @property
    def user(self):
        return self.revprops.get(SVN_PROP_REVISION_AUTHOR)

    @property
    def is_rev(self):
        return self.__is_rev

    @property
    def is_txn(self):
        return not self.__is_rev

    @property
    def rev(self):
        assert self.is_rev
        return self.__rev

    @property
    def txn_name(self):
        assert self.is_txn
        return self.__txn_name

    @property
    def txn(self):
        assert self.is_txn
        return self.__txn

    @property
    def is_repository_hook(self):
        return False

    def _init_evn(self):
        self.is_rev_for_empty_repo = self.is_rev and self.rev == 0
        self.is_rev_for_first_commit = self.is_rev and self.rev == 1
        self.is_txn_for_first_commit = self.is_txn and self.base_rev == 0
        self.is_normal_rev_or_txn = (
            (self.is_txn and self.base_rev >= 1) or
            (self.is_rev and self.rev > 1)
        )

        # Test mutually-exclusive invariants.
        # XXX TODO: convert to MutexDecayDict.
        assert (
            (self.is_rev_for_empty_repo and (
                not self.is_txn_for_first_commit and
                not self.is_rev_for_first_commit and
                not self.is_normal_rev_or_txn
            )) or (self.is_rev_for_first_commit and (
                not self.is_rev_for_empty_repo and
                not self.is_txn_for_first_commit and
                not self.is_normal_rev_or_txn
            )) or (self.is_txn_for_first_commit and (
                not self.is_rev_for_empty_repo and
                not self.is_rev_for_first_commit and
                not self.is_normal_rev_or_txn
            )) or (self.is_normal_rev_or_txn and (
                not self.is_rev_for_empty_repo and
                not self.is_rev_for_first_commit and
                not self.is_txn_for_first_commit
            ))
        )

        rc0 = self.r0_revprop_conf

        if self.is_rev_for_empty_repo and 'version' not in rc0:
            rc0.last_rev = 0
            rc0.version = EVN_BRPROPS_SCHEMA_VERSION

        version = self._load_evn_revprop_int('version', 1)
        if version != EVN_BRPROPS_SCHEMA_VERSION:
            m = e.VersionMismatch % (EVN_BRPROPS_SCHEMA_VERSION, version)
            self.die(m)

        if version == 1:
            self._init_evn_v1()
        else:
            raise UnexpectedCodePath

    @property
    def good_last_rev(self):
        self._reload_last_rev()
        if self.is_repository_hook:
            return bool(self.last_rev == self.base_rev)
        else:
            assert self.is_rev
            return bool(self.last_rev >= self.base_rev)

    @property
    def good_base_rev_roots(self):
        brc = self.base_revprop_conf
        brc._reload()
        return bool(isinstance(brc.roots, Roots))

    def _last_rev_is_bad(self):
        if self.is_rev:
            a = (self.rev, self.base_rev, self.last_rev, self.latest_rev)
            if self.is_repository_hook:
                m = e.LastRevNotSetToBaseRevDuringPostCommit
            else:
                m = e.OutOfOrderRevisionProcessingAttempt
        else:
            assert self.is_txn
            a = (self.base_rev, self.last_rev, self.latest_rev)
            if self.base_rev < self.last_rev:
                m = e.StaleTxnProbablyDueToHighLoad
            else:
                m = e.RepositoryOutOfSyncTxn

        self.die(m % a)

    def _base_rev_roots_is_bad(self):
        if self.is_rev:
            a = (self.rev, self.base_rev, self.last_rev, self.latest_rev)
            if self.is_repository_hook:
                m = e.RootsMissingFromBaseRevDuringPostCommit
            else:
                m = e.InvalidRootsForRev
            self.die(m % a)
        else:
            assert self.is_txn
            a = (self.txn_name, self.base_rev, self.last_rev, self.latest_rev)
            m = e.RootsMissingFromBaseRevTxn

        self.die(m % a)

    def _last_rev_and_base_rev_roots_are_good(self):
        try:
            os.unlink(self.base_rev_lockfile)
        except:
            pass

        brc = self.base_revprop_conf
        assert isinstance(brc.roots, Roots)
        if self.is_txn:
            self.__roots = (brc, brc.roots)
            return

        assert self.is_rev

        rc = self.revprop_conf

        # XXX force override for now.
        self.__roots = (rc, self._inherit_roots(brc.roots))
        return

        if rc.roots is not None:
            # We must be re-processing an already-processed revision.
            assert isinstance(rc.roots, Roots)
            self.__roots = (rc, dict(rc.roots))
        else:
            # Processing a revision for the first time outside the context
            # of a post-commit hook, i.e. repo is being analysed.  As with
            # the post-commit processing logic above, we bring over a sim-
            # plified version of the base_rev's roots via _inherit_roots.
            self.__roots = (rc, self._inherit_roots(brc.roots))

    def _init_evn_v1(self):

        self.__init_evn_dir_v1()

        if self.is_rev_for_empty_repo:
            return

        if self.is_txn_for_first_commit or self.is_rev_for_first_commit:
            assert self.base_rev == 0
            k = Dict()
            if self.is_txn:
                k.base_rev = 0
            else:
                k.rev = 1
            c = self.rconf(**k)
            self.__roots = (c, {})
            return

        assert self.base_rev > 0
        if self.is_rev:
            assert self.rev >= 2
        else:
            assert self.base_rev >= 1

        max_revlock_waits = self.conf.get('main', 'max-revlock-waits')

        # Quick sanity check of last_rev to make sure it's not higher than the
        # highest rev of the repository.
        self._reload_last_rev()
        highest_rev = svn.fs.youngest_rev(self.fs, self.pool)
        if self.last_rev > highest_rev:
            self.die(e.LastRevTooHigh % (self.last_rev, highest_rev))

        if self.is_rev and self.is_repository_hook:
            with open(self.rev_lockfile, 'w') as f:
                f.write(str(os.getpid()))
                f.flush()
                f.close()

        if self.good_last_rev and self.good_base_rev_roots:
            self._last_rev_and_base_rev_roots_are_good()
            return

        a = (str(self.rev_or_txn), self.base_rev, self.last_rev)
        self._dbg('rev_or_txn: %s, base_rev: %d, last_rev: %d' % a)

        found = False
        fn = self.base_rev_lockfile
        count = itertools.count()
        while True:
            c = count.next()
            self._dbg('looking for revlock file: %s (attempt: %d)' % (fn, c))
            if os.path.isfile(fn):
                found = True
                self._dbg('found revlock after %d attempts' % c)
                break
            time.sleep(1)
            if c == max_revlock_waits:
                self._dbg('no revlock found after %d attempts' % c)
                break

        if self.good_last_rev and self.good_base_rev_roots:
            self._last_rev_and_base_rev_roots_are_good()
            return

        if found:
            s = None
            try:
                s = open(fn, 'r').read()
            except:
                pass
            if not s:
                self._dbg('failed to open/read lock file %s' % fn)
            else:
                try:
                    pid = int(s)
                    self._dbg("pid for lock file %s: %d" % (fn, pid))
                except:
                    self._dbg("invalid pid for lock file %s: %s" % (fn, s))
                else:
                    count = itertools.count()
                    still_running = pid_exists(pid)
                    while still_running:
                        a = (count.next(), pid)
                        self._dbg("[%d] pid %d is still running" % a)
                        time.sleep(1)
                        still_running = pid_exists(pid)

        good_last_rev = self.good_last_rev
        good_base_rev_roots = self.good_base_rev_roots
        if good_last_rev and good_base_rev_roots:
            self._last_rev_and_base_rev_roots_are_good()
            return

        if not good_last_rev:
            self._last_rev_is_bad()

        if not good_base_rev_roots:
            self._base_rev_roots_is_bad()

        raise UnexpectedCodePath

    def _dbg(self, msg):
        pass

    def _inherit_roots(self, roots):
        d = lambda v: { 'created' : v['created'] }
        return dict((k, d(v)) for (k, v) in roots.items())

    def die(self, error=None):
        if error is not None:
            self.error = error
        if not self.error:
            self.error = e.InvariantViolatedDieCalledWithoutErrorInfo

        needs_prefix = (
            not self.error.startswith('error') and
            not self.error.startswith('warning')
        )
        if needs_prefix:
            self.error = 'error: ' + self.error

        raise RepositoryError(self.error)

    def _load_evn_revprop_int(self, n, greater_than_or_equal_to):
        gt = greater_than_or_equal_to
        rc0 = self.r0_revprop_conf
        v = rc0.get(n)
        if v is None or v == '':
            self.die(e.MissingOrEmptyRevPropOnRev0 % n)

        try:
            i = int(v)
            valid = bool(i >= gt)
        except ValueError:
            valid = False
        if not valid:
            self.die(e.InvalidIntegerRevPropOnRev0 % (n, gt, repr(v)))

        return i

    def _init_rootmatcher(self):
        assert isinstance(self.__roots, tuple)
        assert len(self.__roots) == 2
        (c, d) = self.__roots
        assert isinstance(c, RepositoryRevisionConfig)
        assert isinstance(d, dict)
        if self.is_txn:
            assert c.readonly
            paths = d.keys()
        else:
            assert not c.readonly
            # It's important we only initialise our rootmatcher with paths
            # that weren't created in the same rev as us, otherwise, all the
            # root matching logic in the _process_*() methods will break.
            paths = (k for (k, v) in d.items() if v['created'] != self.rev)

        self.rootmatcher = SimpleRootMatcher(set(paths))
        if self.is_txn_for_first_commit:
            return
        c.roots = d
        self.roots = c.roots
        assert isinstance(self.roots, Roots)
        assert self.roots == d

    def __init_evn_dir_v1(self):
        self.__evn_dir = join_path(self.path, 'evn')
        self.__evn_db_dir = join_path(self.path, 'db')
        self.__evn_logs_dir = join_path(self.path, 'logs')
        self.__evn_locks_dir = join_path(self.path, 'locks')

        dirs = (
            self.__evn_dir,
            self.__evn_db_dir,
            self.__evn_logs_dir,
            self.__evn_locks_dir,
        )
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

        for d in dirs:
            assert os.path.isdir(d)

        # Initialize lock file names.
        f = join_path(self.__evn_locks_dir, str(self.base_rev))
        self.__base_rev_lockfile = f

        if self.is_rev:
            self.__rev_lockfile = join_path(d, str(self.rev))

    @property
    def lockdir(self):
        return self.__lockdir

    @property
    def base_rev_lockfile(self):
        return self.__base_rev_lockfile

    @property
    def rev_lockfile(self):
        return self.__rev_lockfile

    @property
    def last_rev(self):
        return self.__last_rev

    @property
    def base_rev_roots(self):
        return self.__base_rev_roots

    @property
    def log(self):
        return self.__logger

    @property
    def latest_rev(self):
        return svn.fs.youngest_rev(self.fs, self.pool)

    @property
    def is_latest(self):
        if self.is_rev:
            return self.rev == self.latest_rev
        else:
            return self.base_rev == self.latest_rev

    def _init_authz_conf(self):
        self.authz_admins = set()
        self.authz_overrides = set()
        self.authz_groups = dict()
        if self.is_txn and self.base_rev == 0:
            return
        try:
            ef = self.conf.get('repo', 'entitlements-filename')
        except configparser.NoOptionError:
            return

        if not svn.fs.is_file(self.root, ef, self.pool):
            return

        length = svn.fs.file_length(self.root, ef, self.pool)
        stream = svn.fs.file_contents(self.root, ef, self.pool)
        buf = StringIO.StringIO()
        buf.write(svn.core.svn_stream_read(stream, int(length)))
        buf.seek(0)
        c = ConfigParser()
        try:
            c.readfp(buf)

            g = dict(
                (k, frozenset(n for n in v.replace(' ', '').split(',')))
                    for (k, v) in c.items('groups')
            )

            a = set()
            for (name, perm) in c.items(ef):
                if 'w' in perm:
                    if name.startswith('@'):
                        a.update(g[name[1:]])
                    else:
                        a.add(name)

            self.authz_conf = c
            self.authz_admins = a
            self.authz_groups = g

            hook_override_grp = self.conf.get('hook-override', 'group-name')
            if hook_override_grp in self.authz_groups:
                self.authz_overrides = self.authz_groups[hook_override_grp]
        except:
            # log error, bad config file format or no [/unity_entitlements]
            # section
            pass

    @property
    def repo_admins(self):
        return self.authz_admins

    def is_repo_admin(self, user=None):
        return (user.lower() if user else self.user) in self.repo_admins

    def is_allowed_override(self, user=None):
        return (user.lower() if user else self.user) in self.authz_overrides

    @property
    def admins(self):
        if not isinstance(self.__admins, set):
            line = self.conf.get('main', 'admins').lower()
            self.__admins = set(a.strip() for a in line.split(','))
        return self.__admins

    def is_admin(self, user=None):
        return (user.lower() if user else self.user) in self.admins

    @property
    def revprop_conf(self):
        assert self.is_rev
        if not self.__revprop_conf_initialised:
            self.__revprop_conf = self.rconf(rev=self.rev)
            self.__revprop_conf_initialised = True
        return self.__revprop_conf

    @property
    def base_revprop_conf(self):
        if not self.__base_revprop_conf_initialised:
            self.__base_revprop_conf = self.rconf(base_rev=self.base_rev)
            self.__base_revprop_conf_initialised = True
        return self.__base_revprop_conf

    def rconf(self, **kwds):
        k = dict(fs=self.fs, conf=self.conf, **kwds)
        return RepositoryRevisionConfig(**k)

    def __remove_root(self, c, root_path=None, reason=None):
        if not root_path:
            root_path = c.path

        self.rootmatcher.remove_root_path(root_path)

        if self.is_txn:
            return

        if not reason:
            if c.is_replace:
                reason = 'replaced'
            elif c.is_rename:
                reason = 'renamed'
                details = ('renamed_to', (c.path, c.changeset.rev))
            else:
                assert c.is_remove
                reason = 'removed'

        r = self.roots[root_path]
        rc = self.rconf(rev=r.created)
        rc.roots[root_path][reason] = c.changeset.rev
        del self.roots[root_path]
        c.note(n.RootRemoved)

    def __get_root_details(self, path):
        rd = self.rootmatcher.get_root_details(path)
        if rd.is_unknown:
            rd.root_path = path
        return rd

    def __get_historical_rootmatcher(self, rev):
        if self.is_txn and rev == self.base_rev:
            return self.rootmatcher

        if rev not in self._rootmatchers:
            roots = self.rconf(rev=rev).roots
            self._rootmatchers[rev] = SimpleRootMatcher(set(roots.keys()))
        return self._rootmatchers[rev]

    def __get_copied_root_configdict(self, change):
        c = change
        cfr = c.copied_from_rev
        rc = self.rconf(rev=cfr)
        rev = rc.roots[c.copied_from_path]['created']
        rc = self.rconf(rev=rev)
        return rc.roots[c.copied_from_path]

    def __process_mergeinfo(self, change):
        c = change
        has_mergeinfo = False
        if c.is_changeset or not c.is_remove and c.has_propchanges:
            has_mergeinfo = c.has_propchange(SVN_PROP_MERGEINFO)

        if not has_mergeinfo:
            return

        pc = c.get_propchange(SVN_PROP_MERGEINFO)
        if c.is_changeset:
            if pc.change_type == PropertyChangeType.Create:
                c.error(e.MergeinfoAddedToRepositoryRoot)
            elif pc.change_type == PropertyChangeType.Modify:
                c.error(e.MergeinfoModifiedOnRepositoryRoot)
            else:
                assert pc.change_type == PropertyChangeType.Remove
                c.note(n.MergeinfoRemovedFromRepositoryRoot)
        elif c.is_subtree:
            if pc.change_type == PropertyChangeType.Create:
                c.error(e.SubtreeMergeinfoAdded)
            elif pc.change_type == PropertyChangeType.Modify:
                c.note(n.SubtreeMergeinfoModified)
            else:
                assert pc.change_type == PropertyChangeType.Remove
                c.note(n.SubtreeMergeinfoRemoved)
        elif c.is_root:
            if pc.change_type == PropertyChangeType.Remove:
                c.error(e.RootMergeinfoRemoved)
        else:
            raise UnexpectedCodePath
        if not pc.change_type == PropertyChangeType.Remove:
            ext = ExtendedPropertyChangeType
            if pc.extended_change_type == ext.PropertyCreatedWithoutValue:
                c.error(e.EmptyMergeinfoCreated)
            else:
                c.note(n.Merge)

    def __process_roots(self, cs):
        if cs.has_dirs:
            subdirs = [ d for d in cs.dirs ]
            for sd in subdirs:
                sd.root_details = self.__get_root_details(sd.path)

            if len(subdirs) > 1:
                self.__process_multiple_roots(cs)

    def __process_multiple_roots(self, c):
        dirs = [ d for d in c.dirs ]
        assert len(dirs) > 1
        root_path = dirs[0].root_details.root_path
        if all(sd.root_details.root_path == root_path for sd in dirs):
            # Although there are technically multiple roots in the commit,
            # they're all part of the same root path, which is fine.
            return
        elif all(sd.root_details.is_unknown for sd in dirs):
            # We don't care about multi-root commits to unknown roots.
            return
        elif any(sd.root_details.is_unknown for sd in dirs):
            assert any(not sd.root_details.is_unknown for sd in dirs)
            # See if we can find any svn:externals that would explain for
            # the multiple roots.
            known   = set([ d for d in dirs if not d.root_details.is_unknown])
            unknown = set([ d for d in dirs if d.root_details.is_unknown ])
            externals = list()
            for d in known:
                if not d.is_remove:
                    x = d.proplist.get(SVN_PROP_EXTERNALS)
                    if not x:
                        continue
                    for l in x.splitlines():
                        if not l or l.count(' ') < 1:
                            continue

                        idx = l.find(' ')
                        if idx == -1:
                            continue

                        # We'll support two types of svn:externals:
                        #   1. ^/<repo_path> <name>     (1.5 format)
                        #   2. <name> <full uri>        (1.4 format)
                        # Which means we won't be supporting:
                        #   - //<path> <-- relative to scheme
                        #   - ../      <-- relative to current dir
                        #   - /<path>  <-- relative to server root

                        first = l[:idx]
                        second = l[idx+1:].lower()

                        if len(first) < 1:
                            continue

                        if first[0] == '^':
                            externals.append(format_dir(first[2:]))
                            continue

                        prefixes = ('http', 'svn', 'file')
                        uri = second

                        if any(uri.startswith(p) for p in prefixes):
                            # Ensure the external entry points to this repo.
                            idx = uri.rfind(self.name.lower())
                            if idx == -1:
                                continue

                            base = format_dir(uri[idx+len(self.name):])
                            externals.append(base)

            if not externals:
                c.error(e.MultipleUnknownAndKnownRootsModified)
            else:
                for u in [ d for d in unknown ]:
                    unknown_path = u.path.lower()
                    for base_external_path in externals:
                        if unknown_path == base_external_path:
                            unknown.remove(d)

                if not unknown:
                    c.note(n.MultipleUnknownAndKnowRootsVerifiedByExternals)
                else:
                    c.error(e.MixedRootsNotClarifiedByExternals)

        else:
            assert all(not sd.root_details.is_unknown for sd in dirs)

            others = dirs[1:]
            rt = dirs[0].root_details.root_type
            rn = dirs[0].root_details.root_name

            before = set(c.errors)

            # Disable the mixed change-type check for now -- too many false
            # positives.  Our other checks are sufficient.
            #ct = dirs[0].change_type
            #if not all(ct == d.change_type for d in others):
            #    c.error(e.MixedChangeTypesInMultiRootCommit)

            if not all(rn == d.root_details.root_name for d in others):
                c.error(e.MixedRootNamesInMultiRootCommit)

            if not all(rt == d.root_details.root_type for d in others):
                c.error(e.MixedRootTypesInMultiRootCommit)

            if not bool(set(c.errors) - before):
                c.note(n.ValidMultirootCommit)

    def __process_changeset(self, cs):
        if not cs.is_change and cs.is_empty:
            cs.error(e.EmptyChangeSet)
            return

        self.__process_mergeinfo(cs)
        self.__process_roots(cs)

        if self.__valid_subdirs(cs):
            for child in cs:
                self.__process_change(child)

        return

    def _reload_last_rev(self):
        self.r0_revprop_conf._reload()
        self.__last_rev = self._load_evn_revprop_int('last_rev', 0)

    def __finalise_changeset(self, cs):
        if self.is_rev:
            dbg = self._dbg
            self._reload_last_rev()
            dbg('entered __finalise_changeset()')
            dbg('last_rev: %d, self.rev: %d, self.base_rev: %d' % (
                    self.last_rev,
                    self.rev,
                    self.base_rev,
                )
            )
            if self.last_rev < self.rev:
                dbg('updating last rev to %d' % self.rev)
                self.r0_revprop_conf.last_rev = self.rev

            c = self.revprop_conf
            # Use the _save() shortcut here, otherwise _reload() is going to
            # be called if we used direct attribute notation, i.e. c.notes =,
            # which is unnecessary this late in the game.
            if cs.notes:
                c._save('notes', cs.notes)
                dbg('notes: %s' % repr(cs.notes))
            if cs.errors:
                c._save('errors', cs.errors)
                dbg('errors: %s' % repr(cs.errors))
            if cs.warnings:
                c._save('warnings', cs.warnings)
                dbg('warnings: %s' % repr(cs.warnings))

    def _process_copy(self, c):
        # Types of copies (similar to types of renames):
        #   - Replacing an existing absolute root path: defer.
        #   - Copying a known absolute root path to another absolute path:
        #       Valid:
        #             trunk/            -> branches/foo
        #             trunk/            -> tags/2010.01.1
        #             branches/foo      -> branches/bar
        #             branches/foo      -> tags/2.0
        #       Invalid:
        #             tags/2010.01.1    ->  *
        #   - Prevent copying a path that has multiple roots under it:
        #       i.e. copying /src to /source when /src looks like this:
        #           /src/branches/xxx
        #           /src/tags/yyy
        #           /src/trunk
        #   - Copying an unknown path to an absolute valid root path name,
        #     i.e. /foo/junk -> /src/trunk.  This will treat 'trunk' as a
        #     new root, and it'll also convert /foo/junk to be a valid root
        #     by virtue of the fact it was copied to another path.
        #   - Copying an absolute root path
        #   - Copying an unknown path to another unknown path: valid.
        #   - Copying a subtree of a known root to an absolute valid root
        #     path: prevent if we're a txn, and raise a RuntimeError now
        #     if we're a rev.
        #   - Copying an absolute known root to a valid but not absolute
        #     root path name that doesn't reside under an existing known
        #     root, i.e.:
        #       trunk/ -> branches/bugzilla/8101
        #     Prevent this if we're a txn, allow if we're a rev.
        #   - Copying an absolute known root to a subtree of an existing
        #     known root, i.e.:
        #       UI/trunk/ -> /desktop/trunk/UI
        #     Prevent if we're a txn, allow if we're a rev (I guess).
        #   - Copying a subtree of a known root to a valid but not absolute
        #     root path name that doesn't reside under an existing known
        #     root, i.e.
        #       trunk/UI/ -> branches/bugzilla/8130
        #     Prevent if we're a txn, allow if we're a rev (I guess).
        assert c.is_copy

        if c.copied_from_path == '/':
            c.error(e.AbsoluteRootOfRepositoryCopied)
            if c.is_replace:
                self.__processed_replace(c)
            return

        rm = self.rootmatcher
        pm = self.pathmatcher

        if c.path in self.rootmatcher.roots:
            # The only way the path could already exist as a root is if this
            # action is a replace.  Super annoying, as we'll still have to
            # update all the root information if we're a revision to reflect
            # the replace.  (Well, that's what we'll *have* to do, at some
            # point down the track.  For now, if we're a rev, just bomb out.)
            assert c.is_dir
            if c.is_replace:
                assert c.is_root
                assert c.root_details.root_path == c.path
                m = e.KnownRootPathReplacedViaCopy
                c.error(m)
                err = '%s: %s' % (m, c.path)
                if self.is_rev:
                    raise RuntimeError(err)
                return
            else:
                m = e.InvariantViolatedCopyNewPathInRootsButNotReplace
                c.error(m)
                err = '%s: %s' % (m, c.path)
                if self.is_rev:
                    raise RuntimeError(err)
                return

        #  rd: root details via rootmatcher (if existing known root)
        # crm: historical rootmatcher from rev c.copied_from_rev
        # crd: root details of copied from path
        # nrd: root details of new path via pathmatcher
        rd  = c.root_details
        crm = self.__get_historical_rootmatcher(c.copied_from_rev)
        crd = crm.get_root_details(c.copied_from_path)
        nrd = pm.get_root_details(c.path)

        # See if our copy from path has any existing roots under it.
        if c.is_dir:
            paths = crm.find_roots_under_path(c.copied_from_path)
            if paths:
                m = e.MultipleRootsCopied
                c.error(m)
                return
            else:
                assert c.path[-1] == '/'
                if c.path.endswith('branches/'):
                    c.error(e.BranchesDirShouldBeCreatedManuallyNotCopied)
                    return
                elif c.path.endswith('tags/'):
                    c.error(e.TagsDirShouldBeCreatedManuallyNotCopied)
                    return

            assert not rm.find_roots_under_path(c.path)

        # -> tags/2.0.x, branches/foobar
        copied_to_valid_absolute_root_path = (
            rd.is_unknown and
            not nrd.is_unknown and
            nrd.root_path == c.path
        )

        # -> trunk/UI/foo/ (where 'trunk' is a known root)
        copied_to_known_root_subtree = (
            not rd.is_unknown and
            rd.root_path != c.path and
            c.path.startswith(rd.root_path)
        )

        # -> branches/bugzilla/8101 (where bugzilla is not a known root)
        copied_to_subtree_of_valid_root_path = (
            rd.is_unknown and
            not nrd.is_unknown and
            nrd.root_path != c.path and
            c.path.startswith(nrd.root_path)
        )

        # -> junk/foo/bar/
        copied_to_unknown = (
            rd.is_unknown and
            nrd.is_unknown
        )

        # trunk, branches/2.0.x ->
        copied_from_known_root = (
            not crd.is_unknown and
            crd.root_path == c.copied_from_path
        )

        # trunk/UI/foo ->
        copied_from_known_root_subtree = (
            not crd.is_unknown and
            crd.root_path != c.copied_from_path and
            c.copied_from_path.startswith(crd.root_path)
        )

        copied_from_unknown = crd.is_unknown

        # Make sure all of our mutually-exclusive invariants are correct.
        assert (
            (copied_from_known_root and (
                not copied_from_known_root_subtree and
                not copied_from_unknown
            )) or (copied_from_known_root_subtree and (
                not copied_from_known_root and
                not copied_from_unknown
            )) or (copied_from_unknown and (
                not copied_from_known_root_subtree and
                not copied_from_known_root
            ))
        )
        assert (
            (copied_to_valid_absolute_root_path and (
                not copied_to_subtree_of_valid_root_path and
                not copied_to_known_root_subtree and
                not copied_to_unknown
            )) or (copied_to_known_root_subtree and (
                not copied_to_subtree_of_valid_root_path and
                not copied_to_valid_absolute_root_path and
                not copied_to_unknown
            )) or (copied_to_subtree_of_valid_root_path and (
                not copied_to_valid_absolute_root_path and
                not copied_to_known_root_subtree and
                not copied_to_unknown
            )) or (copied_to_unknown and (
                not copied_to_subtree_of_valid_root_path and
                not copied_to_valid_absolute_root_path and
                not copied_to_known_root_subtree
            ))
        )

        new_root = True
        clean_check = True
        errors_before_copy_processing = set(c.errors)

        if copied_from_known_root:
            assert c.is_dir

            if crd.is_tag:
                c.error(e.TagCopied)

            if copied_to_valid_absolute_root_path:
                assert not c.is_replace

            elif copied_to_known_root_subtree:
                new_root = False
                c.error(e.CopyKnownRootToKnownRootSubtree)

            elif copied_to_subtree_of_valid_root_path:
                c.error(e.CopyKnownRootToIncorrectlyNamedRootPath)

            else:
                assert copied_to_unknown
                c.error(e.CopyKnownRootToUnknownPath)

        elif copied_from_known_root_subtree:

            if copied_to_valid_absolute_root_path:
                assert c.is_dir
                c.error(e.CopyKnownRootSubtreeToValidAbsoluteRootPath)

            elif copied_to_known_root_subtree:
                new_root = False
                clean_check = False
                if crd.root_path != rd.root_path:
                    if not c.is_merge:
                        # todo: promote this back to error status
                        c.note(e.PathCopiedFromOutsideRootDuringNonMerge)
                    else:
                        self.__process_copy_during_merge(c)

            elif copied_to_subtree_of_valid_root_path:
                c.error(e.CopyKnownRootSubtreeToIncorrectlyNamedRootPath)

            else:
                assert copied_to_unknown
                c.error(e.CopyKnownRootSubtreeToInvalidRootPath)

        else:
            assert copied_from_unknown
            new_root = False

            if copied_to_valid_absolute_root_path:
                c.error(e.NewRootCreatedByCopyingUnknownPath)

            elif copied_to_known_root_subtree:
                c.error(e.UnknownPathCopiedToKnownRootSubtree)

            elif copied_to_subtree_of_valid_root_path:
                c.error(e.UnknownPathCopiedToIncorrectlyNamedNewRootPath)

            else:
                assert copied_to_unknown
                clean_check = False

        if c.is_replace and (c.path not in self._replacements_processed):
            if copied_to_unknown:
                if not c.is_merge:
                    if c.is_dir:
                        c.error(e.UnknownDirReplacedViaCopyDuringNonMerge)
                    else:
                        # Permit file replacements to unknown paths if a merge
                        # isn't taking place.
                        assert c.is_file
                else:
                    # We don't currently verify merges to unknown paths; if
                    # the replacement can be explained by a merge, that's good
                    # enough for now.
                    pass
            else:
                if not c.is_merge:
                    if c.is_dir:
                        c.note(e.DirReplacedViaCopyDuringNonMerge)
                    else:
                        # Again, permit file replacements to known paths if a
                        # merge is taking place.
                        assert c.is_file
                else:
                    # Permit file/directory replacements during merges.
                    pass
            self.__processed_replace(c)

        if c.is_file:
            return
        else:
            assert c.is_dir
            if clean_check:
                if not c.is_empty:
                    if nrd.is_tag:
                        c.error(e.UncleanCopy)
                    elif not c.is_merge:
                        c.error(e.UncleanCopy)

            if new_root and copied_from_known_root:
                self.rootmatcher.add_root_path(c.path)

                if self.is_rev:
                    d = Dict()
                    d.created = c.changeset.rev
                    d.creation_method = 'copied'
                    d.copied_from = (c.copied_from_path, c.copied_from_rev)
                    d.copies = {}
                    if c.errors:
                        d.errors = c.errors

                    self.roots[c.path] = d
                    root = self.__get_copied_root_configdict(c)
                    root._add_copy(c.copied_from_rev, c.path, c.changeset.rev)

        return

    def __process_copy_during_merge(self, c):
        assert c.is_merge
        if c.is_replace:
            self.__processed_replace(c)
        else:
            # Very basic check that verifies the copied_from_path
            # ancestry derives from one of the paths in our svn:-
            # mergeinfo somewhere.
            mergeinfo_propchanges = list()
            c.collect_mergeinfo_propchanges(mergeinfo_propchanges)
            assert mergeinfo_propchanges
            #found = list()
            found = False
            fn = svn_mergeinfo_parse
            for pc in mergeinfo_propchanges:
                with Pool(self.pool) as p:
                    mergeinfo = fn(pc.new_value, p)
                    for merge_root in mergeinfo:
                        mr = merge_root
                        if c.copied_from_path.startswith(mr):
                            #found.append(mr)
                            found = True
                            break
            if not found:
                m = e.CopiedFromPathNotMatchedToPathsInMergeinfo
                c.error(m)

    def _process_create(self, c):
        # Types of creates:
        #   Valid:
        #       - Creating an unknown path.
        #       - Creating trunk.
        #       - Creating a subtree path under a known root.
        #   Invalid:
        #       - Creating an absolute root path name other than trunk,
        #         i.e. /branches/bugzilla, /tags/foo.
        #       - Creating a subtree path under a valid root path (but
        #         unknown root).
        #       - Creating anything under a tag.

        rd  = c.root_details
        if rd.is_absolute:
            if c.is_replace:
                self.__processed_replace(c)
            return

        nrd = self.pathmatcher.get_root_details(c.path)

        # Unknown path is tricky when the actual path involves legitimate
        # roots (like 'trunk' or 'branches/foo' etc) that weren't created
        # correctly and thus, weren't ever added to evn:roots.  In these
        # cases, root_details (rd) will rightly be unknown, but new root
        # details (nrd) will regex match the valid root part.  We still
        # class such paths as unknown.
        created_unknown_path = (
            rd.is_unknown and (
                nrd.is_unknown or (
                    not nrd.is_unknown and
                    nrd.root_path != c.path
                )
            )
        )

        created_trunk = (
            rd.is_unknown and
            nrd.is_trunk and
            nrd.root_path == c.path
        )

        created_absolute_valid_root_path = (
            rd.is_unknown and
            (nrd.is_branch or nrd.is_tag) and
            nrd.root_path == c.path
        )

        created_path_under_known_root = (
            not rd.is_unknown and
            rd.root_path != c.path and
            c.path.startswith(rd.root_path)
        )

        # Assert mutually-exclusive invariants.
        assert (
            (created_unknown_path and (
                not created_trunk and
                not created_path_under_known_root and
                not created_absolute_valid_root_path
            )) or (created_trunk and (
                not created_unknown_path and
                not created_path_under_known_root and
                not created_absolute_valid_root_path
            )) or (created_path_under_known_root and (
                not created_trunk and
                not created_unknown_path and
                not created_absolute_valid_root_path
            )) or (created_absolute_valid_root_path and (
                not created_trunk and
                not created_unknown_path and
                not created_path_under_known_root
            ))
        )

        if created_trunk:
            assert c.path.endswith('trunk/')
            assert not c.is_replace
            self.rootmatcher.add_root_path(c.path)
            c.root_details = self.rootmatcher.get_root_details(c.path)

        if created_unknown_path:
            pass

        elif created_trunk and self.is_txn:
            pass

        elif created_trunk and self.is_rev:
            d = Dict()
            d.created = c.changeset.rev
            d.creation_method = 'created'
            d.copies = {}
            if c.errors:
                d.errors = c.errors

            self.roots[c.path] = d

        elif created_path_under_known_root:
            if rd.is_tag:
                c.error(e.TagModified)

        else:
            assert created_absolute_valid_root_path
            assert c.is_dir
            if nrd.is_tag:
                c.error(e.TagDirectoryCreatedManually)
            else:
                assert nrd.is_branch
                c.error(e.BranchDirectoryCreatedManually)

        if c.is_replace:
            # Permit file/directory replacements during merges.  Only allow
            # file replacements during non-merges.
            if not c.is_merge:
                if c.is_dir:
                    c.error(e.DirectoryReplacedDuringNonMerge)
            self.__processed_replace(c)

    def __has_mismatched_previous_details(self, c):
        assert c.is_modify
        previous_path_mismatch = c.previous_path != c.path
        previous_rev_mismatch = (
            not previous_path_mismatch and
            c.previous_rev != c.changeset.base_rev
        )
        return previous_path_mismatch or previous_rev_mismatch

    def __processed_replace(self, c):
        assert c.path not in self._replacements_processed
        self._replacements_processed.add(c.path)

    def _process_modify(self, c):
        rd = c.root_details
        if rd.is_tag:
            # Tag modifications are banned, as usual.
            c.error(e.TagModified)
            if c.is_replace:
                # Don't bother tacking on replacement errors; tag modification
                # errors trump all.
                self.__processed_replace(c)
            return
        elif rd.is_absolute:
            # If our root details are absolute, we can only be a file.  If we
            # were a directory, root details would be unknown.  Also, let file
            # replacements to absolute files go through.
            assert c.is_file
            if c.is_replace:
                self.__processed_replace(c)
            return

        previous_path_mismatch = c.previous_path != c.path
        previous_rev_mismatch = (
            not previous_path_mismatch and
            c.previous_rev != c.changeset.base_rev
        )

        assert rd.is_trunk or rd.is_branch or rd.is_unknown
        if not previous_path_mismatch and not previous_rev_mismatch:
            if c.is_replace:
                if c.is_dir and not c.is_merge:
                    c.error(e.DirectoryReplacedDuringNonMerge)
                self.__processed_replace(c)
            return

        # If we get this far, we've either got a previous path mismatch or
        # a previous revision mismatch.  As we're a modify, the only time
        # this is considered legitimate is if there's a merge taking
        # place and our previous path starts with a path present in the
        # svn:mergeinfo prop, or there's a parent copy or rename change
        # and our previous path starts with said change's path.
        if c.is_merge:
            if c.is_replace:
                self.__processed_replace(c)

            if previous_rev_mismatch:
                # If we're only dealing with a revision mismatch, our
                # approach below for checking mergeinfo is too simple as
                # it only checks paths, not revision ranges.  So, for now,
                # just let previous revision mismatches go through if a
                # merge is taking place.
                return

            # Check the previous path against paths in mergeinfo.
            assert previous_path_mismatch
            mergeinfo_propchanges = list()
            c.collect_mergeinfo_propchanges(mergeinfo_propchanges)
            assert mergeinfo_propchanges
            #found = list()
            found = False
            for pc in mergeinfo_propchanges:
                with Pool(self.pool) as pool:
                    mergeinfo = svn_mergeinfo_parse(pc.new_value, pool)
                    for merge_root in mergeinfo:
                        if c.previous_path.startswith(merge_root):
                            #found.append(merge_root)
                            found = True
                            break
            if not found:
                c.error(e.PreviousPathNotMatchedToPathsInMergeinfo)
            return

        # There's no merge taking place, so the only way the previous
        # path (or rev) can be considered legitimate is if we can find
        # a parent change that's a copy or rename with matching info.
        parent = c.find_first_copy_or_rename_parent()
        if not parent:
            # If there is no parent copy or rename, an invariant has been
            # violated.  (The only time 'modify' changes have mismatched
            # previous path/rev is when there's a parent copy/rename.)
            if c.is_replace:
                self.__processed_replace(c)

            if previous_rev_mismatch:
                m = e.InvariantViolatedModifyContainsMismatchedPreviousRev
                c.error(m)
                return

            assert previous_path_mismatch
            m = e.InvariantViolatedModifyContainsMismatchedPreviousPath
            c.error(m)
            return

        assert parent
        assert parent.is_copy or parent.is_rename
        # Directory replacements outside of merges should not be permitted,
        # regardless of whether or not there's a parent copy/rename.
        if c.is_replace:
            if c.is_dir:
                c.error(e.DirectoryReplacedDuringNonMerge)
            self.__processed_replace(c)

        # Account for previous rev mismatch & previous path mismatch.
        # The logic here may seem a bit repetitive, but it's necessary to
        # catch all the different permutations (copy/rename/path/rev).
        if parent.is_copy:
            if previous_rev_mismatch:
                if parent.copied_from_rev != c.previous_rev:
                    c.error(e.PreviousRevDiffersFromParentCopiedFromRev)
            else:
                assert previous_path_mismatch
                if not c.previous_path.startswith(parent.copied_from_path):
                    c.error(e.PreviousPathDiffersFromParentCopiedFromPath)
                if parent.copied_from_rev != c.previous_rev:
                    c.error(e.PreviousRevDiffersFromParentCopiedFromRev)
        else:
            assert parent.is_rename
            if previous_rev_mismatch:
                if parent.renamed_from_rev != c.previous_rev:
                    c.error(e.PreviousRevDiffersFromParentRenamedFromRev)
            else:
                assert previous_path_mismatch
                if not c.previous_path.startswith(parent.renamed_from_path):
                    c.error(e.PreviousPathDiffersFromParentRenamedFromPath)
                if parent.renamed_from_rev != c.previous_rev:
                    c.error(e.PreviousRevDiffersFromParentRenamedFromRev)


    def _process_remove(self, c):

        if c.is_file:
            self.__process_remove_file(c)

        else:
            assert c.is_dir
            self.__process_remove_dir(c)

    def __process_remove_file(self, c):
        assert c.is_file
        if c.root_details.is_tag:
            c.error(e.FileRemovedFromTag)

    def __process_remove_dir(self, c):
        # Types of removals:
        #   Valid:
        #       - Removing an unknown path.
        #       - Removing a subtree from a non-tag known root.
        #   Warn:
        #       - Removing an absolute known root.
        #   Invalid:
        #       - Removing a tag or any tag contents.
        #   Assert:
        #       - Removing a path that affects multiple roots.
        assert c.is_dir

        rd = c.root_details

        paths = self.rootmatcher.find_roots_under_path(c.path)
        if paths:
            c.error(e.MultipleRootsAffectedByRemove)
            if self.is_rev:
                for path in paths:
                    self.__remove_root(c, root_path=path)

        rd = c.root_details

        removed_unknown_path = rd.is_unknown

        removed_tag = (
            rd.is_tag and
            rd.root_path == c.path
        )

        removed_tag_subtree = (
            rd.is_tag and
            rd.root_path != c.path and
            c.path.startswith(rd.root_path)
        )

        removed_subtree_from_non_tag_known_root = (
            not rd.is_unknown and
            not rd.is_tag and
            rd.root_path != c.path and
            c.path.startswith(rd.root_path)
        )

        removed_absolute_non_tag_known_root = (
            not rd.is_unknown and
            not rd.is_tag and
            rd.root_path == c.path
        )

        remove_root = False

        if removed_unknown_path:
            pass

        elif removed_tag:
            remove_root = True
            c.note(e.TagRemoved)

        elif removed_tag_subtree:
            c.error(e.TagSubtreePathRemoved)

        elif removed_subtree_from_non_tag_known_root:
            pass

        else:
            assert removed_absolute_non_tag_known_root
            remove_root = True
            c.note(w.KnownRootRemoved)

        if remove_root:
           self.__remove_root(c)

    def __valid_subdirs(self, c):
        # Check to see if they've checked in a repository.
        paths = [ d.path for d in c.dirs ]
        dirnames = set(os.path.basename(d[:-1]) for d in paths)
        endings = set(('conf', 'db', 'hooks', 'locks'))
        # 3 or more (out of 4) seems like a good enough number.
        if len(dirnames.intersection(endings)) >= 3:
            c.error(e.SubversionRepositoryCheckedIn)
            return False
        else:
            return True

    def __process_change_invariants_and_general_correctness(self, c):
        # Test some fundamental invariants that should always hold true, but
        # always seem to get broken in the Real World.

        if c.is_file:
            if c.is_modify:
                if not c.has_text_changed and not c.has_propchanges:
                    if not c.merge_root:
                        parent = c.find_first_copy_or_rename_parent()
                        if not parent:
                            c.error(e.FileUnchangedAndNoParentCopyOrRename)
                        else:
                            c.note(n.FileUnchangedButParentCopyOrRenameBug)
                    else:
                        c.note(n.UnchangedFileDuringMerge)
        else:
            assert c.is_dir
            if c.is_modify:
                if c.is_empty and not c.has_propchanges:
                    if not c.merge_root:
                        parent = c.find_first_copy_or_rename_parent()
                        if not parent:
                            c.error(e.DirUnchangedAndNoParentCopyOrRename)
                        else:
                            c.note(n.DirUnchangedButParentCopyOrRenameBug)
                    else:
                        c.note(n.UnchangedDirDuringMerge)

        # Make a note of any weird property changes where the value doesn't
        # actually change -- not sure what to make of this yet.
        if not c.is_remove:
            for (name, pc) in c.propchanges.items():
                if pc.extended_change_type == \
                   ExtendedPropertyChangeType.\
                    PropertyChangedButOldAndNewValuesAreSame:
                        m = e.PropertyChangedButOldAndNewValuesAreSame
                        c.note(m % (name, repr(pc.new_value)))

    def __process_change(self, c):
        if c.parent.is_changeset and c.root_details.is_unknown:
            assert c.root_details.root_path == c.path

        self.__process_change_invariants_and_general_correctness(c)
        self.__process_mergeinfo(c)
        if c.is_change:
            fn = '_process_%s' % ChangeType[c.change_type].lower()
            getattr(self, fn)(c)

        if c.is_replace:
            assert c.path in self._replacements_processed

        if c.is_dir:
            if c.has_dirs:
                if not self.__valid_subdirs(c):
                    return

            for child in c:
                self.__process_change(child)

        return

    def _process_rename(self, c):
        # Types of renames:
        #   - Rename of an absolute root path name to another absolute root
        #     path name...:
        #       - branch -> branch: valid if the base dir is the same, i.e.
        #         /src/branches/product-2.0.x -> /src/branches/product-2.1.x
        #       - branch -> trunk: invalid
        #       - branch -> tag: invalid
        #       - trunk -> branch: invalid
        #       - trunk -> trunk: invalid
        #       - tag -> trunk: invalid
        #       - tag -> branch: invalid
        #       - tag -> tag: invalid
        #   - Renaming an absolute known root to an unknown path.
        #   - Renaming a subtree of a known root to an unknown path.
        #   - Renaming a subtree of an absolute known root to a new valid
        #     absolute root path... prevent if txn, allow if rev.
        #   - Renaming a subtree of a known root to another location within
        #     the same root.
        #   - Renaming a subtree of a known root to another location within
        #     a different known root.
        #   - Renaming a path that has multiple roots under it, i.e.:
        #       - Renaming /src to /source:
        #           /src/branches/xxx
        #           /src/tags/xxx
        #           /src/trunk/xxx
        #   - Renaming an unknown path to an absolute valid root path name:
        #       - /contrib/junk/component -> /junk/trunk: valid
        #   - Renaming an unknown path to another unknown path

        assert c.is_rename
        assert not c.path in self.rootmatcher.roots
        assert c.renamed_from_rev == c.changeset.base_rev
        assert c.renamed_from_rev == self.base_rev

        # Originally, there was an assumption that a rename couldn't be a
        # replace.  So, about here, we had an 'assert not c.is_replace'.  Fast
        # forward a few months after deployment in the wild and yes, it turns
        # out, we certainly can have renames that are also replacements.  How
        # should we deal with them?  Should we flag them as an error?  I would
        # personally like to eradicate all replace actions, but alas, the mod-
        # _dav bug that causes prolific replacements tends to make it impossi-
        # ble to discern the difference between a replace that we should be
        # blocking because the user is doing something wrong, versus a replace
        # that's simply an artefact of committing through http://.  So, for
        # now, let's do... *drum roll* nothing.
        if c.is_replace:
            self.__processed_replace(c)

        rm = self.rootmatcher
        pm = self.pathmatcher

        #  rd: root details of path (if existing known root)
        # rrd: root details of renamed path
        # nrd: root details of new path via pathmatcher
        rd  = c.root_details
        rf  = (c.renamed_from_path, c.renamed_from_rev)
        rp  = (c.renamed_from_path, c.path)
        # Note: unlike _process_copy(), which has to deal with paths being
        # copied from any revision, we don't need to load a historical root-
        # matcher object below, because renamed_from_rev will always equal
        # our (changeset|self).base_rev (see assertions a few lines up),
        # which is what self.rootmatcher will be tied to.
        rrd = rm.get_root_details(c.renamed_from_path)
        nrd = pm.get_root_details(c.path)

        if c.is_dir:

            # There shouldn't ever be any existing roots under the new path
            # name.  (XXX: could weird directory replacements break this?)
            assert not rm.find_roots_under_path(c.path)

            old_paths = rm.find_roots_under_path(c.renamed_from_path)
            if old_paths:
                assert rrd.is_unknown

                # Multi-root renames are permitted IFF the rename is clean.

                # In the context of a txn, the user must explicitly confirm
                # the multi-root rename in the log message.  In the context
                # of a revision, if the confirmation is in the log message,
                # add a note indicating the multi-root rename; if not, mark
                # it as an error.

                # We don't currently permit unclean multi-root renames 'cause
                # it would increase complexity immensely; every rename would
                # have to be analysed to verify all the original roots are
                # being brought over, any new roots that have been created,
                # any existing roots that have been modified (i.e. cheeky tag
                # modifications during the rename), any existing roots that
                # have subsequently been renamed and deleted, etc.  Absolute
                # nightmare.

                if not c.is_empty:
                    m = e.UncleanRenameAffectsMultipleRoots
                    if self.is_txn:
                        c.error(m)
                        return
                    else:
                        assert self.is_rev
                        raise RuntimeError(m)

                m = e.RenameAffectsMultipleRoots
                confirmation = EVN_ERROR_CONFIRMATIONS[m]

                new_paths = [ p.replace(*rp) for p in old_paths ]
                # Temporary preventative measures for preventing dodgy
                # commits from corrupting evn:roots.
                for (old_path, new_path) in zip(old_paths, new_paths):
                    # Until the root refactoring work is complete, call
                    # SimpleRootMatcher's remove_root_path and add_root-
                    # path before persisting changes in the revprop; both
                    # of those methods will raise an AssertionError if
                    # there is anything dodgy going on with evn:roots.
                    rm.remove_root_path(old_path)
                    rm.add_root_path(new_path)

                if self.is_txn:
                    if confirmation not in self.log_msg:
                        c.error(m)
                    else:
                        # No need to 'c.note(m)' as with revision processing
                        # below if we're a txn.
                        pass
                    return
                else:
                    assert self.is_rev
                    if confirmation not in self.log_msg:
                        c.error(m)
                    else:
                        c.note(m)

                    for (old_path, new_path) in zip(old_paths, new_paths):
                        # Find the relevant evn:roots entry for when the old
                        # path was created, then record the fact it's just
                        # been renamed.
                        rfrev = c.renamed_from_rev
                        rc = self.rconf(rev=rfrev)
                        crev = rc.roots[old_path]['created']
                        rc = self.rconf(rev=crev)
                        root = rc.roots[old_path]
                        root.removed = c.changeset.rev
                        root.removal_method = 'renamed_indirectly'
                        root.renamed_indirectly = rp
                        root.renamed = (new_path, c.changeset.rev)

                        # Delete the old root from our current roots.
                        del self.roots[old_path]

                        # ....and add the new root.
                        d = Dict()
                        d.created = c.changeset.rev
                        d.creation_method = 'renamed_indirectly'
                        d.renamed_indirectly_from = rp
                        d.renamed_from = (old_path, rfrev)
                        d.copies = {}
                        if c.errors:
                            d.errors = c.errors

                        self.roots[new_path] = d

                    return

        # -> tags/2.0.x/, branches/foo/, trunk/
        renamed_to_valid_absolute_root_path = (
            rd.is_unknown and
            not nrd.is_unknown and
            nrd.root_path == c.path
        )

        # -> trunk/UI/foo/ (where 'trunk' is a known root)
        renamed_to_known_root_subtree = (
            not rd.is_unknown and
            rd.root_path != c.path and
            c.path.startswith(rd.root_path)
        )

        # -> branches/bugzilla/8101 (where bugzilla is not a known root)
        renamed_to_subtree_of_valid_root_path = (
            rd.is_unknown and
            not nrd.is_unknown and
            nrd.root_path != c.path and
            c.path.startswith(nrd.root_path)
        )

        # -> junk/foo/bar/
        renamed_to_unknown = (
            rd.is_unknown and
            nrd.is_unknown
        )

        # trunk, branches/2.0.x ->
        renamed_from_known_root = (
            not rrd.is_unknown and
            rrd.root_path == c.renamed_from_path
        )

        # trunk/UI/foo ->
        renamed_from_known_root_subtree = (
            not rrd.is_unknown and
            rrd.root_path != c.renamed_from_path and
            c.renamed_from_path.startswith(rrd.root_path)
        )

        renamed_from_unknown = rrd.is_unknown

        # Make sure all of our mutually-exclusive invariants are correct.
        assert (
            (renamed_from_known_root and (
                not renamed_from_known_root_subtree and
                not renamed_from_unknown
            )) or (renamed_from_known_root_subtree and (
                not renamed_from_known_root and
                not renamed_from_unknown
            )) or (renamed_from_unknown and (
                not renamed_from_known_root_subtree and
                not renamed_from_known_root
            ))
        )
        assert (
            (renamed_to_valid_absolute_root_path and (
                not renamed_to_subtree_of_valid_root_path and
                not renamed_to_known_root_subtree and
                not renamed_to_unknown
            )) or (renamed_to_known_root_subtree and (
                not renamed_to_subtree_of_valid_root_path and
                not renamed_to_valid_absolute_root_path and
                not renamed_to_unknown
            )) or (renamed_to_subtree_of_valid_root_path and (
                not renamed_to_valid_absolute_root_path and
                not renamed_to_known_root_subtree and
                not renamed_to_unknown
            )) or (renamed_to_unknown and (
                not renamed_to_subtree_of_valid_root_path and
                not renamed_to_valid_absolute_root_path and
                not renamed_to_known_root_subtree
            ))
        )

        clean_check = True
        new_root = None

        if renamed_from_known_root:
            assert c.is_dir

            if rrd.is_tag:
                # Always flag attempts to rename tags, regardless of what
                # they're being renamed to.
                c.error(e.TagRenamed)

            elif renamed_to_valid_absolute_root_path:
                new_root = True
                if rrd.is_branch:
                    if nrd.is_branch:
                        dn = os.path.dirname
                        rrbd = dn(c.renamed_from_path[:-1])
                        nrbd = dn(c.path[:-1])
                        if rrbd == nrbd:
                            c.note(n.BranchRenamed)
                        else:
                            c.error(e.BranchRenamedOutsideRootBaseDir)
                    elif nrd.is_trunk:
                        c.error(e.BranchRenamedToTrunk)
                    else:
                        assert nrd.is_tag
                        c.error(e.BranchRenamedToTag)
                else:
                    assert rrd.is_trunk
                    if nrd.is_trunk:
                        # Permit trunk relocations ('cause I can't think of
                        # any reason not to, at the moment).
                        c.note(n.TrunkRelocated)
                    elif nrd.is_branch:
                        c.error(e.TrunkRenamedToBranch)
                    else:
                        assert nrd.is_tag
                        c.error(e.TrunkRenamedToTag)

            elif renamed_to_known_root_subtree:
                new_root = False
                c.error(e.RenamedKnownRootToKnownRootSubtree)

            elif renamed_to_subtree_of_valid_root_path:
                new_root = True
                c.error(e.RenamedKnownRootToIncorrectlyNamedRootPath)

            else:
                assert renamed_to_unknown
                new_root = True
                c.error(e.RenamedKnownRootToUnknownPath)

        elif renamed_from_known_root_subtree:
            new_root = False

            if renamed_to_valid_absolute_root_path:
                assert c.is_dir
                c.error(e.RenamedKnownRootSubtreeToValidRootPath)
                if nrd.is_trunk:
                    new_root = True

            elif renamed_to_known_root_subtree:
                clean_check = False

                if rrd.root_path != rd.root_path:
                    c.error(e.RenameRelocatedPathOutsideKnownRoot)

            elif renamed_to_subtree_of_valid_root_path:
                c.error(e.RenamedKnownRootSubtreeToIncorrectlyNamedRootPath)

            else:
                assert renamed_to_unknown
                c.error(e.RenamedKnownRootSubtreeToUnknownPath)

        else:
            assert renamed_from_unknown
            new_root = False

            if renamed_to_valid_absolute_root_path:
                c.error(e.NewRootCreatedByRenamingUnknownPath)
                if nrd.is_trunk:
                    new_root = True

            elif renamed_to_known_root_subtree:
                c.error(e.NewRootCreatedByRenamingUnknownPath)

            elif renamed_to_subtree_of_valid_root_path:
                c.error(e.UnknownPathRenamedToIncorrectlyNamedNewRootPath)

            else:
                assert renamed_to_unknown
                clean_check = False

        if c.is_file:
            return

        if new_root:
            assert renamed_from_known_root or nrd.is_trunk

        if clean_check:
            if not c.is_empty:
                c.error(e.UncleanRename)

        if self.is_rev:
            if renamed_from_known_root:
                # Need to mark the old root as removed and delete it from
                # our current roots.
                rev = c.renamed_from_rev
                rc = self.rconf(rev=rev)
                crev = rc.roots[c.renamed_from_path]['created']
                rc = self.rconf(rev=crev)
                root = rc.roots[c.renamed_from_path]
                root.removed = c.changeset.rev
                root.removal_method = 'renamed'
                root.renamed = (c.path, c.changeset.rev)

                self.rootmatcher.remove_root_path(c.renamed_from_path)
                del self.roots[c.renamed_from_path]

            if new_root:
                d = Dict()
                d.created = c.changeset.rev
                d.creation_method = 'renamed'
                d.renamed_from = (c.renamed_from_path, c.renamed_from_rev)
                d.copies = {}
                if c.errors:
                    d.errors = c.errors

                self.roots[c.path] = d

        else:
            assert self.is_txn
            if renamed_from_known_root:
                self.rootmatcher.remove_root_path(c.renamed_from_path)

            if new_root:
                self.rootmatcher.add_root_path(c.path)

    def __process_copy_or_rename(self, c):
        # I've gone back and forward a few times on whether or not to deal
        # with copy and renames in separate methods or one combined method.
        # The huge chunk of logic that handles all the 'from path' and 'to
        # path' (src and dst) permutations is almost identical for copies
        # and renames, so I've gone with this combined method, for now.
        # Side bar: this method is pretty heavy on 2-3 letter alias vars
        # for commonly accessed objects.
        assert c.is_copy or c.is_rename

        rm = self.rootmatcher
        pm = self.pathmatcher
        rd = c.root_details

        if c.is_copy:
            src_path = sp = c.copied_from_path
            src_rev  = sr = c.copied_from_rev
            # We need to load the historical root matcher for the rev that's
            # being copied in order to get sensible root details.
            hrm = self.__get_historical_rootmatcher(sr)
            src_root_details = srd = hrm.get_root_details(sp)
            src_roots = hrm.find_roots_under_path(sp)
        else:
            assert c.is_rename
            assert c.renamed_from_rev == c.changeset.base_rev
            assert c.renamed_from_rev == self.base_rev
            src_path = sp = c.renamed_from_path
            src_rev  = sr = c.renamed_from_rev
            # Unlike the copy logic above, which has to deal with paths being
            # copied from any revision, we don't need to load a historical
            # root matcher object below, because renamed_from_rev will always
            # equal our (changeset|self).base_rev (see assertions a few lines
            # up), which is what self.rootmatcher will be tied to.
            src_root_details = srd = rm.get_root_details(sp)
            src_roots = rm.find_roots_under_path(sp)

        dst_path  = dp = c.path
        dst_roots = rm.find_roots_under_path(dp)
        dst_root_details = drd = pm.get_root_details(dp)

        src_has_roots_under_it = bool(src_roots)
        dst_has_roots_under_it = bool(dst_roots)

        # src begin
        src = MutexDecayDict()
        # junk/foo/bar/ ->
        src.unknown = (
            srd.is_unknown and
            not src_has_roots_under_it
        )

        # trunk/, branches/2.0.x/ ->
        src.known_root = (
            not srd.is_unknown and
            srd.root_path == src_path
        )

        # trunk/UI/foo/ -> (where 'trunk' is a known root)
        src.known_root_subtree = (
            not srd.is_unknown and
            srd.root_path != src_path and
            src_path.startswith(srd.root_path)
        )

        # /xyz/foo/ ->, where the following roots exist:
        #       /xyz/foo/trunk
        #       /xyz/foo/branches/1.0.x
        src.root_ancestor = (
            srd.is_unknown and
            bool(src_has_roots_under_it)
        )
        # src end

        # dst begin
        dst = MutexDecayDict()
        # -> junk/foo/bar/
        dst.unknown = (
            rd.is_unknown and
            drd.is_unknown and
            not dst_roots
        )

        # -> trunk/ (where 'trunk/' is a known root)
        dst.known_root = (
            c.is_replace and
            not rd.is_unknown and
            rd.root_path == dst_path
        )

        # -> trunk/UI/foo/ (where 'trunk/' is a known root)
        dst.known_root_subtree = (
            not rd.is_unknown and
            rd.root_path != dst_path and
            dst_path.startswith(rd.root_path)
        )

        # -> tags/2.0.x/, branches/foo/, trunk/
        dst.valid_root = (
            rd.is_unknown and
            not drd.is_unknown and
            drd.root_path == dst_path
        )

        # -> branches/bugs/8101 (where 'branches/bugs/' is not a known root)
        dst.valid_root_subtree = (
            rd.is_unknown and
            not drd.is_unknown and
            drd.root_path != dst_path and
            dst_path.startswith(drd.root_path)
        )

        # -> /xyz/foo/, where the following roots already exist:
        #       /xyz/foo/trunk
        #       /xyz/foo/branches/1.0.x
        dst.root_ancestor = (
            c.is_replace and
            rd.is_unknown and
            dst_has_roots_under_it
        )

        # dst end

        clean_check   = True

        new_root     = False
        remove_root  = False
        create_root  = False
        replace_root = False

        en = 'Copied' if c.is_copy else 'Renamed'

        with nested(src, dst) as (src, dst):

            if src.unknown:

                if dst.unknown:
                    clean_check = False

                elif dst.known_root:
                    assert c.is_dir
                    rm.remove_root_path(dst_root)
                    create_root = True
                    replace_root = True
                    CopyOrRename.UnknownToKnownRoot(c)

                elif dst.known_root_subtree:
                    CopyOrRename.UnknownToKnownRootSubtree(c)

                elif dst.valid_root:
                    CopyOrRename.UnknownToValidRoot(c)
                    if drd.is_trunk:
                        create_root = True

                elif dst.valid_root_subtree:
                    CopyOrRename.UnknownToValidRootSubtree(c)

                elif dst.root_ancestor:
                    assert c.is_dir
                    replace_roots = True
                    CopyOrRename.UnknownToRootAncestor(c)

                else:
                    raise UnexpectedCodePath

            elif src.known_root:
                assert c.is_dir
                new_root = True

                if srd.is_tag:
                    # Always flag attempts to copy or rename tags.
                    c.error(getattr(e, 'Tag' + en))

                if dst.unknown:
                    CopyOrRename.KnownRootToUnknown(c)

                elif dst.known_root:
                    CopyOrRename.KnownRootToKnownRoot(c)

                elif dst.known_root_subtree:
                    new_root = False
                    remove_root = True
                    CopyOrRename.KnownRootToKnownRootSubtree(c)

                elif dst.valid_root:
                    if c.is_rename:
                        paths = (sp, dp)
                        root_details = (srd, drd)
                        args = (c, paths, root_details)
                        self.__known_root_renamed(*args)

                elif dst.valid_root_subtree:
                    CopyOrRename.KnownRootToValidRootSubtree(c)

                elif dst.root_ancestor:
                    CopyOrRename.KnownRootToRootAncestor(c)

                else:
                    raise UnexpectedCodePath

            elif src.known_root_subtree:

                if srd.is_tag:
                    # Always flag attempts to copy or rename tag subtrees.
                    c.error(getattr(e, 'TagSubtree' + en))

                if dst.unknown:
                    CopyOrRename.KnownRootSubtreeToUnknown(c)

                elif dst.known_root:
                    CopyOrRename.KnownRootSubtreeToKnownRoot(c)

                elif dst.known_root_subtree:
                    if srd.root_path != drd.root_path:
                        CopyOrRename.\
                            KnownRootSubtreeToUnrelatedKnownRootSubtree(c)
                    else:
                        clean_check = False

                elif dst.root_ancestor:
                    CopyOrRename.KnownRootSubtreeToRootAncestor(c)

                if dst.valid_root:
                    CopyOrRename.KnownRootToValidRoot(c)
                    if drd.is_trunk:
                        create_root = True

                elif dst.valid_root_subtree:
                    CopyOrRename.KnownRootSubtreeToValidRootSubtree(c)

                else:
                    raise UnexpectedCodePath

            elif src.root_ancestor:
                rename_root = True

                if dst.unknown:
                    CopyOrRename.RootAncestorToUnknown(c)

                elif dst.known_root:
                    replace_root = True
                    CopyOrRename.RootAncestorReplacesKnownRoot(c)

                elif dst.known_root_subtree:
                    rename_root = False
                    remove_root = True
                    CopyOrRename.RootAncestorToKnownRootSubtree(c)

                elif dst.root_ancestor:
                    replace_root = True
                    CopyOrRename.RootAncestorReplacesRootAncestor(c)

                elif dst.valid_root:
                    # This has to be one of the most retarded things to do.
                    #
                    # Given:
                    #   /foo/branches/1.0.x
                    #   /foo/branches/2.0.x
                    # Someone has done:
                    #   svn mv ^/foo ^/trunk, or
                    #   svn mv ^/foo ^/src/branches/2.0.x
                    #
                    # The precedent set by other parts of the code dealing
                    # with dst.valid_root is to only create a new root if our
                    # new path name is 'trunk'.  Another precedent we follow
                    # is that the destination path's semantic value trumps the
                    # source path's semantic value.  In this case, the source
                    # path's semantic value (it is a container for multiple
                    # roots) definitely outweighs the destination path's value
                    # (it's a valid root path, but not a known root), so we'll
                    # just rename all the roots.  Yes, even if that means we
                    # ended up with the following known roots:
                    #   /trunk/branches/1.0.x/
                    #   /trunk/branches/2.0.x/
                    #   /trunk/trunk/
                    # (Retarded eh?)
                    CopyOrRename.RootAncestorToValidRoot(c)

                elif dst.valid_root_subtree:
                    # Similar level of retardation as above; let's just let
                    # the multi-root rename go through.
                    CopyOrRename.RootAncestorToValidRootSubtree(c)

                else:
                    raise UnexpectedCodePath

            else:
                raise UnexpectedCodePath

        if c.is_file:
            assert none(
                new_root,
                remove_root,
                rename_root,
                create_root,
                replace_root,
            )
            return

        src._unlock()
        dst._unlock()


        if replace_root:
            pass



        if remove_root:
            self.rootmatcher.remove_root_path(dst_root)
        #if dst.known_root:
        #    assert c.is_dir
        #    # xxx todo: replace root

        #elif dst.valid_root:
        #    assert c.is_dir

        #elif dst.root_ancestor:
        #    assert c.is_dir
        #    # xxx todo: replace roots


        if clean_check:
            if not c.is_empty:
                c.error(e.UncleanRename)


        if new_root and copied_from_known_root:
            self.rootmatcher.add_root_path(c.path)

            if self.is_rev:
                d = Dict()
                d.created = c.changeset.rev
                d.creation_method = 'copied'
                d.copied_from = (c.copied_from_path, c.copied_from_rev)
                d.copies = {}
                if c.errors:
                    d.errors = c.errors

                root = self.__get_copied_root_configdict(c)

                k = Dict()
                k.roots = self.roots
                k.change = c
                k.details = d
                k.src_path = src_path
                k.dst_path = dst_path
                if replace_root:
                    pass

                self.__enqueue_root_action()

                self.roots[c.path] = d
                root = self.__get_copied_root_configdict(c)
                root._add_copy(c.copied_from_rev, c.path, c.changeset.rev)

        if self.is_rev:
            if renamed_from_known_root:
                # Need to mark the old root as removed and delete it from
                # our current roots.
                rev = c.renamed_from_rev
                rc = RepositoryRevisionConfig(fs=self.fs, rev=rev)
                crev = rc.roots[c.renamed_from_path]['created']
                rc = RepositoryRevisionConfig(fs=self.fs, rev=crev)
                root = rc.roots[c.renamed_from_path]
                root.removed = c.changeset.rev
                root.removal_method = 'renamed'
                root.renamed = (c.path, c.changeset.rev)

                self.rootmatcher.remove_root_path(c.renamed_from_path)
                del self.roots[c.renamed_from_path]

            if new_root:
                d = Dict()
                d.created = c.changeset.rev
                d.creation_method = 'renamed'
                d.renamed_from = (c.renamed_from_path, c.renamed_from_rev)
                d.copies = {}
                if c.errors:
                    d.errors = c.errors

                self.roots[c.path] = d

        else:
            assert self.is_txn
            if renamed_from_known_root:
                self.rootmatcher.remove_root_path(c.renamed_from_path)

            if new_root:
                self.rootmatcher.add_root_path(c.path)
    def __known_root_renamed(self, change, paths, root_details):
        c = change
        (sp, dp)   = paths
        (srd, drd) = root_details

        if srd.is_branch:
            if drd.is_branch:
                dn = os.path.dirname
                # (s|d)rbd: (src|dst) root base dir
                srbd = dn(sp[:-1])
                drbd = dn(dp[:-1])
                if srbd == drbd:
                    c.note(n.BranchRenamed)
                else:
                    c.error(e.BranchRenamedOutsideRootBaseDir)
            elif drd.is_trunk:
                c.error(e.BranchRenamedToTrunk)
            else:
                assert drd.is_tag
                c.error(e.BranchRenamedToTag)
        elif srd.is_tag:
            # No need to do anything here as we would have already
            # flagged the tag rename error above.
            pass
        else:
            assert srd.is_trunk
            if drd.is_trunk:
                # Permit trunk relocations ('cause I can't think of
                # any reason not to, at the moment).
                c.note(n.TrunkRelocated)
            elif drd.is_branch:
                c.error(e.TrunkRenamedToBranch)
            else:
                assert drd.is_tag
                c.error(e.TrunkRenamedToTag)


    def _get_revlock_filename(self, r):
        pass

    @property
    def revlock_filename(self):
        if not self.__revlock_filename_initialised:
            pass

    @property
    def base_revlock_filename(self):
        if not self.__base_revlock_filename_initialised:
            pass

    @property
    def _changeset_kwds(self):
        k = Dict()
        k.fs   = self.fs
        k.root = self.root
        k.conf = self.conf
        k.pool = self.pool
        k.estream = self.estream
        k.ostream = self.ostream
        k.options = self.options
        return k

    @property
    def _raw_changeset(self):
        if self.is_rev and self.rev == 0:
            self.die(e.ChangeSetOnlyApplicableForRev1AndHigher)

        return ChangeSet(self.fs, self.root)

    @property
    def changeset(self):
        if self.is_rev and self.rev == 0:
            self.die(e.ChangeSetOnlyApplicableForRev1AndHigher)

        if not self.__changeset_initialised:
            self._init_rootmatcher()
            cs = ChangeSet(self.path, self.rev_or_txn, self.options)
            cs.load()
            self.__process_changeset(cs)
            self.__finalise_changeset(cs)
            self.__changeset = cs
            self.__changeset_initialised = True
        return self.__changeset

    def _pre_check_invariants(self):
        pass

    def _check_invariants(self):
        pass
        #assert not os.path.exists(self._managed_file)

    def propget(self, name, path=''):
        return svn.fs.node_prop(self.root, path, name, self.pool)

    def hasprop(self, name, path=''):
        return name in self.proplist(path=path)

    def proplist(self, path=''):
        return svn.fs.node_proplist(self.root, path, self.pool)

    def ls(self, path='', names_only=True, kinds=None):
        """
        @path: defaults to ''
        @kind: list of svn_node_kind_t types, defaults to all
        """
        if not kinds:
            kinds = svn_node_types
        args = (self.root, path, self.pool)
        return [
            (n if names_only else (n, de))
                for (n, de) in svn.fs.dir_entries(*args).items()
                    if de.kind in kinds
        ]

    def ls_dirs(self, path='', names_only=True):
        return self.ls(path, names_only=names_only, kinds=(svn_node_dir,))

    def ls_files(self, path='', names_only=True):
        return self.ls(path, names_only=names_only, kinds=(svn_node_file,))

    def propget(self, name, path=''):
        return svn.fs.node_prop(self.root, path, name, self.pool)

    def hasprop(self, name, path=''):
        return name in self.proplist(path=path)

    def proplist(self, path=''):
        return svn.fs.node_proplist(self.root, path, self.pool)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
