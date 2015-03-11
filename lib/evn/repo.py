#===============================================================================
# Imports
#===============================================================================
import os
import sys
import time
import inspect
import getpass
import logging
import datetime
import itertools
import contextlib
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
    svn_rangelist_intersect,

    SVN_PROP_EXTERNALS,
    SVN_PROP_MERGEINFO,
    SVN_PROP_REVISION_LOG,
    SVN_PROP_REVISION_AUTHOR,
)

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from evn import logic

from evn.path import (
    join_path,
    format_dir,
    extract_component_name,

    PathMatcher,
)

from evn.root import (
    Roots,
    RootPathMatcher,
    SimpleRootMatcher,
)

from evn.change import (
    ChangeSet,
    ChangeType,
    PropertyChangeType,
    ExtendedPropertyChangeType,
)

from evn.util import (
    one,
    none,
    is_int,
    memoize,
    pid_exists,
    literal_eval,
    implicit_context,
    strip_linesep_if_present,
    Pool,
    Dict,
    DecayDict,
    ConfigDict,
    UnexpectedCodePath,
    ImplicitContextSensitiveObject,
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
    format_file_exceeds_max_size_error,
)

#===============================================================================
# Change Attributes
#===============================================================================
_code_lines_cache = dict()
def get_code_lines(fname):
    global _code_lines_cache
    fn = fname[:-1] if fname.endswith('.pyc') else fname
    if fn not in _code_lines_cache:
        with open(fn, 'r') as f:
            _code_lines_cache[fn] = f.read().splitlines()
    return _code_lines_cache[fn]

def get_code_for_lineno(fname, lineno):
    return get_code_lines(fname)[lineno-1]

class ChangeAttribute(object):
    def __init__(self, *args):
        f = inspect.currentframe().f_back.f_back
        c = get_code_for_lineno(f.f_code.co_filename, f.f_lineno)
        self._name = c.split('=')[0].strip()

        setattr(self.__class__, self.name, self)

        self._note = False
        self._requires_confirm = False
        self._requires_confirm_or_ignore = False
        self._msg_initialised = False
        self._msg = str()

        self._change = None
        self._changeset = None
        self._log_msg = None

        if isinstance(args[-1], int):
            ix = args[-1]
            assert ix != -1
            self.args = args[:-1]
        else:
            ix = 1
            self.args = args

        self._fmt = getattr(self.__class__, '_%d' % ix)

    @property
    def name(self):
        return self._name

    @property
    def fmt(self):
        return self._fmt

    @property
    def msg(self):
        if not self._msg_initialised:
            self._fmt = self._pre_process_fmt(self.fmt)
            self._msg = self.fmt % self.args
            self._msg = self._post_process_msg(self._msg)
            self._msg_initialised = True
        return self._msg

    def _pre_process_fmt(self, fmt):
        return fmt

    def _post_process_msg(self, msg):
        return msg

    @property
    def requires_confirm(self):
        return self._requires_confirm

    @property
    def requires_confirm_or_ignore(self):
        return self._requires_confirm_or_ignore

    @property
    def rc(self):
        assert not self.is_note
        assert not self.requires_confirm_or_ignore
        self._requires_confirm = True
        return self

    @property
    def rcoi(self):
        assert not self.is_note
        assert not self.requires_confirm
        self._requires_confirm_or_ignore = True
        return self

    @property
    def note(self):
        assert not self.requires_confirm
        assert not self.requires_confirm_or_ignore
        self._note = True
        return self

    @property
    def error_if_component_repo_else_note(self):
        assert not self.is_note
        assert not self.is_error

    @property
    def is_note(self):
        return self._note

    @property
    def change(self):
        return self._change

    @property
    def changeset(self):
        return self._changeset

    @property
    def log_msg(self):
        return self._log_msg

    @property
    def is_error(self):
        return not self.is_note

    def __call__(self, c):
        cs = c.changeset
        l = cs.log_msg

        self._change = c
        self._changeset = cs
        self._log_msg = l

        self._validate_change()

        #assert not self.requires_confirm_or_ignore
        if self.is_error:
            c.error(self.msg)
        elif self.is_note:
            c.note(self.msg)


class CopyOrRename(ChangeAttribute):
    _1 = '%s COR to %s'
    _2 = '%s COR via replace to %s'
    _3 = '%s COR to unrelated %s'

    def __init__(self, *args):
        ChangeAttribute.__init__(self, *args)

    def _validate_change(self):
        c = self.change
        assert c.is_copy or c.is_rename
        self._validate_component_change()

    def _pre_process_fmt(self, fmt):
        c = self.change
        return fmt.replace('COR', 'copied' if c.is_copy else 'renamed')

    def _validate_component_change(self):
        # Well, this certainly feels hacky.
        repo = RepositoryRevOrTxn.active
        component_depth = repo.component_depth

        if repo.component_depth == -1:
            return

        assert component_depth in (0, 1)

        is_multi = bool(component_depth == 1)
        is_single = bool(component_depth == 0)

        assert (
            (is_single and not is_multi) or
            (is_multi  and not is_single)
        )

        c = self.change
        path = c.path
        if c.is_copy:
            orig_path = c.copied_from_path
        elif c.is_rename:
            orig_path = c.renamed_from_path

        assert path and orig_path, (path, orig_path)

        self._note = False
        if self is CopyOrRename.KnownRootToValidRoot:
            if is_multi:
                if orig_path.count('/') < 3:
                    # Single->multi rename.
                    self._note = True
                    return
                src_component = extract_component_name(orig_path)
                dst_component = extract_component_name(path)
                if src_component == dst_component:
                    self._note = True

                if not self._note:
                    m = self.msg
                    self._msg = (
                        m.replace('known root path', 'component root path')
                         .replace('valid root path', 'unrelated component')
                    )
            else:
                self._note = True

def _load_change_attributes():
    u       = "unknown path"
    t       = "tag"
    b       = "branch"
    k       = "trunk"
    r       = "via replace"
    ur      = "unrelated"
    kr      = "known root path"
    vr      = "valid root path"
    ra      = "root ancestor path"
    krs     = "known root subtree path"
    vrs     = "valid root subtree path"
    arr     = "absolute root of repository"

    _ = CopyOrRename
    # Absolute root of the repository to ...
    AbsoluteToKnownRoot         = _(arr, kr, 2)
    AbsoluteToRootAncestor      = _(arr, ra, 2)

    # Unknown path to ...
    UnknownToKnownRoot          = _(u, kr, 2)
    UnknownToKnownRootSubtree   = _(u, krs)
    UnknownToValidRoot          = _(u, vr)
    UnknownToValidRootSubtree   = _(u, vrs).note
    UnknownToRootAncestor       = _(u, ra, 2)

    # Known root to ...
    KnownRootToUnknown          = _(kr, u).note
    KnownRootToKnownRoot        = _(kr, kr, 2).note
    KnownRootToKnownRootSubtree = _(kr, krs).note
    KnownRootToValidRoot        = _(kr, vr).note
    KnownRootToValidRootSubtree = _(kr, vrs).note
    KnownRootToRootAncestor     = _(kr, ra, 2).rc

    # Known root subtree to ...
    KnownRootSubtreeToUnknown           = _(krs, u)
    KnownRootSubtreeToKnownRoot         = _(krs, kr, 2)
    KnownRootSubtreeToValidRoot         = _(krs, vr)
    KnownRootSubtreeToValidRootSubtree  = _(krs, vrs).rc
    KnownRootSubtreeToRootAncestor      = _(krs, ra, 2)
    KnownRootSubtreeToUnrelatedKnownRootSubtree = _(krs, krs, 3)

    # Valid root to ...
    ValidRootToUnknown          = _(vr, u)
    ValidRootToKnownRoot        = _(vr, kr, 2)
    ValidRootToKnownRootSubtree = _(vr, krs)
    ValidRootToValidRoot        = _(vr, vr).rcoi
    ValidRootToValidRootSubtree = _(vr, vrs).rcoi
    ValidRootToRootAncestor     = _(vr, ra, 2)

    # Valid root subtree to ...
    ValidRootSubtreeToUnknown          = _(vrs, u).note
    ValidRootSubtreeToKnownRoot        = _(vrs, kr, 2).note
    ValidRootSubtreeToKnownRootSubtree = _(vrs, krs).note
    ValidRootSubtreeToValidRoot        = _(vrs, vr).note
    ValidRootSubtreeToValidRootSubtree = _(vrs, vrs).note
    ValidRootSubtreeToRootAncestor     = _(vrs, ra, 2).rc

    # Root ancestor path to ...
    RootAncestorToUnknown           = _(ra, u).rcoi
    RootAncestorToKnownRoot         = _(ra, kr, 2)
    RootAncestorToKnownRootSubtree  = _(ra, krs)
    RootAncestorToValidRoot         = _(ra, vr)
    RootAncestorToValidRootSubtree  = _(ra, vrs)
    RootAncestorToRootAncestor      = _(ra, ra, 2)

_load_change_attributes()

#===============================================================================
# Repository-related Configuration Classes
#===============================================================================

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

#===============================================================================
# Fatal Errors
#===============================================================================

#===============================================================================
# Classes
#===============================================================================
class RepositoryError(Exception):
    pass

class RepositoryRevOrTxn(ImplicitContextSensitiveObject):
    active = None

    def __init__(self, **kwds):
        k = DecayDict(**kwds)

        self.fs                 = k.fs
        self.uri                = k.uri
        self.conf               = k.conf
        self.name               = k.name
        self.path               = k.path
        self.repo               = k.repo
        self.istream            = k.istream
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

        self.__processed_changes                = list()

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

        name_override = join_path(self.path, '.name')
        if os.path.isfile(name_override):
            with open(name_override, 'r') as f:
                self.name = strip_linesep_if_present(f.read())

        self.max_file_size_in_bytes = self.conf.max_file_size_in_bytes
        self.track_file_sizes = bool(self.max_file_size_in_bytes)
        if self.track_file_sizes:
            self.max_file_size_in_mb = (
                float(self.max_file_size_in_bytes) / 1024.0 / 1024.0
            )
            self.options.track_file_sizes = True
            self.options.max_file_size_in_bytes = self.max_file_size_in_bytes

    def __enter__(self):
        assert self.entered is False
        self.entered = True
        self.pool = svn.core.Pool()
        RepositoryRevOrTxn.active = self
        return self

    def __exit__(self, *exc_info):
        if self.__changeset_initialised:
            self.__changeset.destroy()
            self.__changeset = None
        self.pool.destroy()
        RepositoryRevOrTxn.active = None
        self.exited = True

    @implicit_context
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
    def processed_changes(self):
        return self.__processed_changes

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
        # XXX TODO: convert to logic.Mutex().
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
    @memoize
    def component_depth(self):
        rc0 = self.r0_revprop_conf
        v = rc0.get('component_depth')
        if not is_int(v):
            return -1

        d = int(v)
        if d < 0:
            return -1

        return d

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
        username = (user if user else self.user).lower()
        os_username = getpass.getuser().lower()
        if username == os_username:
            return True
        else:
            return username in self.admins

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

    def __create_root(self, change):
        c = change
        assert c.is_create
        rm = self.rootmatcher
        rm.add_root_path(c.path)
        c.root_details = rm.get_root_details(c.path)

        if self.is_txn:
            return

        assert self.is_rev
        d = Dict()
        d.created = c.changeset.rev
        d.creation_method = 'created'
        d.copies = {}
        if c.errors:
            d.errors = c.errors

        self.roots[c.path] = d

    def __new_trunk_via_copy_or_rename(self, change, src_path, src_rev):
        c = change
        assert c.is_copy or c.is_rename
        rm = self.rootmatcher
        rm.add_root_path(c.path)
        c.root_details = rm.get_root_details(c.path)

        if self.is_txn:
            return

        method = 'copy' if c.is_copy else 'rename'

        d = Dict()
        d.created = c.changeset.rev
        d.creation_method = method
        d.copies = {}
        setattr(d, '%s_from' % method, (src_path, src_rev))
        if c.errors:
            d.errors = c.errors

        self.roots[c.path] = d

    def __root_replaced(self, change):
        c = change
        rm = self.rootmatcher
        rm.remove_root_path(c.path)

        if self.is_txn:
            return

        # Mark the evn:roots entry for the root as removed/replaced.
        root = self.__get_root(c.path)
        root.removed = c.changeset.rev
        root.removal_method = 'replaced'

        # And remove it from our roots.
        del self.roots[c.path]

        c.note(e.RootReplaced)

    def __root_removed_directly(self, change):
        c = change
        rm = self.rootmatcher
        rm.remove_root_path(c.path)

        assert c.is_remove
        assert not c.is_replace

        if self.is_txn:
            return

        root = self.__get_root(c.path)
        root.removed = c.changeset.rev
        root.removal_method = 'removed'

        del self.roots[c.path]

        c.note(n.RootRemoved)

    def __find_closest_change(self, change, path):
        c = change
        changeset = c.changeset
        new_change = None
        while path != c.path:
            try:
                new_change = changeset[path]
                break
            except KeyError:
                pass
            path = path[:path[:-1].rfind('/')+1]

        return new_change

    def __roots_removed_indirectly(self, change, roots):
        c = change
        rm = self.rootmatcher

        assert c.is_remove
        assert not c.is_replace

        for root_path in roots:
            assert root_path.startswith(c.path)

            rm.remove_root_path(root_path)

            if self.is_txn:
                continue

            root = self.__get_root(root_path)
            root.removed = c.changeset.rev
            root.removal_method = 'removed_indirectly'
            root.removed_indirectly = c.path

            del self.roots[root_path]

    def __root_replaced_directly(self, change):
        c = change
        rm = self.rootmatcher
        rm.remove_root_path(c.path)

        assert not c.is_remove
        assert c.is_replace

        if self.is_txn:
            return

        root = self.__get_root(c.path)
        root.removed = c.changeset.rev
        root.removal_method = 'replaced'
        root.replaced_by = c.path

        del self.roots[c.path]

        c.note(e.RootReplaced)

    def __roots_replaced_indirectly(self, change, roots):
        c = change
        rm = self.rootmatcher

        assert not c.is_remove
        assert c.is_replace

        for root_path in roots:
            assert root_path.startswith(c.path)
            rm.remove_root_path(root_path)

            if self.is_txn:
                continue

            root = self.__get_root(root_path)
            root.removed = c.changeset.rev
            root.removal_method = 'replaced_indirectly'
            root.replaced_indirectly_by = c.path

            del self.roots[root_path]

    def __get_historical_rootmatcher(self, rev):
        if self.is_txn and rev == self.base_rev:
            return self.rootmatcher

        roots = self.rconf(rev=rev).roots
        return SimpleRootMatcher(set(roots.keys()))

    def __get_copied_root_configdict(self, change):
        c = change
        cfr = c.copied_from_rev
        rc = self.rconf(rev=cfr)
        rev = rc.roots[c.copied_from_path]['created']
        rc = self.rconf(rev=rev)
        return rc.roots[c.copied_from_path]

    def __get_root(self, path, rev=None):
        if not rev:
            rev = self.base_rev
        rc = self.rconf(rev=rev)
        created_rev = rc.roots[path]['created']
        rc = self.rconf(rev=created_rev)
        return rc.roots[path]

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
        if not cs.has_dirs:
            return

        subdirs = [ d for d in cs.dirs ]
        rm = self.rootmatcher
        for sd in subdirs:
            sd.root_details = rm.get_root_details(sd.path)

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
            prefixes = ('http', 'svn', 'file')
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

        if self.track_file_sizes:
            for c in cs.files_over_max_size:
                if self.conf.is_change_excluded_from_size_limits(c):
                    continue
                args = (c.filesize, self.max_file_size_in_bytes)
                msg = format_file_exceeds_max_size_error(*args)
                c.error(msg)

        self.__process_mergeinfo(cs)
        self.__process_toplevel_dirs(cs)
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

    def __known_subtree_to_other_known_subtree(self, change, **kwds):
        k = DecayDict(kwds)
        src_rev = k.src_rev
        src_path = k.src_path
        dst_path = k.dst_path
        src_root_details = k.src_root_details
        dst_root_details = k.dst_root_details
        k.assert_empty(self)

        rm = self.rootmatcher
        pm = self.pathmatcher

        c = change
        assert c.is_copy or c.is_rename

        src_root = src_root_details.root_path
        dst_root = dst_root_details.root_path
        assert src_root != dst_root

        if not c.is_merge:

            if c.is_rename:
                c.error(e.RenameRelocatedPathOutsideKnownRootDuringNonMerge)
            else:
                c.error(e.PathCopiedFromOutsideRootDuringNonMerge)

            return

        if c.is_rename:
            c.error(e.RenameRelocatedPathBetweenKnownRootsDuringMerge)
            return

        assert c.is_copy

        c.changeset.add_possible_merge_source(src_root, src_rev)

        pc = c.merge_root.propchanges
        mipc = pc[SVN_PROP_MERGEINFO]
        merged = mipc.merged
        reverse_merged = mipc.reverse_merged
        # Lop off the trailing '/'
        assert src_root[-1] == '/'
        src_rev_str = str(src_rev)
        consider_inheritance = False
        intersect = lambda a, b, c: svn_rangelist_intersect(a, b, c)
        targets = (merged, reverse_merged)
        found_path = False
        for target in targets:
            for (path, revs) in target.items():
                if not src_path.startswith(path):
                    continue

                found_path = True

                # Fast-path check that the revision is valid.
                if revs.startswith(src_rev_str) or revs.endswith(src_rev_str):
                    return

                # Another fast-path for '123-456'-type rev ranges.
                dashes = revs.count('-')
                if ',' not in revs and '*' not in revs and dashes == 1:
                    (start, end) = [ int(s) for s in revs.split('-') ]
                    if src_rev >= start and src_rev <= end:
                        return
                    else:
                        continue

                # Do a proper rangelist intersection check.
                p = svn.core.Pool()
                c_mi_str = '%s:%d' % (src_root[:-1], src_rev)
                c_mi = svn_mergeinfo_parse(c_mi_str, p)
                c_ri = c_mi[src_root[:-1]]

                src_mi_str = '%s:%s' % (src_root[:-1], revs)
                src_mi = svn_mergeinfo_parse(src_mi_str, p)
                src_ri = src_mi[src_root[:-1]]

                ri = bool(intersect(c_ri, src_ri, consider_inheritance))
                p.destroy()
                del p
                if ri:
                    return

        if not found_path:
            c.error(e.PathCopiedFromUnrelatedKnownRootDuringMerge)
        else:
            c.error(e.PathCopiedFromUnrelatedRevisionDuringMerge)

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
        rd = c.root_details
        if rd.is_absolute:
            if c.is_replace:
                self.__processed_replace(c)
            return

        self._check_component_depth(c)

        pm = self.pathmatcher
        rm = self.rootmatcher

        valid_dst_root_details = pm.get_root_details(c.path)
        known_dst_root_details = rm.get_root_details(c.path)

        dst_roots = rm.find_roots_under_path(format_dir(c.path))
        dst_has_roots_under_it = bool(dst_roots)
        dst_path = c.path

        # dst begin
        dst = logic.Mutex()
        # -> junk/foo/bar/
        dst.unknown = (
            known_dst_root_details.is_unknown and
            valid_dst_root_details.is_unknown and
            not dst_has_roots_under_it
        )

        # -> trunk/ (where 'trunk/' is a known root)
        dst.known_root = (
            c.is_replace and
            not known_dst_root_details.is_unknown and
            known_dst_root_details.root_path == dst_path
        )

        # -> trunk/UI/foo/ (where 'trunk/' is a known root)
        dst.known_root_subtree = (
            not known_dst_root_details.is_unknown and
            known_dst_root_details.root_path != dst_path and
            dst_path.startswith(known_dst_root_details.root_path)
        )

        # -> tags/2.0.x/, branches/foo/, trunk/
        dst.valid_root = (
            known_dst_root_details.is_unknown and
            not valid_dst_root_details.is_unknown and
            valid_dst_root_details.root_path == dst_path and
            not dst_has_roots_under_it
        )

        # -> branches/bugs/8101 (where 'branches/bugs/' is not a known root)
        dst.valid_root_subtree = (
            known_dst_root_details.is_unknown and
            not valid_dst_root_details.is_unknown and
            valid_dst_root_details.root_path != dst_path and
            dst_path.startswith(valid_dst_root_details.root_path) and
            not dst_has_roots_under_it
        )

        # -> /xyz/foo/, where the following roots already exist:
        #       /xyz/foo/trunk
        #       /xyz/foo/branches/1.0.x
        dst.root_ancestor = (
            c.is_replace and
            known_dst_root_details.is_unknown and
            dst_has_roots_under_it
        )
        # dst end

        with dst as dst:

            if dst.unknown or dst.valid_root_subtree:
                # Nothing to do here.
                pass

            elif dst.known_root_subtree:
                if known_dst_root_details.is_tag:
                    c.error(e.TagModified)

            elif dst.valid_root:
                t = logic.Mutex()
                t.tag = valid_dst_root_details.is_tag
                t.trunk = valid_dst_root_details.is_trunk
                t.branch = valid_dst_root_details.is_branch
                with t as t:
                    if t.branch:
                        c.error(e.BranchDirectoryCreatedManually)

                    elif t.tag:
                        c.error(e.TagDirectoryCreatedManually)

                    elif t.trunk:
                        self.__create_root(c)

                    else:
                        raise UnexpectedCodePath

            elif dst.known_root:
                c.error(e.RootReplaced)
                self.__root_replaced(c)

                if valid_dst_root_details.is_trunk:
                    self.__create_root(c)

            elif dst.root_ancestor:
                c.error(e.RootAncestorReplaced)

                for root_path in dst_roots:
                    self.__root_removed_indirectly(c, root_path)

                if valid_dst_root_details.is_trunk:
                    self.__create_root(c)

            else:
                raise UnexpectedCodePath

        dst._unlock()

        if dst.known_root or dst.root_ancestor:
            assert c.is_replace
            self.__processed_replace(c)
        else:
            if c.is_replace:
                self.__processed_replace(c)

        if self.conf.is_blocked_file(c.path):
            c.error(e.BlockedFileExtension)

        return

    def _check_component_depth(self, c):
        standard = self.conf.standard_layout
        if not standard:
            return

        # Ignore files and non-create changes for now (i.e. only process
        # mkdirs)
        if c.is_file or not c.is_create:
            return

        # For now, let's just support an explicit component depth of 0 and 1.
        # We only need to handle 1 here -- 0 implies a single-component layout
        # (i.e. just /trunk, /tags and /branches at the root of the repo), and
        # that is enforced in __process_toplevel_dirs().
        component_depth = self.component_depth
        if component_depth != 1:
            return

        # '/foo/trunk/' -> ['foo', 'trunk']
        parts = c.path.split('/')[1:-1]
        parts_len = len(parts)

        if parts_len != 2:
            return

        err = e.InvalidTopLevelRepoComponentDirectoryCreated % (parts[0], '%s')
        msg = err % ', '.join("'%s'" % r for r in standard)

        path = '/%s/' % parts[-1]
        if path not in standard:
            c.error(msg)

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
        assert c.is_dir

        rm = self.rootmatcher

        known_dst_root_details = rm.get_root_details(c.path)

        dst_roots = rm.find_roots_under_path(format_dir(c.path))
        dst_has_roots_under_it = bool(dst_roots)
        dst_path = c.path

        # dst begin
        dst = logic.Mutex()
        # -> junk/foo/bar/
        dst.unknown = (
            known_dst_root_details.is_unknown and
            not dst_has_roots_under_it
        )

        # -> trunk/ (where 'trunk/' is a known root)
        dst.known_root = (
            not known_dst_root_details.is_unknown and
            known_dst_root_details.root_path == dst_path
        )

        # -> trunk/UI/foo/ (where 'trunk/' is a known root)
        dst.known_root_subtree = (
            not known_dst_root_details.is_unknown and
            known_dst_root_details.root_path != dst_path and
            dst_path.startswith(known_dst_root_details.root_path)
        )

        # -> /xyz/foo/, where the following roots already exist:
        #       /xyz/foo/trunk
        #       /xyz/foo/branches/1.0.x
        dst.root_ancestor = (
            known_dst_root_details.is_unknown and
            dst_has_roots_under_it
        )
        # dst end

        with dst as dst:

            if dst.unknown:
                # Nothing to do here.
                pass

            elif dst.known_root:
                if known_dst_root_details.is_tag:
                    c.error(e.TagRemoved)

                self.__root_removed_directly(c)

            elif dst.known_root_subtree:
                if known_dst_root_details.is_tag:
                    c.error(e.TagSubtreePathRemoved)

            elif dst.root_ancestor:
                c.error(e.RootAncestorRemoved)
                c.error(e.MultipleRootsAffectedByRemove)

                self.__roots_removed_indirectly(c, dst_roots)

            else:
                raise UnexpectedCodePath

        return

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

    def __process_toplevel_dirs(self, cs):
        # Ensure top-level directories in changeset align with standard root
        # layout directories when applicable.
        if cs.is_rev:
            return

        # A non-zero component_depth indicates multi-component repository, in
        # which case, this method doesn't need to run.
        is_multi = bool(self.component_depth == 1)
        is_single = bool(self.component_depth == 0)
        is_neither = bool(self.component_depth == -1)

        standard = self.conf.standard_layout
        if not standard:
            return

        standard_str = ', '.join("'%s'" % r for r in standard)
        single_msg = e.InvalidTopLevelRepoDirectoryCreated % standard_str
        multi_msg = e.StandardLayoutTopLevelDirectoryCreatedInMultiComponentRepo

        for d in cs.dirs:
            c = cs[d.path]
            top = format_dir(d.path.split('/')[1])

            if c.path != top:
                # If the directory already exists, let it through.
                continue

            elif c.is_create:
                if is_multi:
                    if top in standard:
                        # Prevent top-level tags/trunk/branches from being
                        # created if we're a multi-component repository.
                        c.error(multi_msg)

                    else:
                        # Let non-standard top-level directories go through.
                        continue
                elif is_single:
                    if top not in standard:
                        # Prevent non-standard top-level directories from
                        # being created when we're a single-component repo.
                        c.error(single_msg)
                    else:
                        continue
                else:
                    # No component-depth, create whatever you want.
                    continue

            elif top not in standard:
                # If the action isn't create, we don't care if the directory
                # isn't in the standard layout (i.e. could be trying to remove
                # an erroneous directory).
                continue

            elif c.is_remove and is_single:
                c.error(e.TopLevelRepoDirectoryRemoved)

            elif c.is_replace and is_single:
                c.error(e.TopLevelRepoDirectoryReplaced)

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

        change_type = c.change_type
        change_type_name = ChangeType[c.change_type]
        self.__processed_changes.append((change_type_name, c.path))

        self.__process_change_invariants_and_general_correctness(c)
        self.__process_mergeinfo(c)
        if c.is_change:
            # We used to use the following two lines of code here to invoke
            # the appropriate _process_<change_type>() method:
            #   fn = '_process_%s' % ChangeType[c.change_type].lower()
            #   getattr(self, fn)(c)

            # ....which worked fine.  However, getattr(self, fn)(c) isn't
            # particularly useful when viewing a traceback and you want to
            # know which method was affected.  So, let's go back to a good ol'
            # fashion, Python-style switch statement.  i.e. if elif elif else.
            if change_type in (ChangeType.Copy, ChangeType.Rename):
                self._process_copy_or_rename(c)
            elif change_type == ChangeType.Create:
                self._process_create(c)
            elif change_type == ChangeType.Modify:
                self._process_modify(c)
            elif change_type == ChangeType.Remove:
                self._process_remove(c)
            else:
                m = "unsupported change type: %s" % change_type_name
                raise UnexpectedCodePath(m)

        if c.is_replace:
            assert c.path in self._replacements_processed

        if c.is_dir:
            if c.has_dirs:
                if not self.__valid_subdirs(c):
                    return

            for child in c:
                self.__process_change(child)

        return

    def _process_copy_or_rename(self, c):
        # I've gone back and forward a few times on whether or not to deal
        # with copy and renames in separate methods or one combined method.
        # The huge chunk of logic that handles all the 'from path' and 'to
        # path' (src and dst) permutations is almost identical for copies
        # and renames, so I've gone with this combined method, for now.
        # Side bar: this method is pretty heavy on 2-3 letter alias vars
        # for commonly accessed objects.
        assert c.is_copy or c.is_rename

        cs = c.changeset
        rm = self.rootmatcher
        pm = self.pathmatcher

        src_roots = None
        dst_roots = None
        src_roots_len = 0
        dst_roots_len = 0

        # Just a quick refresher on root nomenclature: a 'valid' root is one
        # that is syntactically correct (i.e. '/branches/foo/'), but not a
        # *known* root, i.e. it doesn't have an evn:roots entry.  (This may
        # happen if, say, '/branches/foo/' was created manually via mkdir,
        # instead of being copied from an existing root.)
        #
        # A 'known' root is a root with an evn:roots entry.  If it's not
        # trunk, then it can either be traced back to trunk, or was forcibly
        # converted to a root at some point.

        if c.is_copy:
            src_path = sp = c.copied_from_path
            src_rev  = sr = c.copied_from_rev
            # We need to load the historical root matcher for the rev that's
            # being copied in order to get sensible root details.
            hrm = self.__get_historical_rootmatcher(sr)
            known_src_root_details = ksrd = hrm.get_root_details(sp)
            valid_src_root_details = vsrd = pm.get_root_details(sp)
            src_roots = hrm.find_roots_under_path(format_dir(sp))
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
            known_src_root_details = ksrd = rm.get_root_details(sp)
            valid_src_root_details = vsrd = pm.get_root_details(sp)
            src_roots = rm.find_roots_under_path(format_dir(sp))

        dst_path = dp = c.path

        dst_roots = rm.find_roots_under_path(format_dir(dp))

        src_roots_len = len(src_roots)
        dst_roots_len = len(dst_roots)

        valid_dst_root_details = vdrd = pm.get_root_details(dp)
        known_dst_root_details = kdrd = c.root_details

        src_has_roots_under_it = bool(src_roots)
        dst_has_roots_under_it = bool(dst_roots)

        src_is_root_of_repository = (src_path == '/')
        if src_is_root_of_repository:
            assert c.is_copy
            src_roots = []
            src_roots_len = 0
            src_has_roots_under_it = False


        # src begin
        src = logic.Mutex()
        # / ->
        src.absolute = valid_src_root_details.is_absolute

        # junk/foo/bar/ ->
        src.unknown = (
            known_src_root_details.is_unknown and
            valid_src_root_details.is_unknown and
            not src_has_roots_under_it
        )

        # trunk/, branches/2.0.x/ ->
        src.known_root = (
            not known_src_root_details.is_unknown and
            not valid_src_root_details.is_absolute and
            known_src_root_details.root_path == src_path
        )

        # trunk/UI/foo/ -> (where 'trunk' is a known root)
        src.known_root_subtree = (
            not known_src_root_details.is_unknown and
            not valid_src_root_details.is_absolute and
            known_src_root_details.root_path != src_path and
            src_path.startswith(known_src_root_details.root_path)
        )

        # branches/foo ->, where branches/foo is not a known root
        src.valid_root = (
            known_src_root_details.is_unknown and
            not valid_src_root_details.is_unknown and
            not valid_src_root_details.is_absolute and
            valid_src_root_details.root_path == src_path and
            not src_has_roots_under_it
        )

        # branches/foo/bar, where branches/foo is not a known root
        src.valid_root_subtree = (
            known_src_root_details.is_unknown and
            not valid_src_root_details.is_unknown and
            not valid_src_root_details.is_absolute and
            valid_src_root_details.root_path != src_path and
            src_path.startswith(valid_src_root_details.root_path) and
            not src_has_roots_under_it
        )

        # /xyz/foo/ ->, where the following roots exist:
        #       /xyz/foo/trunk
        #       /xyz/foo/branches/1.0.x
        src.root_ancestor = (
            not valid_src_root_details.is_absolute and
            known_src_root_details.is_unknown and
            src_has_roots_under_it
        )
        # src end

        # dst begin
        dst = logic.Mutex()
        # -> junk/foo/bar/
        dst.unknown = (
            known_dst_root_details.is_unknown and
            valid_dst_root_details.is_unknown and
            not dst_has_roots_under_it
        )

        # -> trunk/ (where 'trunk/' is a known root)
        dst.known_root = (
            c.is_replace and
            not known_dst_root_details.is_unknown and
            known_dst_root_details.root_path == dst_path
        )

        # -> trunk/UI/foo/ (where 'trunk/' is a known root)
        dst.known_root_subtree = (
            not known_dst_root_details.is_unknown and
            known_dst_root_details.root_path != dst_path and
            dst_path.startswith(known_dst_root_details.root_path)
        )

        # -> tags/2.0.x/, branches/foo/, trunk/
        dst.valid_root = (
            known_dst_root_details.is_unknown and
            not valid_dst_root_details.is_unknown and
            valid_dst_root_details.root_path == dst_path and
            not dst_has_roots_under_it
        )

        # -> branches/bugs/8101 (where 'branches/bugs/' is not a known root)
        dst.valid_root_subtree = (
            known_dst_root_details.is_unknown and
            not valid_dst_root_details.is_unknown and
            valid_dst_root_details.root_path != dst_path and
            dst_path.startswith(valid_dst_root_details.root_path) and
            not dst_has_roots_under_it
        )

        # -> /xyz/foo/, where the following roots already exist:
        #       /xyz/foo/trunk
        #       /xyz/foo/branches/1.0.x
        dst.root_ancestor = (
            c.is_replace and
            known_dst_root_details.is_unknown and
            dst_has_roots_under_it
        )
        # dst end

        clean_check = True

        en = 'Copied' if c.is_copy else 'Renamed'

        with contextlib.nested(src, dst) as (src, dst):

            if src.absolute:
                assert not c.is_rename
                if dst.unknown or dst.valid_root or dst.valid_root_subtree:
                    c.error(e.AbsoluteRootOfRepositoryCopied)

                elif dst.known_root:
                    CopyOrRename.AbsoluteToKnownRoot(c)
                    self.__root_replaced_directly(c)

                elif dst.root_ancestor:
                    CopyOrRename.AbsoluteToRootAncestor(c)
                    self.__roots_replaced_indirectly(c, dst_roots)

            elif src.unknown:

                if dst.unknown:
                    pass

                elif dst.known_root:
                    CopyOrRename.UnknownToKnownRoot(c)
                    self.__root_replaced_directly(c)

                elif dst.known_root_subtree:
                    CopyOrRename.UnknownToKnownRootSubtree(c)

                elif dst.valid_root:
                    CopyOrRename.UnknownToValidRoot(c)
                    if valid_dst_root_details.is_trunk:
                        args = (c, src_path, src_rev)
                        self.__new_trunk_via_copy_or_rename(*args)

                elif dst.valid_root_subtree:
                    CopyOrRename.UnknownToValidRootSubtree(c)

                elif dst.root_ancestor:
                    CopyOrRename.UnknownToRootAncestor(c)
                    self.__roots_replaced_indirectly(c, dst_roots)

                else:
                    raise UnexpectedCodePath

            elif src.known_root:

                if known_src_root_details.is_tag:
                    # Always flag attempts to copy or rename tags.
                    c.error(getattr(e, 'Tag' + en))

                if dst.known_root:
                    CopyOrRename.KnownRootToKnownRoot(c)
                    # Given:
                    #   /branches/1.x
                    #   /trunk
                    # Someone has managed to effect the following:
                    #   R /branches/1.x (from /trunk:180)
                    #
                    # We treat this as follows:
                    #
                    #   1. Remove the previous /branches/1.x (treat it as
                    #      though it was explicitly removed).
                    #   2. Treat the new /branches/1.x as though it was a copy
                    #      of the source root.

                    # There's no need to call rm.remove_root_path() or
                    # add_root_path() as we're effectively removing the
                    # '/branches/1.x' branch then adding it back.  Which
                    # means we don't have anything to do if we're a txn.
                    if self.is_txn:
                        raise logic.Break

                    # Find the evn:roots entry for /branches/1.x.
                    root = self.__get_root(dst_path)
                    root.removed = cs.rev
                    root.removal_method = 'replaced'
                    root.replaced_by = (src_path, src_rev)

                    # Delete the old version (just to re-iterate: we add the
                    # new root back below).
                    del self.roots[dst_path]

                    # Create a new entry from the copied/renamed path.
                    d = Dict()
                    d.created = cs.rev
                    d.copies = {}
                    d.errors = c.errors
                    if c.is_copy:
                        d.creation_method = 'copied_via_replace'
                        d.copied_from = (src_path, src_rev)
                    else:
                        d.creation_method = 'renamed_via_replace'
                        d.renamed_from = (src_path, src_rev)

                    # Add it to our roots.
                    self.roots[dst_path] = d

                    # Find the evn:roots entry for when the old root
                    # was created.  If we're a copy, we add the copy
                    # details, if we're a rename, we annotate the root
                    # with the rename/removal details.
                    root = self.__get_root(src_path, src_rev)
                    if c.is_copy:
                        root._add_copy(src_rev, dst_path, cs.rev)
                    else:
                        root.removed = cs.rev
                        root.removal_method = 'renamed_via_replace'
                        root.renamed = (dst_path, cs.rev)

                elif dst.known_root_subtree:
                    # Known root is being renamed to an existing root's
                    # subtree.  The existing root takes precedence so we need
                    # to remove the old root.
                    CopyOrRename.KnownRootToKnownRootSubtree(c)

                    rm.remove_root_path(src_path)

                    if self.is_txn:
                        raise logic.Break

                    root = self.__get_root(src_path, src_rev)
                    root.removed = cs.rev
                    root.removal_method = 'removed_indirectly_via_rename'

                    del self.roots[src_path]

                elif dst.unknown or dst.valid_root or dst.valid_root_subtree:
                    # A known root is being renamed/copied to a new path that
                    # isn't a root ancestor or known root, so we create a new
                    # root.

                    # Given:
                    #   /branches/1.x
                    if dst._peek('unknown'):
                        # Someone has done:
                        #   svn (cp|mv) /branches/1.x /foo/bar
                        CopyOrRename.KnownRootToUnknown(c)
                    elif dst._peek('valid_root'):
                        # Someone has done:
                        #   svn (cp|mv) /branches/1.x /tags/1.0.0
                        CopyOrRename.KnownRootToValidRoot(c)
                    elif dst._peek('valid_root_subtree'):
                        # Someone has done:
                        #   svn (cp|mv) /branches/1.x /branches/foo/bar
                        CopyOrRename.KnownRootToValidRootSubtree(c)
                    else:
                        raise UnexpectedCodePath

                    # Always add the new root.
                    rm.add_root_path(dst_path)

                    if c.is_rename:
                        # Remove the source root if we're a rename...
                        rm.remove_root_path(src_path)
                        paths = (sp, dp)
                        root_details = (ksrd, vdrd)
                        args = (c, paths, root_details)
                        # ....and do some extra checks.
                        self.__known_root_renamed(*args)

                    # Prime the new root details.
                    c.root_details = rm.get_root_details(dst_path)

                    # The rest of the stuff we need to do affects evn:roots,
                    # which we only do if we're a rev.
                    if self.is_txn:
                        raise logic.Break

                    if c.is_rename:
                        # Delete the old root if we're a rename.
                        del self.roots[src_path]

                    # Create a new entry from the copied/renamed path.
                    d = Dict()
                    d.created = cs.rev
                    d.copies = {}
                    d.errors = c.errors
                    if c.is_copy:
                        d.creation_method = 'copied'
                        d.copied_from = (src_path, src_rev)
                    else:
                        d.creation_method = 'renamed'
                        d.renamed_from = (src_path, src_rev)

                    # Add it to our roots.
                    self.roots[dst_path] = d

                    # Find the evn:roots entry for when the old root
                    # was created.  If we're a copy, we add the copy
                    # details, if we're a rename, we annotate the root
                    # with the rename/removal details.
                    root = self.__get_root(src_path, src_rev)
                    if c.is_copy:
                        root._add_copy(src_rev, dst_path, cs.rev)
                    else:
                        root.removed = cs.rev
                        root.removal_method = 'renamed'
                        root.renamed = (dst_path, cs.rev)

                elif dst.root_ancestor:
                    CopyOrRename.KnownRootToRootAncestor(c)
                    self.__roots_replaced_indirectly(c, dst_roots)

                else:
                    raise UnexpectedCodePath

            elif src.known_root_subtree:

                if known_src_root_details.is_tag:
                    # Always flag attempts to copy or rename tag subtrees.
                    c.error(getattr(e, 'TagSubtree' + en))

                if dst.unknown:
                    CopyOrRename.KnownRootSubtreeToUnknown(c)
                    clean_check = False

                elif dst.known_root:
                    CopyOrRename.KnownRootSubtreeToKnownRoot(c)
                    self.__root_replaced_directly(c)

                elif dst.known_root_subtree:
                    clean_check = False
                    src_root = known_src_root_details.root_path
                    dst_root = known_dst_root_details.root_path
                    if src_root != dst_root:
                        k = Dict()
                        k.src_rev = src_rev
                        k.src_path = src_path
                        k.dst_path = dst_path
                        k.src_root_details = known_src_root_details
                        k.dst_root_details = known_dst_root_details
                        fn = self.__known_subtree_to_other_known_subtree
                        fn(c, **k)

                elif dst.valid_root:
                    if not valid_dst_root_details.is_trunk:
                        CopyOrRename.KnownRootSubtreeToValidRoot(c)
                        raise logic.Break

                    args = (c, src_path, src_rev)
                    self.__new_trunk_via_copy_or_rename(*args)

                elif dst.valid_root_subtree:
                    CopyOrRename.KnownRootSubtreeToValidRootSubtree(c)

                elif dst.root_ancestor:
                    CopyOrRename.KnownRootSubtreeToRootAncestor(c)
                    self.__roots_replaced_indirectly(c, dst_roots)

                else:
                    raise UnexpectedCodePath

            elif src.valid_root:

                if dst.unknown:
                    CopyOrRename.ValidRootToUnknown(c)

                elif dst.known_root:
                    CopyOrRename.ValidRootToKnownRoot(c)
                    self.__root_replaced_directly(c)

                elif dst.known_root_subtree:
                    CopyOrRename.ValidRootToKnownRootSubtree(c)

                elif dst.valid_root:
                    CopyOrRename.ValidRootToValidRoot(c)
                    if valid_dst_root_details.is_trunk:
                        args = (c, src_path, src_rev)
                        self.__new_trunk_via_copy_or_rename(*args)

                elif dst.valid_root_subtree:
                    CopyOrRename.ValidRootToValidRootSubtree(c)

                elif dst.root_ancestor:
                    CopyOrRename.ValidRootToRootAncestor(c)
                    self.__roots_replaced_indirectly(c, dst_roots)

                else:
                    raise UnexpectedCodePath

            elif src.valid_root_subtree:

                if dst.unknown:
                    CopyOrRename.ValidRootSubtreeToUnknown(c)

                elif dst.known_root:
                    CopyOrRename.ValidRootSubtreeToKnownRoot(c)
                    self.__root_replaced_directly(c)

                elif dst.known_root_subtree:
                    CopyOrRename.ValidRootSubtreeToKnownRootSubtree(c)

                elif dst.valid_root:
                    CopyOrRename.ValidRootSubtreeToValidRoot(c)
                    if valid_dst_root_details.is_trunk:
                        args = (c, src_path, src_rev)
                        self.__new_trunk_via_copy_or_rename(*args)

                elif dst.valid_root_subtree:
                    CopyOrRename.ValidRootSubtreeToValidRootSubtree(c)

                elif dst.root_ancestor:
                    CopyOrRename.ValidRootSubtreeToRootAncestor(c)
                    self.__roots_replaced_indirectly(c, dst_roots)

                else:
                    raise UnexpectedCodePath

            elif src.root_ancestor:

                copy_or_rename_src_roots = True

                if dst.unknown:
                    CopyOrRename.RootAncestorToUnknown(c)

                elif dst.known_root:
                    CopyOrRename.RootAncestorToKnownRoot(c)
                    self.__root_replaced_directly(c)

                elif dst.known_root_subtree:
                    CopyOrRename.RootAncestorToKnownRootSubtree(c)

                    # Given:
                    #   /foo/branches/1.0.x
                    #   /foo/branches/2.0.x
                    #   /foo/tags/1.0.0
                    #   /foo/tags/2.0.0
                    # And:
                    #   /trunk
                    # Someone has done:
                    #   svn mv ^/foo ^/trunk/foo
                    # Or:
                    #   svn cp ^/foo ^/trunk/foo
                    # Where '/trunk' is a known root.
                    #
                    # We need to:
                    #   1. Remove the /trunk root.
                    #       (Done immediately below.)
                    #   2. Rename/copy all the /foo roots.
                    #       (Done at the end of this if/elif block.)

                    rp = (sp, dp)
                    dst_root = known_dst_root_details.root_path
                    rm.remove_root_path(dst_root)
                    if self.is_rev:
                        root = self.__get_root(dst_root)
                        root.removed = cs.rev
                        root.removal_method = 'removed_indirectly'
                        root.removed_indirectly = rp

                        del self.roots[dst_root]

                elif dst.valid_root:
                    CopyOrRename.RootAncestorToValidRoot(c)

                elif dst.valid_root_subtree:
                    CopyOrRename.RootAncestorToValidRootSubtree(c)

                elif dst.root_ancestor:
                    CopyOrRename.RootAncestorToRootAncestor(c)

                    rp = (sp, dp)
                    if src_roots_len > dst_roots_len:
                        self.__roots_replaced_indirectly(c, dst_roots)

                    elif src_roots_len < dst_roots_len:
                        copy_or_rename_src_roots = False

                    elif src_roots_len == dst_roots_len:
                        # Which one should we keep?  Let's... keep the dst.
                        # Rationale: it's what I came up with after investing
                        # a total of about 20 seconds thinking about which one
                        # we should keep.
                        copy_or_rename_src_roots = False

                    else:
                        raise UnexpectedCodePath

                else:
                    raise UnexpectedCodePath

                if not copy_or_rename_src_roots:
                    self.__roots_replaced_indirectly(c, src_roots)
                    raise logic.Break

                rp = (sp, dp)
                new_roots = [ p.replace(*rp) for p in src_roots ]
                # For each src ancestor affected, check to see if it
                # still exists in the changeset (i.e. it hasn't been
                # subsequently deleted).  If it does, add a new root
                # for it.  If it doesn't, don't.  In either case, we
                # still need to update the relevant root details for
                # when the src root was created (i.e. as either being
                # copied, renamed or removed).
                for (old_root, new_root) in zip(src_roots, new_roots):
                    path = new_root
                    new_change = None
                    while path != c.path:
                        try:
                            new_change = c.changeset[path]
                            break
                        except KeyError:
                            pass
                        path = path[:path[:-1].rfind('/')+1]

                    if not new_change or not new_change.is_change:
                        # The original root has been brought over
                        # cleanly.
                        action = 'keep'
                    else:
                        if new_change.is_remove:
                            action = 'remove'
                        elif new_change.is_rename:
                            action = 'rename'
                        elif new_change.is_copy:
                            action = 'copy'
                        else:
                            ct = ChangeType[new_change.change_type]
                            msg = "unexpected change type: %s" % ct
                            raise RuntimeError(msg)

                    if action == 'keep':
                        # Weird delete ordering (asf@122645) may result in the
                        # old root already being removed by this point.
                        if not old_root in rm.roots_removed:
                            rm.remove_root_path(old_root)
                        rm.add_root_path(new_root)

                    if self.is_txn or action != 'keep':
                        continue

                    # Prepare the new root entry...
                    d = Dict()
                    d.created = cs.rev
                    d.copies = {}
                    if c.errors:
                        d.errors = c.errors
                    if c.is_copy:
                        d.creation_method = 'copied_indirectly'
                        d.copied_indirectly_from = (sp, dp)
                    else:
                        d.creation_method = 'renamed_indirectly'
                        d.renamed_indirectly_from = (sp, dp)
                        d.renamed_from = (old_root, sr)
                        # As we're a rename, delete the old root.
                        del self.roots[old_root]

                    # ....then add it to our roots.
                    assert new_root not in self.roots
                    self.roots[new_root] = d

                    # Find the evn:roots entry for when the old root
                    # was created.  If we're a copy, we add the copy
                    # details, if we're a rename, we record the
                    # rename.
                    root = self.__get_root(old_root, src_rev)
                    if c.is_copy:
                        root._add_copy(sr, new_root, cs.rev)
                    else:
                        root.removed = cs.rev
                        root.removal_method = 'renamed_indirectly'
                        root.renamed_indirectly = rp
                        root.renamed = (new_root, cs.rev)

            else:
                raise UnexpectedCodePath

        src._unlock()
        dst._unlock()

        if dst.known_root or dst.root_ancestor:
            assert c.is_replace
            self.__processed_replace(c)
        else:
            if c.is_replace:
                self.__processed_replace(c)

        if self.conf.is_blocked_file(c.path):
            c.error(e.BlockedFileExtension)

        if c.is_file:
            return

        if clean_check:
            if not c.is_empty:
                c.error(e.UncleanCopy if c.is_copy else e.UncleanRename)

        return

    def __known_root_renamed(self, change, paths, root_details):
        c = change
        (sp, dp)   = paths
        (srd, drd) = root_details

        assert not drd.is_absolute
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
            elif drd.is_tag:
                c.error(e.BranchRenamedToTag)
            else:
                assert drd.is_unknown
                c.error(e.BranchRenamedToUnknown)
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
            elif drd.is_tag:
                c.error(e.TrunkRenamedToTag)
            else:
                assert drd.is_unknown
                c.error(e.TrunkRenamedToUnknownPath)

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
