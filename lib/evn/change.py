#===============================================================================
# Imports
#===============================================================================
import os
import gc
import time

import itertools

import svn
import svn.fs
import svn.core
import svn.repos
import svn.delta

from svn.core import (
    svn_node_dir,
    svn_node_file,
    svn_node_none,
    svn_node_unknown,

    svn_mergeinfo_diff,
    svn_mergeinfo_parse,
    svn_rangelist_to_string,

    SVN_INVALID_REVNUM,
    SVN_PROP_MERGEINFO,
    SVN_PROP_REVISION_LOG,
    SVN_PROP_REVISION_AUTHOR,
)

from collections import (
    defaultdict,
)

from evn.path import (
    format_dir,
    format_file,
    format_path,
    get_root_path,
    PathMatcher,
)

from evn.perfmon import (
    track_resource_usage,
    ResourceUsageTracker,
    DummyResourceUsageTracker,
)

from evn.root import (
    AbsoluteRootDetails,
)

from evn.constants import (
    EVN_ERROR_CONFIRMATIONS,
    EVN_ERROR_CONFIRMATION_BLURB,
)

from evn.util import (
    try_int,
    memoize,
    Pool,
    Dict,
    Options,
    Constant,
    DecayDict,
    NullObject,
    UnexpectedCodePath,
)

#===============================================================================
# Helper Methods
#===============================================================================
def create_propchange(**kwds):
    if kwds['name'] == SVN_PROP_MERGEINFO:
        return MergeinfoPropertyChange(**kwds)
    else:
        return PropertyChange(**kwds)

#===============================================================================
# Change Constant Classes
#===============================================================================
class _ItemKind(Constant):
    Nada    = 0 # 'None' = reserved keyword
    File    = 1
    Dir     = 2
    Unknown = 3
ItemKind = _ItemKind()

class _ChangeType(Constant):
    Nada            = -1
    Copy            = 1
    Create          = 2
    Modify          = 3
    Remove          = 4
    Rename          = 5
ChangeType = _ChangeType()

class _PropertyChangeType(Constant):
    Create  = 1
    Modify  = 2
    Remove  = 3
PropertyChangeType = _PropertyChangeType()

class _ExtendedPropertyChangeType(Constant):
    PropertyCreatedWithValue                = 1
    PropertyCreatedWithoutValue             = 2
    ExistingPropertyValueChanged            = 3
    ExistingPropertyValueCleared            = 4
    ValueProvidedForPreviouslyEmptyProperty = 5
    PropertyRemoved                         = 6
    PropertyChangedButOldAndNewValuesAreSame= 7
ExtendedPropertyChangeType = _ExtendedPropertyChangeType()

PropertyChangeTypeToExtendedPropertyChangeType = {
    PropertyChangeType.Create : (
        ExtendedPropertyChangeType.PropertyCreatedWithValue,
        ExtendedPropertyChangeType.PropertyCreatedWithoutValue,
    ),

    PropertyChangeType.Modify : (
        ExtendedPropertyChangeType.ExistingPropertyValueChanged,
        ExtendedPropertyChangeType.ExistingPropertyValueCleared,
        ExtendedPropertyChangeType.ValueProvidedForPreviouslyEmptyProperty,
        ExtendedPropertyChangeType.PropertyChangedButOldAndNewValuesAreSame,
    ),

    PropertyChangeType.Remove : (
        ExtendedPropertyChangeType.PropertyRemoved,
    ),

}
ExtendedPropertyChangeTypeToChangeType = dict()
for (k, values) in PropertyChangeTypeToExtendedPropertyChangeType.items():
    for v in values:
        ExtendedPropertyChangeTypeToChangeType[v] = k

class _PropertyReplacementType(Constant):
    PropertyRemoved         = 1
    PropertyValueCleared    = 2
    PropertyValueChanged    = 3
PropertyReplacementType = _PropertyReplacementType()

#===============================================================================
# PropertyChange-type Classes
#===============================================================================
class PropertyChange(object):

    def __init__(self, **kwds):
        k = DecayDict(kwds)
        self.__name = k.name
        self.__parent = k.parent
        self.__old_value = k.old_value
        self.__new_value = k.get('new_value')
        self.__replacement = None
        self.__is_replace = False
        replacement = k.get('replacement')
        if replacement:
            self.replacement = replacement
        else:
            self.__is_replace = k.get('is_replace')
        if self.is_replace:
            self.__removal = k.removal
        k.assert_empty(self)

    @property
    def name(self):
        return self.__name

    @property
    def parent(self):
        return self.__parent

    def unparent(self):
        """
        Sets 'parent' attribute to None (asserts 'parent' is not None first).

        This is a (temporary) helper method intended to be called by
        ChangeSet.__del__ to break circular references.
        """
        assert self.parent is not None
        self.__parent = None

    @property
    def old_value(self):
        return self.__old_value

    @property
    def new_value(self):
        return self.__new_value

    @property
    def is_replace(self):
        return self.__is_replace

    @property
    def removal(self):
        assert self.is_replace
        return self.__removal

    @removal.setter
    def removal(self, removal):
        assert self.is_replace
        assert isinstance(removal, PropertyChange)
        assert self.is_replace
        assert self.name == replacement.name
        if self.parent.is_remove:
            assert not replacement.parent.is_replace and (
                replacement.parent.is_copy or
                replacement.parent.is_create or
                replacement.parent.is_modify
            )
        else:
            assert (
                replacement.parent.is_remove and
                replacement.parent.is_replace and (
                    self.is_copy or
                    self.is_create or
                    self.is_modify
                )
            )

        self.__replacement = replacement
        self.__is_replace = True
        if self.parent.is_remove:
            replacement.replacement = self

    @property
    def change_type(self):
        assert not self.is_replace
        return ExtendedPropertyChangeTypeToChangeType[
            self.extended_change_type
        ]

    @property
    def extended_change_type(self):
        assert not self.is_replace
        if self.old_value == self.new_value:
            # Yup, this can happen.
            return ExtendedPropertyChangeType.\
                PropertyChangedButOldAndNewValuesAreSame
        elif self.new_value is not None:
            if self.old_value is None:
                if self.new_value != '':
                    return ExtendedPropertyChangeType.\
                        PropertyCreatedWithValue
                else:
                    return ExtendedPropertyChangeType.\
                        PropertyCreatedWithoutValue
            elif self.old_value != '':
                if self.new_value != '':
                    return ExtendedPropertyChangeType.\
                        ExistingPropertyValueChanged
                else:
                    return ExtendedPropertyChangeType.\
                        ExistingPropertyValueCleared
            else:
                assert self.new_value
                return ExtendedPropertyChangeType.\
                    ValueProvidedForPreviouslyEmptyProperty
        else:
            assert self.old_value is not None
            return ExtendedPropertyChangeType.PropertyRemoved

    @property
    def replacement_type(self):
        assert self.is_replace
        if not self.parent.is_remove:
            return self.replacement.replacement_type
        else:
            if self.new_value is None:
                return PropertyReplacementType.PropertyRemoved
            elif self.new_value is '':
                return PropertyReplacementType.PropertyValueCleared
            elif self.new_value != self.old_value:
                return PropertyReplacementType.PropertyValueChanged
            else:
                raise UnexpectedCodePath

    @property
    def replacement(self):
        assert self.is_replace and self.__replacement is not None
        return self.__replacement

    @replacement.setter
    def replacement(self, replacement):
        assert isinstance(replacement, PropertyChange)
        assert not self.is_replace
        assert self.name == replacement.name
        if self.parent.is_remove:
            assert not replacement.parent.is_replace and (
                replacement.parent.is_copy or
                replacement.parent.is_create or
                replacement.parent.is_modify
            )
        else:
            assert (
                replacement.parent.is_remove and
                replacement.parent.is_replace and (
                    self.is_copy or
                    self.is_create or
                    self.is_modify
                )
            )

        self.__replacement = replacement
        self.__is_replace = True
        if self.parent.is_remove:
            replacement.replacement = self

    def __repr__(self):
        r = [
            ("name", self.name),
            ("path", self.parent.path),
        ]
        if self.is_replace:
            r += [
                ("replacement_type", PropertyReplacementType[
                    self.replacement_type
                ])
            ]
        else:
            r += [
                ("change_type", PropertyChangeType[self.change_type]),
                ("extended_change_type", ExtendedPropertyChangeType[
                    self.extended_change_type
                ]),
            ]
        if self.old_value:
            r.append(("old_value", self.old_value))
        if self.new_value:
            r.append(("new_value", self.new_value))

        return "<%s(%s)>" % (
            self.__class__.__name__,
            ', '.join('%s=%s' % (k, v) for (k, v) in r),
        )

class MergeinfoPropertyChange(PropertyChange):
    def __init__(self, **kwds):
        PropertyChange.__init__(self, **kwds)

        self.__merged = dict()
        self.__reverse_merged = dict()

        p = svn.core.Pool()
        values = (self.old_value, self.new_value)
        (old, new) = (v if v else '' for v in values)
        old = svn_mergeinfo_parse(old, p)
        new = svn_mergeinfo_parse(new, p)
        consider_inheritance = True
        diff = svn_mergeinfo_diff(old, new, consider_inheritance, p)
        (deleted, added) = diff
        for (k, v) in deleted.items():
            assert k not in self.__reverse_merged
            self.__reverse_merged[k] = str(svn_rangelist_to_string(v, p))

        for (k, v) in added.items():
            assert k not in self.__merged
            self.__merged[k] = str(svn_rangelist_to_string(v, p))

        p.destroy()
        del p


    @property
    def merged(self):
        return self.__merged

    @property
    def reverse_merged(self):
        return self.__reverse_merged

    def __repr__(self):
        r = [
            ("path", self.parent.path),
        ]
        if self.is_replace:
            r += [
                ("replacement_type", PropertyReplacementType[
                    self.replacement_type
                ])
            ]
        else:
            r += [
                ("change_type", PropertyChangeType[self.change_type]),
                ("extended_change_type", ExtendedPropertyChangeType[
                    self.extended_change_type
                ]),
            ]
        if self.reverse_merged:
            r.append(("reverse_merged", self.reverse_merged))
        if self.merged:
            r.append(("merged", self.merged))

        return "<%s(%s)>" % (
            self.__class__.__name__,
            ', '.join('%s=%s' % (k, v) for (k, v) in r),
        )

#===============================================================================
# Change-type Classes
#===============================================================================
class AbstractChange(object):
    def __init__(self, **kwds):
        object.__init__(self)
        k = DecayDict(kwds)
        self.__kwds = kwds
        self.__path = k.path
        self._assert_empty(k)

        self.__is_open = True
        self.__close_count = itertools.count(1)
        self.__proplist = None
        self.__propchanges = dict()
        self.__change_prop = dict()

        self.__previous_proplist = None
        self.__has_loaded_propchanges = False

        self.__destroyed = False

    def destroy(self):
        assert not self.__destroyed
        self.__destroyed = True

        for (k, v) in self.__propchanges.items():
            v.unparent()
            del v
            del self.__propchanges[k]

        del self.__propchanges
        self.__propchanges = None

    #def __del__(self):
    #    if not self.__destroyed:
    #        self.destroy()

    def _get_proplist(self, path, rev=None):
        raise NotImplementedError()

    @property
    def is_tag(self):
        return self.root_details.is_tag

    @property
    def is_trunk(self):
        return self.root_details.is_trunk

    @property
    def is_branch(self):
        return self.root_details.is_branch

    def was_xxx(self, root_type):
        rootmatcher = self.root_details.rootmatcher
        if self.path not in rootmatcher.roots_removed:
            return False

        pathmatcher = rootmatcher.pathmatcher
        root_details = pathmatcher.get_root_details(self.path)
        return getattr(root_details, 'is_%s' % root_type)

    @property
    def was_tag(self):
        return self.was_xxx('tag')

    @property
    def was_trunk(self):
        return self.was_xxx('trunk')

    @property
    def was_branch(self):
        return self.was_xxx('branch')

    @property
    def is_tag_create(self):
        return (
            self.is_root and
            self.is_copy and
            self.is_tag
        )

    @property
    def is_tag_remove(self):
        return (
            self.is_root and
            self.is_remove and
            self.was_tag
        )

    @property
    def is_branch_create(self):
        return (
            self.is_root and
            self.is_copy and
            self.is_branch
        )

    @property
    def is_branch_remove(self):
        return (
            self.is_root and
            self.is_remove and
            self.was_branch
        )

    @property
    def has_checked_modify_invariants(self):
        raise NotImplementedError()

    @property
    def has_loaded_propchanges(self):
        return self.__has_loaded_propchanges

    @property
    def propchanges(self):
        assert self.has_loaded_propchanges
        return self.__propchanges

    def has_propchange(self, name):
        assert self.has_loaded_propchanges
        return name in self.__propchanges

    def get_propchange(self, name):
        assert self.has_loaded_propchanges
        return self.__propchanges[name]

    def _add_propchange(self, propchange):
        assert propchange.name not in self.__propchanges
        assert propchange.parent == self
        self.__propchanges[propchange.name] = propchange

    @property
    def change_type(self):
        raise NotImplementedError()

    @change_type.setter
    def change_type(self):
        raise NotImplementedError()

    @property
    def path(self):
        return self.__path

    @property
    def is_open(self):
        return self.__is_open

    @property
    def is_changeset(self):
        raise NotImplementedError()

    @property
    def path(self):
        return self.__path

    @property
    def previous_path(self):
        raise NotImplementedError()

    @property
    def previous_rev(self):
        raise NotImplementedError()

    @property
    def has_propchanges(self):
        assert self.is_changeset or not self.is_remove
        return bool(len(self.__propchanges))

    @property
    def proplist(self):
        assert self.is_changeset or not self.is_remove
        if self.__proplist is None:
            self.__proplist = self._get_proplist(self.path)
        return self.__proplist

    @property
    def previous_proplist(self):
        assert self.is_modify
        if self.is_changeset:
            previous_path = '/'
            previous_rev  = self.base_rev
        else:
            assert self.previous_path and self.previous_rev
            previous_path = self.previous_path
            previous_rev  = self.previous_rev

        if self.__previous_proplist is None:
            self.__previous_proplist = self._get_proplist(
                previous_path,
                previous_rev,
            )
        return self.__previous_proplist

    @property
    def is_change(self):
        return self.change_type != ChangeType.Nada

    @property
    def is_modify(self):
        return self.change_type == ChangeType.Modify

    @property
    def is_dir(self):
        raise NotImplementedError()

    @property
    def node_kind(self):
        raise NotImplementedError()

    @property
    def base_node_kind(self):
        raise NotImplementedError()

    @property
    def node_type(self):
        raise NotImplementedError()

    def _close(self):
        # Protect against _close() being called multiple times.
        assert self.__close_count.next() == 1
        self.__is_open = False

    def _change_prop(self, name, value):
        if not self.is_change:
            self.change_type = ChangeType.Modify
        assert name not in self.__change_prop
        self.__change_prop[name] = value

    def _load_propchanges(self):
        assert not self.has_loaded_propchanges
        for (name, new_value) in self.__change_prop.items():
            if new_value is not None:
                assert new_value == self.proplist[name]
            k = Dict()
            k.name = name
            k.new_value = new_value
            if not self.is_changeset and self.is_create:
                k.old_value = None
            else:
                assert (
                    self.is_changeset or
                    self.is_modify or
                    self.is_copy or
                    self.is_rename
                )
                if self.is_changeset:
                    old_proplist = self.previous_proplist
                elif self.is_modify:
                    old_proplist = self.previous_proplist
                elif self.is_copy:
                    old_proplist = self.copied_from_proplist
                elif self.is_rename:
                    old_proplist = self.renamed_from_proplist
                else:
                    raise UnexpectedCodePath()

                if name not in old_proplist:
                    k.old_value = None
                else:
                    old_value = old_proplist[name]
                    if not old_value:
                        k.old_value = ''
                    else:
                        # We used to assert that old_value != new_value here;
                        # but then we ran into repos in the wild where prop
                        # changes were being triggered but the old and new
                        # values are identical.
                        k.old_value = old_value

            k.parent = self
            self._add_propchange(create_propchange(**k))

        self.__has_loaded_propchanges = True

    def _format(self, p):
        return p if p[0] == '/' else '/' + p

    def _format_path(self, p, is_dir=None):
        n = p
        if n is not None:
            if is_dir == False:
                assert n != ''
            n = format_path(self._format(n), is_dir=is_dir)

        return n

    def _format_file(self, p):
        f = p
        if f is not None:
            assert f != ''
            f = format_file(self._format(f))

        return f

    def _format_dir(self, p):
        d = p
        if d is not None:
            if d == '':
                d = '/'
            else:
                d = format_dir(self._format(d))

        return d

    def _assert_empty(self, decaydict):
        assert isinstance(decaydict, DecayDict)
        if decaydict:
            raise RuntimeError(
                "%s:%s: unexpected keywords: %s" % (
                    self.__class__.__name__,
                    inspect.currentframe().f_back.f_code.co_name,
                    repr(decaydict)
                )
            )

    def _build_repr(self):
        if not self.is_change:
            first = ("is_change", "False")
        else:
            first = ("is_" + ChangeType[self.change_type].lower(), "True")
        return [
            first,
            ("type", self.node_type),
        ]

    def __repr__(self):
        return "<%s(%s)>" % (
            self.__class__.__name__,
            ', '.join('%s=%s' % (k, v) for (k, v) in self._build_repr()),
        )

class NodeChange(AbstractChange):
    def __init__(self, **kwds):
        k = DecayDict(kwds)
        self.__parent = k.parent
        self.__changeset = k.changeset
        self.__change_type = k.change_type
        if self.is_copy:
            self.__copied_from_path = k.copied_from_path
            self.__copied_from_rev  = k.copied_from_rev
            self.__copied_from_proplist = k.copied_from_proplist
        elif self.is_remove:
            self.__removed_from_path = k.removed_from_path
            self.__removed_from_rev  = k.removed_from_rev
            self.__removed_from_proplist = k.removed_from_proplist

        AbstractChange.__init__(self, path=k.path)
        k.assert_empty(self)
        del k

        # change type and path will be unique for the entire changeset
        self.__hash = (self.change_type, self.path)

        self.parent.add(self)

        self.__old = None
        self.__proplist = None
        self.__previous_proplist = None
        self.__has_changed_type = False
        self.__registered = False

        self.__copy = None
        self.__modify = None
        self.__rename = None
        self.__remove = None
        self.__is_replace = False
        self.__replacement = None

        self.__base_node_kind = None
        self.__base_node_kind_initialized = False

        self.__previous_rev = None
        self.__previous_path = None
        self.__previous_parent_path = None
        self.__checked_modify_invariants = False

        self.__propreplacements = dict()
        self.__has_loaded_propchanges = False
        self.__has_loaded_propreplacements = False

        self.__notes = list()
        self.__errors = list()
        self.__warnings = list()

    @property
    def notes(self):
        return self.__notes

    @property
    def errors(self):
        return self.__errors

    @property
    def warnings(self):
        return self.__warnings

    def note(self, n):
        if '%' in n:
            n = n % self
        self.__notes.append(n)
        self.changeset.note(self, n)

    def error(self, e):
        c = EVN_ERROR_CONFIRMATIONS.get(e, '')
        if '%' in e:
            e = e % self
        self.__errors.append(e)

        self.changeset.error(self, e, confirm=c)

    def warn(self, w):
        if '%' in w:
            w = w % self
        self.__warnings.append(w)
        self.changeset.warn(self, w)

    @property
    def root_details(self):
        raise NotImplementedError

    @property
    def is_root(self):
        raise NotImplementedError

    @property
    def is_subtree(self):
        raise NotImplementedError

    @property
    def merge_root(self):
        raise NotImplementedError

    @property
    def has_propchanges(self):
        assert not self.is_remove
        return super(NodeChange, self).has_propchanges

    @property
    def previous_path(self):
        assert self.is_modify and self.has_checked_modify_invariants
        return self.__previous_path

    @property
    def previous_rev(self):
        assert self.is_modify and self.has_checked_modify_invariants
        return self.__previous_rev

    @property
    def previous_parent_path(self):
        assert self.is_modify and self.has_checked_modify_invariants
        return self.__previous_parent_path

    def _add_propchange(self, propchange):
        AbstractChange._add_propchange(self, propchange)
        self.changeset._register_propchange(propchange)

    def _add_propreplacement(self, propchange):
        assert propchange.is_replace
        assert propchange.name not in self.__propreplacements
        self.__propreplacements[propchange.name] = propchange
        self.changeset._register_propreplacement(propchange)

    @property
    def is_merge(self):
        return bool(self.merge_root)

    @property
    def has_mergeinfo_propchange(self):
        if self.is_remove:
            return False

        if not self.has_propchange(SVN_PROP_MERGEINFO):
            return False

        propchange = self.get_propchange(SVN_PROP_MERGEINFO)
        extended_change_type = propchange.extended_change_type

        ex = ExtendedPropertyChangeType
        return (
            extended_change_type in (
                ex.PropertyCreatedWithValue,
                ex.ExistingPropertyValueChanged,
                ex.ValueProvidedForPreviouslyEmptyProperty,
            )
        )

    def collect_mergeinfo_propchanges(self, mi):
        if self.has_mergeinfo_propchange:
            mi.append(self.get_propchange(SVN_PROP_MERGEINFO))
        if not self.parent.is_changeset:
            self.parent.collect_mergeinfo_propchanges(mi)

    @property
    def has_propreplacements(self):
        assert self.is_change
        assert self.has_loaded_propreplacements
        return bool(len(self.__propreplacements))

    def has_propreplacement(self, name):
        assert self.is_change
        assert self.has_loaded_propreplacements
        return name in self.__propreplacements

    @property
    def has_loaded_propreplacements(self):
        return self.__has_loaded_propreplacements

    @property
    def propreplacements(self):
        return dict(self.__propreplacements)

    @property
    def replacement(self):
        assert self.is_replace and self.__replacement is not None
        return self.__replacement

    @replacement.setter
    def replacement(self, change):
        assert isinstance(change, NodeChange)
        assert not self.is_replace
        assert self.path == change.path
        if self.is_remove:
            assert not change.is_replace and (
                change.is_copy or
                change.is_create or
                change.is_modify
            )
        else:
            assert change.is_remove and change.is_replace and (
                self.is_copy or
                self.is_create or
                self.is_modify
            )

        self.__replacement = change
        self.__is_replace = True
        if self.is_remove:
            change.replacement = self
            self.changeset.replace(self, change)

    def _load_propchanges(self):
        if not self.is_remove:
            AbstractChange._load_propchanges(self)
        elif not self.is_replace:
            assert not self.has_loaded_propchanges
            for (name, old_value) in self.removed_from_proplist.items():
                k = Dict()
                k.name = name
                k.old_value = old_value
                k.new_value = None
                k.parent = self
                self._add_propchange(create_propchange(**k))
            self.__has_loaded_propchanges = True

    @property
    def has_loaded_propchanges(self):
        if not self.is_remove:
            return super(NodeChange, self).has_loaded_propchanges
        else:
            return self.__has_loaded_propchanges

    def _load_propreplacements(self):
        assert self.is_remove and self.is_replace

        replacement = self.replacement
        for (name, old_value) in self.removed_from_proplist.items():
            k = Dict()
            k.name = name
            k.old_value = old_value
            if name not in replacement.proplist:
                k.new_value = None
            else:
                new_value = replacement.proplist[name]
                if not new_value:
                    k.new_value = ''
                elif old_value != new_value:
                    k.new_value = new_value
                else:
                    continue
            if replacement.has_propchange(name):
                k.replacement = replacement.get_propchange(name)
            else:
                k.is_replace = True

            k.parent = self
            self._add_propreplacement(create_propchange(**k))

    @property
    def has_checked_modify_invariants(self):
        return self.__checked_modify_invariants

    @property
    def base_node_kind(self):
        if not self.__base_node_kind_initialized:
            base_rev = self.changeset.base_rev
            base_root = self.changeset._get_root(base_rev)
            with Pool() as pool:
                base_kind = svn.fs.check_path(base_root, self.path, pool)
            self.__base_node_kind = base_kind
            self.__base_node_kind_initialized = True
        return self.__base_node_kind

    @property
    def existed_previously(self):
        return (self.node_kind == self.base_node_kind)

    def _check_modify_invariants(self):
        assert self.is_modify
        assert self.has_checked_modify_invariants == False
        if self.base_node_kind in (svn_node_file, svn_node_dir):
            self.__previous_rev = self.changeset.base_rev
            self.__previous_path = self.path
            self.__previous_parent_path = self.parent.path
        else:
            self.changeset._indirect_copy_then_modify.append(self.path)
            # We're a modify, but we didn't exist at the same path in the
            # base revision, which means that we're an indirect copy; i.e.
            # one of our grandparents is of type copy.  We use the same
            # approach below as in ChangeSet.delete_entry().

            # XXX TODO: this... isn't particularly elegant.
            args = (self.path, self.parent)
            k = self.changeset._find_first_parent_copy_or_rename(*args)
            self.__previous_rev = k.base_rev
            self.__previous_path = k.base_path
            self.__previous_parent_path = k.base_parent_path

        self.__checked_modify_invariants = True

    @property
    def rename(self):
        assert self.__rename is not None
        assert self.is_rename or self.is_remove

    @rename.setter
    def rename(self, change):
        assert isinstance(change, NodeChange)
        assert not self.is_rename
        assert self.path != change.path
        assert (
            (self.is_remove and change.is_copy) or
            (self.is_copy and change.is_remove)
        )

        self.__rename = change
        if self.is_remove:
            change.rename = self
            self.changeset.rename(self, change)
        else:
            self.__change_type = ChangeType.Rename

    def __hash__(self):
        return self.__hash.__hash__()

    @property
    def is_replace(self):
        return self.__is_replace

    @property
    def is_file(self):
        raise NotImplementedError()

    @property
    def change_type(self):
        return self.__change_type

    @change_type.setter
    def change_type(self, value):
        assert not self.is_change
        assert value == ChangeType.Modify
        self.__change_type = value
        self.changeset.modify(self)

    @property
    def parent(self):
        return self.__parent

    def reparent(self, parent):
        assert self.__parent != parent
        self.parent.remove(self)
        self.__parent = parent
        self.parent.add(self)

    def unparent(self):
        """
        Sets 'parent' and 'changeset' attributes to None (asserts 'parent'
        and 'changeset' are not None first).

        This is a (temporary) helper method intended to be called by
        ChangeSet.destroy to break circular references.
        """
        assert self.parent is not None
        assert self.changeset is not None
        self.__parent = None
        self.__changeset = None

    def _get_proplist(self, path, rev=None):
        return self.changeset._get_proplist(path, rev=rev)

    @property
    def registered(self):
        return self.__registered

    @registered.setter
    def registered(self, value):
        assert not self.__registered
        assert value == True
        self.__registered = True

    @property
    def changeset(self):
        return self.__changeset

    @property
    def is_changeset(self):
        return False

    @property
    def is_copy(self):
        return self.change_type == ChangeType.Copy

    @property
    def is_create(self):
        return self.change_type == ChangeType.Create

    @property
    def is_remove(self):
        return self.change_type == ChangeType.Remove

    @property
    def is_rename(self):
        return self.change_type == ChangeType.Rename

    @property
    def copied_from_path(self):
        assert self.is_copy
        return self.__copied_from_path

    @property
    def copied_from_rev(self):
        assert self.is_copy
        return self.__copied_from_rev

    @property
    def copied_from_proplist(self):
        assert self.is_copy
        return self.__copied_from_proplist

    @property
    def renamed_from_path(self):
        assert self.is_rename
        return self.__copied_from_path

    @property
    def renamed_from_rev(self):
        assert self.is_rename
        return self.__copied_from_rev

    @property
    def renamed_from_proplist(self):
        assert self.is_rename
        return self.__copied_from_proplist

    @property
    def removed_from_path(self):
        assert self.is_remove
        return self.__removed_from_path

    @property
    def removed_from_rev(self):
        assert self.is_remove
        return self.__removed_from_rev

    @property
    def removed_from_proplist(self):
        assert self.is_remove
        return self.__removed_from_proplist

    @property
    def replaced_proplist(self):
        assert self.is_replace
        return self.__replaced_proplist

    def _build_repr(self):
        r = AbstractChange._build_repr(self)
        r.append(("path", self.path))

        if not self.is_change or not self.is_remove:
            r += [
                ("has_propchanges", repr(self.has_propchanges)),
            ]
            if self.has_propchanges:
                names = self.propchanges.keys()
                if len(names) == 1:
                    r.append(("props_changed", names[0]))
                else:
                    names = "(%s)" % ', '.join(names)
                    r.append(("props_changed", names))

        if self.is_change:
            if self.is_replace:
                r += [
                    ("is_replace", "True"),
                ]
            if self.is_copy:
                r += [
                    ("copied_from_path", self.copied_from_path),
                    ("copied_from_rev", self.copied_from_rev),
                    ("copied_from_proplist", self.copied_from_proplist),
                ]
            elif self.is_create:
                pass
            elif self.is_modify:
                if not self.existed_previously:
                    r.append(("existed_previously", "False"))
                    if self.has_checked_modify_invariants:
                        r += [
                            ("previous_path", self.previous_path),
                            ("previous_rev", self.previous_rev),
                            ("previous_parent_path", \
                                self.previous_parent_path
                            ),
                        ]
            elif self.is_rename:
                r += [
                    ("renamed_from_path", self.renamed_from_path),
                    ("renamed_from_rev", self.renamed_from_rev),
                    ("renamed_from_proplist", self.renamed_from_proplist),
                ]
            elif self.is_remove:
                r += [
                    ("removed_from_path", self.removed_from_path),
                    ("removed_from_rev", self.removed_from_rev),
                    ("removed_from_proplist", self.removed_from_proplist),
                ]
            else:
                # We should never reach here.
                raise UnexpectedCodePath()
        return r

class AbstractChangeSet(set, AbstractChange):

    def __init__(self, **kwds):
        if kwds:
            AbstractChange.__init__(self, **kwds)
        self.__paths = set()
        self.__subdir = None
        self.__dir_count = 0
        self.__file_count = 0
        self.__child_count = 0

        self.__destroyed = None

    def destroy(self):
        assert not self.__destroyed
        self.__destroyed = True
        set.clear(self)
        AbstractChange.destroy(self)

    def collect_mergeinfo_propchanges_forward(self, mi):
        if self.has_mergeinfo_propchange:
            mi.append((self, self.get_propchange(SVN_PROP_MERGEINFO)))
        for child in self:
            child.collect_mergeinfo_propchanges_forward(mi)

    def collect_mergeinfo_forward(self, mi):
        pl = self.proplist
        if SVN_PROP_MERGEINFO in pl:
            mi.append((self, pl[SVN_PROP_MERGEINFO]))
        for child in self:
            child.collect_mergeinfo_forward(mi)

    @property
    def top(self):
        """
        Iff one child change is present, return it.  Otherwise, return an
        instance of a NullObject.
        """
        if self.child_count != 1:
            return NullObject()
        else:
            top = None
            for child in self:
                top = child
                break
            return top

    @property
    def paths(self):
        return self.__paths

    @property
    def subdir(self):
        return self.__subdir

    @property
    def child_count(self):
        assert len(self) == self.__child_count
        return self.__child_count

    @property
    def dir_count(self):
        return self.__dir_count

    @property
    def is_empty(self):
        return self.child_count == 0

    @property
    def has_files(self):
        return self.file_count > 0

    @property
    def has_dirs(self):
        return self.dir_count > 0

    @property
    def file_count(self):
        return self.__file_count

    @property
    def files(self):
        return (c for c in self if c.is_file)

    @property
    def dirs(self):
        return (c for c in self if c.is_dir)

    @property
    def dir_names(self):
        assert self.has_dirs
        return (os.path.dirname(c.path) + '/' for c in self if c.is_dir)

    @property
    def file_names(self):
        assert self.has_files
        return (os.path.basename(c.path) for c in self if c.is_file)

    def add(self, child):
        assert child not in self
        assert child.parent == self
        set.add(self, child)
        if child.path in self.paths:
            if self.is_changeset:
                quirky = self._quirky_adds
            else:
                quirky = self.changeset._quirky_adds
            quirky.append((child.path, self))
        else:
            self.paths.add(child.path)
        self.__child_count += 1
        if child.is_file:
            self.__file_count += 1
        else:
            self.__dir_count += 1
        self.__refresh_subdir()

    def remove(self, child):
        assert child in self
        assert child.parent == self
        if child.path not in self.paths:
            if self.is_changeset:
                quirky = self._quirky_removes
            else:
                quirky = self.changeset._quirky_removes
            quirky.append((child.path, self))
        else:
            self.paths.remove(child.path)
        set.remove(self, child)
        self.__child_count -= 1
        if child.is_file:
            self.__file_count -= 1
        else:
            self.__dir_count -= 1
        self.__refresh_subdir()
        if not self.is_changeset:
            if self.is_empty and not self.is_change:
                if not self.parent.is_changeset:
                    if self in self.parent:
                        self.parent.remove(self)

    def __refresh_subdir(self):
        if self.dir_count == 1 and not self.has_files:
            self.__subdir = [ s for s in self.dirs ][0]
        else:
            self.__subdir = None

    def _build_repr(self):
        r = list()
        if self.is_empty:
            r += [
                ("is_empty", "True"),
            ]
        elif self.subdir:
            r += [
                ("subdir", self.subdir.path),
            ]
        else:
            r += [
                ("child_count", self.child_count),
            ]
            if self.has_files:
                r += [
                    ("file_count", self.file_count),
                    ("file_names", "(%s)" % ', '.join(
                        "'%s'" % n for n in self.file_names
                        ),
                    ),
                ]
            if self.has_dirs:
                r += [
                    ("dir_count", self.dir_count),
                    ("dir_names", "(%s)" % ', '.join(
                        "'%s'" % n for n in self.dir_names
                        ),
                    ),
                ]
        return r


class DirectoryChange(AbstractChangeSet, NodeChange):

    def __init__(self, **kwds):
        set.__init__(self)
        self.__root_details = None
        NodeChange.__init__(self, **kwds)
        AbstractChangeSet.__init__(self)

        self.__destroyed = None

    def destroy(self):
        assert not self.__destroyed
        self.__destroyed = True
        self.__root_details = None
        AbstractChangeSet.destroy(self)

    def __hash__(self):
        return NodeChange.__hash__(self)

    def __nonzero__(self):
        # Without the following, the following happens:
        #   >>> change.is_empty
        #   True
        #   >>> 'change_exists' if change else 'change_does_not_exist'
        #   'change_does_not_exist'
        #
        # i.e. because we derive from set(), and an empty set fails the Python
        # truth test, an `if change:` type expression will fail unexpectedly.
        return True

    @property
    def is_subtree(self):
        return not self.is_root

    @property
    def root(self):
        return self if self.is_root else self.parent.root

    @property
    def root_details(self):
        root_details = self.__root_details
        if root_details:
            if root_details.version is None:
                return root_details

            path = self.path
            rootmatcher = root_details.rootmatcher
            if root_details.version < rootmatcher.version:
                root_details = rootmatcher.get_root_details(path)
                self.__root_details = root_details
            return root_details
        else:
            return self.parent.root_details

    @root_details.setter
    def root_details(self, value):
        self.__root_details = value

    @property
    def is_root(self):
        return self.root_details.root_path == self.path

    @property
    def merge_root(self):
        return self if self.has_mergeinfo_propchange else (
            None if self.parent.is_changeset else self.parent.merge_root
        )

    def collect_parents(self, parents):
        parents.append(self)
        if self.parent.is_changeset:
            parents.append(self.parent)
        else:
            self.collect_parents(parents)

    def find_first_copy_or_rename_parent(self):
        if not self.is_copy and not self.is_rename:
            if self.parent.is_changeset:
                return None
            else:
                return self.parent.find_first_copy_or_rename_parent()
        else:
            return self

    def collect_parent_replacements(self, pr):
        if self.is_replace:
            pr.append(self)
        if not self.parent.is_changeset:
            self.parent.collect_parent_replacements(pr)

    @property
    def is_file(self):
        return False

    @property
    def is_dir(self):
        return True

    @property
    def node_kind(self):
        return svn_node_dir

    @property
    def node_type(self):
        return 'dir'

    @property
    def is_an_action_root(self):
        return (
            not self.is_replace and (
                self.is_copy or
                self.is_create or
                self.is_rename
            )
        )

    def _build_repr(self):
        return (
            NodeChange._build_repr(self) +
            AbstractChangeSet._build_repr(self)
        )

    def __repr__(self):
        return AbstractChange.__repr__(self)

    def _close(self):
        NodeChange._close(self)
        if self.is_modify and not self.is_replace:
            #assert self.has_propchanges
            pass


class FileChange(NodeChange):
    def __init__(self, **kwds):
        NodeChange.__init__(self, **kwds)
        self.__kwds = kwds
        self.__base_checksum = None
        self.__text_checksum = None
        self.__apply_textdelta_count = itertools.count(1)
        self.__has_text_changed = False

    @property
    @memoize
    def filesize(self):
        return svn.fs.file_length(self.root, self.path, self.changeset.pool)

    @property
    def is_root(self):
        return False

    @property
    def is_subtree(self):
        return True

    @property
    def root_details(self):
        return self.parent.root_details

    def collect_mergeinfo_propchanges_forward(self, mi):
        if self.has_mergeinfo_propchange:
            mi.append((self, self.get_propchange(SVN_PROP_MERGEINFO)))

    def collect_mergeinfo_forward(self, mi):
        pl = self.proplist
        if SVN_PROP_MERGEINFO in pl:
            mi.append((self, pl[SVN_PROP_MERGEINFO]))

    def collect_parent_replacements(self, pr):
        if not self.parent.is_changeset:
            self.parent.collect_parent_replacements(pr)

    def find_first_copy_or_rename_parent(self):
        if not self.parent.is_changeset:
            return self.parent.find_first_copy_or_rename_parent()
        else:
            return None

    def collect_parents(self, parents):
        if self.parent.is_changeset:
            parents.append(self.parent)
        else:
            self.collect_parents(parents)

    @property
    def root(self):
        return self.parent.root

    @property
    def merge_root(self):
        return None if self.parent.is_changeset else self.parent.merge_root

    @property
    def base_checksum(self):
        return self.__base_checksum

    @property
    def text_checksum(self):
        return self.__text_checksum

    @property
    def is_file(self):
        return True

    @property
    def is_dir(self):
        return False

    @property
    def node_kind(self):
        return svn_node_file

    @property
    def node_type(self):
        return 'file'

    @property
    def has_text_changed(self):
        return self.__has_text_changed

    def _apply_textdelta(self, base_checksum):
        assert self.__apply_textdelta_count.next() == 1
        self.__base_checksum = base_checksum
        self.__has_text_changed = True
        if not self.is_change:
            self.change_type = ChangeType.Modify

    def _close(self, text_checksum):
        NodeChange._close(self)
        self.__text_checksum = text_checksum
        if not self.is_change:
            # Meh, seems like _close() is getting called against files that
            # were opened but never had apply_textdelta called against them.
            self.change_type = ChangeType.Modify

        #if self.is_modify:
        #    assert self.has_text_changed or self.has_propchanges

class ChangeSet(AbstractChangeSet):

    def __init__(self, repo_path, rev_or_txn, options=Options()):
        self.__repo_path = os.path.abspath(repo_path)
        self.__rev_or_txn = rev_or_txn
        self.__options = options

        self.entered = False
        self.exited  = False

        self.__roots = dict()

        self.__fs = None
        self.__root = None
        self.__revprops = None
        self.__base_root = None

        self._nada = dict()
        self._copy = dict()
        self._create = dict()
        self._modify = dict()
        self._remove = dict()
        self._rename = dict()
        self._replace = dict()
        self._copied_from = dict()
        self._renamed_from = dict()

        self._quirky_adds = list()
        self._quirky_removes = list()

        self.__change_type = ChangeType.Nada

        self._all_changes = dict()
        self.__all_propchanges = dict()
        self.__all_propreplacements = dict()

        self.__has_analysed = False
        self.__analysis = None

        self.__analysis_time = None
        self.__analysis_end_time = None
        self.__analysis_start_time = None

        self.__closed = False
        self.__opened_root = False

        self.__load_time = None
        self.__load_end_time = None
        self.__load_start_time = None

        self.__commit_root_path = None
        self.__action_root = None
        self.__action_roots = None
        self.__action_root_logic_initialised = False

        self.__notes = dict()
        self.__errors = dict()
        self.__warnings = dict()

        self.__errors_with_confirmation_instructions = dict()

        self.__mergeinfo_propchanges = list()

        self.__pool = None

        self._tracker = None
        self._track_resource_usage = options.track_resource_usage
        if self._track_resource_usage:
            self._tracker = ResourceUsageTracker(self.__class__.__name__)
        else:
            self._tracker = DummyResourceUsageTracker()

        self._delete_entry_called = 0
        self._raw_deletes = list()
        self._indirect_copy_then_modify = list()
        self._removes_that_might_be_renames = list()

        self.__destroyed = None

        self.__possible_merge_sources = set()

        self.files_by_size = defaultdict(list)
        self.track_file_sizes = options.track_file_sizes
        if self.track_file_sizes:
            self.max_file_size_in_bytes = (
                try_int(options.max_file_size_in_bytes)
            )
            invalid = (
                not self.max_file_size_in_bytes or
                self.max_file_size_in_bytes <= 0
            )
            if invalid:
                self.track_file_sizes = False

        self.files_over_max_size = []

    @property
    def is_tag_create(self):
        return self.top.is_tag_create

    @property
    def is_tag_remove(self):
        return self.top.is_tag_remove

    @property
    def is_branch_create(self):
        return self.top.is_branch_create

    @property
    def is_branch_remove(self):
        return self.top.is_branch_remove

    @property
    def possible_merge_sources(self):
        return self.__possible_merge_sources

    def add_possible_merge_source(self, path, rev):
        if path[-1] != '/':
            path = path + '/'
        self.__possible_merge_sources.add((path, rev))

    def destroy(self):
        """
        Destroy a ChangeSet object, releasing all acquired resources.

        This method needs to be called before a ChangeSet object can be
        garbage collected.
        """
        # XXX TODO: this entire method is just horrid.  Basically, the initial
        # implementation of the ChangeSet class and various Change* subclasses
        # (AbstractChange, FileChange, DirectoryChange, etc) were rife with
        # circular links, because all child objects linked backed to their
        # parents (i.e. via self.parent).  (And by "initial implementation", I
        # mean "initial and still current implementation".)
        #
        # This prevented a ChangeSet and all its child objects from being
        # garbage collected.  Upon realizing the error of my ways, much
        # hacking was done to break the circular references so that objects
        # could be collected properly.
        #
        # This particular method is the biggest, ugliest artefact from that
        # hacking work.  It is almost certainly overkill (del'ing objects,
        # then setting them to None... say wha'?), but eh, in its current
        # form, warts and all, it works.  Call changeset.destroy(), and gc
        # will be able to clean up the object and all the children correctly.
        #
        # But, yeah, this whole approach should definitely get cleaned up when
        # ChangeSet and friends go in for their next refactoring service.

        assert not self.__destroyed
        self.__destroyed = True

        del self._nada
        del self._copy
        del self._create
        del self._modify
        del self._remove
        del self._replace
        del self._copied_from
        del self._renamed_from

        del self._raw_deletes
        del self._indirect_copy_then_modify
        del self._removes_that_might_be_renames

        del self.__all_propchanges
        del self.__all_propreplacements
        del self.__mergeinfo_propchanges

        del self.__notes
        del self.__errors
        del self.__warnings

        del self.__roots
        del self.__revprops

        del self.__fs
        del self.__ptr
        del self.__repo
        del self.__root
        del self.__baton
        del self.__base_root

        self._nada = None
        self._copy = None
        self._create = None
        self._modify = None
        self._remove = None
        self._rename = None
        self._replace = None
        self._copied_from = None
        self._renamed_from = None

        self.__all_propchanges = None
        self.__all_propreplacements = None
        self.__mergeinfo_propchanges = None

        self._raw_deletes = None
        self._indirect_copy_then_modify = None
        self._removes_that_might_be_renames = None

        self.__notes = None
        self.__errors = None
        self.__warnings = None

        self.__roots = None

        self.__fs = None
        self.__repo = None
        self.__root = None
        self.__revprops = None
        self.__base_root = None

        del self._tracker
        self._tracker = None

        for (k, c) in self._all_changes.items():
            c.unparent()
            c.destroy()
            del c

        for k in self._all_changes.keys():
            del self._all_changes[k]
        del self._all_changes
        self._all_changes = None

        if self.__pool is not None:
            self.__pool.destroy()
            self.__pool = None

        AbstractChangeSet.destroy(self)

        gc.collect()

    @property
    def fs(self):
        return self.__fs

    @property
    def repo(self):
        return self.__repo

    @property
    def root(self):
        return self.__root

    @property
    def base_root(self):
        return self.__base_root

    @property
    def repo_path(self):
        return self.__repo_path

    @property
    def options(self):
        return self.__options

    @property
    def rev_or_txn(self):
        return self.__rev_or_txn

    @property
    def revprops(self):
        return self.__revprops

    def __hash__(self):
        return id(self)

    def _track(self, msg):
        return self._tracker.track(msg)

    @property
    def id(self):
        return id(self)

    @property
    def pool(self):
        return self.__pool

    @track_resource_usage
    def load(self):

        AbstractChangeSet.__init__(self, path='/')

        self.__load_start_time = time.time()
        self.__pool = svn.core.Pool()
        self.__repo = svn.repos.open(self.repo_path, self.pool)
        self.__fs   = svn.repos.fs(self.repo)

        try:
            self.__rev = int(self.rev_or_txn)
            self.__is_rev = True
        except:
            assert isinstance(self.rev_or_txn, str)
            self.__is_rev = False
            self.__txn_name = self.rev_or_txn

        if self.is_rev:
            assert self.rev > 0
            self.__base_rev = self.rev - 1
            args = (self.fs, self.rev, self.pool)
            self.__root = svn.fs.revision_root(*args)
            self.__revprops = svn.fs.revision_proplist(*args)
        else:
            self.__txn = svn.fs.open_txn(self.fs, self.txn_name, self.pool)
            self.__root = svn.fs.txn_root(self.txn, self.pool)
            self.__revprops = svn.fs.txn_proplist(self.txn, self.pool)
            self.__base_rev = svn.fs.txn_base_revision(self.txn)

        self.__base_root = None
        if self.base_rev != -1:
            self.__base_root = self._get_root(self.base_rev)

        self.root_details = AbsoluteRootDetails

        (self.__ptr, self.__baton) = svn.delta.make_editor(self, self.pool)

        svn.repos.replay2(
            self.root,              # root
            '',                     # base_dir
            SVN_INVALID_REVNUM,     # low_water_mark
            True,                   # send_deltas
            self.__ptr,             # editor
            self.__baton,           # edit_baton
            None,                   # authz_read_func
            self.pool,              # pool
        )

    @property
    def log_msg(self):
        assert self.__closed
        return self.revprops.get('svn:log')

    @property
    def user(self):
        assert self.__closed
        return self.revprops.get('svn:author')

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

    def __ewn(self, *args):
        assert args and len(args) in (2, 3)
        args = list(args)
        t = args.pop(0)
        l = len(args)
        if l == 1:
            m = args[0]
            if '%' in m:
                m = m % self
            p = '/'
        else:
            (c, m) = args
            p = c.path
        t.setdefault(p, []).append(m)
        return (p, m)

    def error(self, *args, **kwds):
        k = DecayDict(kwds)
        c = k.get('confirm', '')
        k.assert_empty(self)
        (p, m) = self.__ewn(self.__errors, *args)
        if c:
            m = EVN_ERROR_CONFIRMATION_BLURB % (m, c)

        self.__errors_with_confirmation_instructions \
            .setdefault(p, [])                       \
            .append(m)

    def warn(self, *args):
        self.__ewn(self.__warnings, *args)

    def note(self, *args):
        self.__ewn(self.__notes, *args)

    @property
    def has_notes(self):
        return bool(self.__notes)

    @property
    def has_errors(self):
        return bool(self.__errors)

    @property
    def has_warnings(self):
        return bool(self.__warnings)

    @property
    def notes(self):
        return self.__notes

    @property
    def errors(self):
        return self.__errors

    @property
    def errors_with_confirmation_instructions(self):
        return self.__errors_with_confirmation_instructions

    @property
    def warnings(self):
        return self.__warnings

    @property
    def is_closed(self):
        return self.__closed

    @property
    def has_checked_modify_invariants(self):
        return self.__checked_modify_invariants

    def __getitem__(self, path):
        """
        Convenience method for directly accessing changes by path.
        """
        return self._all_changes[path]

    def _register_propchange(self, propchange):
        assert not propchange.is_replace
        self.__all_propchanges.setdefault(propchange.name, [])\
                              .append(propchange)
        if propchange.name == SVN_PROP_MERGEINFO:
            assert propchange.__class__ == MergeinfoPropertyChange
            self.__mergeinfo_propchanges.append(propchange)

    @property
    def has_merges(self):
        return (len(self.__mergeinfo_propchanges) > 0)

    @property
    def mergeinfo_propchanges(self):
        return self.__mergeinfo_propchanges

    def _register_propreplacement(self, propchange):
        assert propchange.is_replace
        self.__all_propreplacements.setdefault(propchange.name, [])\
                                   .append(propchange)

    def _add_propchange(self, propchange):
        AbstractChange._add_propchange(self, propchange)
        self._register_propchange(propchange)

    def get_all_changes(self):
        return dict(self._all_changes)

    def get_change_for_path(self, path):
        # Temporary workaround for __all_changes_by_path oddities.
        return self._create.get(path,                                        \
                    self._rename.get(path,                                   \
                        self._copy.get(path,                                 \
                            self._modify.get(path,                           \
                                self._remove.get(path,                       \
                                    self._nada.get(path)
                                )
                            )
                        )
                    )
                )

    def get_all_changes_for_path(self, path):
        return [
            c for c in (
                self._copy.get(path),
                self._create.get(path),
                self._modify.get(path),
                self._remove.get(path),
                self._rename.get(path),
                self._nada.get(path),
            ) if c is not None
        ]

    def get_all_changes_for_path(self, filter_=None):
        if filter_ is None:
            filter_ = lambda _: True
        return [
            c for c in chain(
                self._copy.values(),
                self._create.values(),
                self._modify.values(),
                self._remove.values(),
                self._rename.values(),
                self._nada.values(),
            ) if filter_(c)
        ]

    @property
    def all_propchanges(self):
        return dict(self.__all_propchanges)

    @property
    def all_mergeinfo_propchanges(self):
        return dict(
            (k, v) for (k, v) in self.__all_propchanges
                if k == SVN_PROP_MERGEINFO
        )

    @property
    def all_propreplacements(self):
        return dict(self.__all_propreplacements)

    @property
    def node_kind(self):
        return svn_node_dir

    @property
    def node_type(self):
        return 'dir'

    @property
    def is_dir(self):
        return True

    @property
    def base_rev(self):
        return self.__base_rev

    @property
    def action_root(self):
        assert self.__action_root_logic_initialised == True
        return self.__action_root

    @property
    def action_roots(self):
        assert self.__action_root_logic_initialised == True
        return self.__action_roots

    @property
    def commit_root_path(self):
        assert self.__closed == True
        assert self.__commit_root_path is not None
        return self.__commit_root_path

    @property
    def change_type(self):
        return self.__change_type

    @change_type.setter
    def change_type(self, value):
        assert not self.is_change
        assert value == ChangeType.Modify
        self.__change_type = value

    def __purge(self, change):
        assert change.is_remove
        del self._remove[change.path]
        parent = change.parent
        parent.remove(change)

    def replace(self, remove, change):
        assert remove.is_remove and remove.path in self._remove
        self.__purge(remove)
        self._replace[change.path] = change

    def rename(self, remove, rename):
        assert remove.is_remove and remove.path in self._remove
        assert rename.path not in self._rename
        if rename.path in self._copy:
            del self._copy[rename.path]
        self.__purge(remove)
        self._rename[rename.path] = rename
        self._renamed_from[rename.renamed_from_path] = rename

    def modify(self, change):
        assert change.is_modify and change.path not in self._modify
        if change.path in self._nada:
            del self._nada[change.path]
        self._modify[change.path] = change

    def __register(self, new):
        assert isinstance(new, NodeChange)
        assert not new.registered

        new_store = getattr(self, '_' + ChangeType[new.change_type].lower())
        assert new.path not in new_store
        new_store[new.path] = new

        if new.is_replace:
            assert not new.path in self._replace
            self._replace[new.path] = new

        if new.is_copy:
            self._copied_from.setdefault(new.copied_from_path, {})           \
                             .setdefault(new.copied_from_rev, [])            \
                                .append(new)
        elif new.is_rename:
            assert new.renamed_from_path not in self._renamed_from
            self._renamed_from[new.renamed_from_path] = new

        if not new.is_remove:
            self._all_changes[new.path] = new

        if not new.is_remove and new.is_file and self.track_file_sizes:
            size = new.filesize
            if size >= self.max_file_size_in_bytes:
                self.files_over_max_size.append(new)

        new.registered = True
        return new

    @property
    def is_changeset(self):
        return True

    def _get_proplist(self, path, rev=None):
        """
        Returns a dict() of properties, where keys represent property names
        and values are corresponding property values.  If @rev is None, the
        node's proplist in the current root (which is either a rev or a txn)
        is used.
        """
        root = self.root if rev is None else self._get_root(rev)
        return svn.fs.node_proplist(root, path, self.pool)

    def _get_root(self, rev):
        if rev not in self.__roots:
            self.__roots[rev] = svn.fs.revision_root(self.fs, rev, self.pool)
        return self.__roots[rev]

    def set_target_revision(self, rev):
        self.target_rev = rev
        if self.target_rev:
            if self.base_rev != -1:
                assert self.base_rev == self.target_rev-1

    def open_root(self, base_rev, pool):
        assert not self.__opened_root
        self.__opened_root = True
        assert base_rev == -1
        return self

    def delete_entry(self, path, revision, parent, pool):
        assert revision == -1
        path = '/' + path

        self._delete_entry_called += 1
        self._raw_deletes.append(path)

        base_path = path
        base_rev = self.base_rev
        node_kind = svn.fs.check_path(self.base_root, path, pool)
        if node_kind not in (svn_node_file, svn_node_dir):
            # You'd think we could assume that if delete_entry was being
            # invoked against a path, that path existed in our base rev.
            # Unfortunately, this is not the case.  Dodgy replacements
            # seem to screw the ordering of delta editor callbacks; if the
            # path doesn't exist in base rev, we *must* have existed in our
            # parent's copied_from_path@copied_from_rev.  (Or if our parent
            # isn't a change, the first parent/grandparent we find that is a
            # copy.)
            k = self._find_first_parent_copy(path, parent)
            node_kind = k.node_kind
            base_path = k.base_path
            base_rev  = k.base_rev
            parent    = k.parent
            del k

        is_dir = (node_kind == svn_node_dir)
        cls = DirectoryChange if is_dir else FileChange
        k = Dict()
        k.path = self._format_path(path, is_dir=is_dir)
        k.parent = parent
        k.changeset = self
        k.change_type = ChangeType.Remove
        k.removed_from_path = self._format_path(base_path, is_dir=is_dir)
        k.removed_from_rev  = base_rev
        k.removed_from_proplist = self._get_proplist(base_path, base_rev)

        self.__register(cls(**k))

    def _find_first_parent_copy(self, path, parent):
        args = (path, parent, (ChangeType.Copy,))
        return self.__find_first_parent_of_type(*args)

    def _find_first_parent_copy_or_rename(self, path, parent):
        args = (path, parent, (ChangeType.Copy, ChangeType.Rename))
        return self.__find_first_parent_of_type(*args)

    def __find_first_parent_of_type(self, path, parent, types):
        node_kind = base_path = base_rev = None
        dirs = list()
        while True:
            dirs.append(parent.path)
            if parent.is_changeset or parent.change_type in types:
                break
            parent = parent.parent

        assert not parent.is_changeset
        assert parent.change_type in types
        k = Dict()
        k.parent = parent
        k.base_name = os.path.basename(path)
        if parent.is_copy:
            k.base_rev = parent.copied_from_rev
            k.base_dir = parent.copied_from_path
        elif parent.is_rename:
            k.base_rev = parent.renamed_from_rev
            k.base_dir = parent.renamed_from_path
        else:
            raise UnexpectedCodePath

        (first, last) = (dirs[0], dirs[-1])
        k.base_subdir = first.replace(last, '')
        k.base_parent_path = k.base_dir + k.base_subdir
        k.base_path = k.base_parent_path + k.base_name

        base_root = self._get_root(k.base_rev)
        k.node_kind = svn.fs.check_path(base_root, k.base_path, self.pool)
        assert k.node_kind in (svn_node_file, svn_node_dir)
        return k

    def add_directory(self, path, parent, copied_from_path,
                      copied_from_rev, dir_pool):

        return self.__add_node(
            DirectoryChange,
            format_dir(path),
            parent,
            self._format_dir(copied_from_path),
            copied_from_rev,
        )

    def add_file(self, path, parent, copied_from_path,
                 copied_from_rev, file_pool):

        return self.__add_node(
            FileChange,
            format_file(path),
            parent,
            self._format_file(copied_from_path),
            copied_from_rev,
        )

    def __add_node(self, *args):
        (cls, path, parent, copied_from_path, copied_from_rev) = args
        k = Dict()
        k.path = path
        k.parent = parent
        if not copied_from_path:
            k.change_type = ChangeType.Create
        else:
            k.change_type = ChangeType.Copy
            k.copied_from_path = copied_from_path
            k.copied_from_rev  = copied_from_rev
            k.copied_from_proplist = self._get_proplist(
                copied_from_path,
                copied_from_rev
            )

        k.changeset = self
        return self.__register(cls(**k))

    def change_dir_prop(self, change, name, value, pool):
        change._change_prop(name, value)

    def change_file_prop(self, change, name, value, pool):
        change._change_prop(name, value)

    def open_directory(self, path, parent, base_rev, dir_pool):
        assert base_rev == -1
        return self.__register(
            DirectoryChange(
                path=self._format_dir(path),
                parent=parent,
                changeset=self,
                change_type=ChangeType.Nada,
            )
        )

    def open_file(self, path, parent, base_rev, file_pool):
        assert base_rev == -1
        return self.__register(
            FileChange(
                path=self._format_file(path),
                parent=parent,
                changeset=self,
                change_type=ChangeType.Nada,
            )
        )

    def apply_textdelta(self, change, base_checksum):
        return change._apply_textdelta(base_checksum)

    def __removes_for_path(self, path):
        return [ r for r in self._remove.values() if path == r.path ]

    @property
    def __copies_that_are_possibly_renames(self):
        copies = [
            c for c in self._copy.values() if (
                c.copied_from_path != c.path and
                c.copied_from_rev  == self.base_rev
            )
        ]
        return (c for c in copies if c.is_copy)

    @track_resource_usage
    def _close(self):
        assert not self.__closed

        # Take a copy of our _remove and _copy dicts before we start messing
        # with them; they can be very handy during debugging.
        self._old_remove = dict(self._remove)
        self._old_copy   = dict(self._copy)

        # Find all renames via replacements and convert them accordingly.
        for copy in self.__copies_that_are_possibly_renames:
            path = copy.path
            old_path = copy.copied_from_path
            for rename in self.__removes_for_path(old_path):
                for replace in self.__removes_for_path(path):
                    replace.replacement = copy
                    rename.rename = copy
                    assert path in self._rename
                    assert path in self._replace
                    assert path not in self._copy
                    assert path not in self._remove
                    assert old_path not in self._remove
                    assert old_path in self._renamed_from

                    change = self._rename[path]
                    assert change == copy
                    assert change.is_rename
                    assert change.is_replace

        # Now that we've handled pesky renames via replacements, we're free to
        # enumerate over all our removes and identify those that are renames
        # or replacements (but not both, 'cause we handled those above).
        for (path, remove) in self._remove.items():

            copy = self._copy.get(path)
            create = self._create.get(path)
            modify = self._modify.get(path)

            if copy is not None:
                assert create is None and modify is None
                remove.replacement = copy
            elif create is not None:
                assert modify is None
                remove.replacement = create
            elif modify is not None:
                remove.replacement = modify
            else:
                # No paths were affected with the exact same path as the one
                # removed, so let's look for renames.  We do this by checking
                # whether or not the removed path exists in our copied_from
                # store.  This store is a little different from the others in
                # that it's a two tier dict; the first level maps paths to a
                # second level of dicts that map the copied_from_rev to a list
                # of change objects.  This is because a given path could be
                # copied_from more than once in a single changeset.  We only
                # consider a change a rename if there's a single copied_from
                # entry for the same node id.  If the node id doesn't match,
                # or there are multiple copies for the same node id, we don't
                # consider it a rename.
                copies = self._copied_from.get(path, {}) \
                             .get(self.base_rev) or []

                if not copies:
                    # The path that was removed wasn't copied anywhere, so,
                    # this definitely isn't a rename.
                    continue

                if len(copies) > 1:
                    # If a path being removed has been copied multiple times,
                    # one of the copies *could* be a rename (from the user's
                    # perspective), but we have no way of discerning which one
                    # was the rename, so, *drum roll*, do nothing.
                    continue

                # If we get here, there's one copy that matches the exact
                # details of the remove, which means it's a rename.  Assert
                # that the copy-from info lines up and that the node ids are
                # related.
                copy = copies[0]
                assert path == copy.copied_from_path
                assert self.base_rev == copy.copied_from_rev

                with Pool(self.pool) as pool:
                    args = (self.base_root, path, pool)
                    rename_node_id = svn.fs.node_id(*args)
                    rid = svn.fs.node_id(self.base_root, path, pool)
                    cid = svn.fs.node_id(self.root, copy.path, pool)

                    # svn.fs.compare_ids() returns 0 for related nodes,
                    # 1 for equivalent and -1 for unrelated.  We're looking
                    # for either equivalent or related.
                    comparison = svn.fs.compare_ids(rid, cid)
                    assert comparison in (0, 1), \
                        "comp: %d, path: %s, rid: %s, cid: %s" % \
                            (comparison, path, rid, cid)

                    # Ok, we're definitely a rename.  Convert accordingly.
                    remove.rename = copy


        # Now we need to go through all our modifies and check if the path
        # actually existed in base_rev-1.  You'd think it would, eh?  You
        # know, given that it's a modify and all.  Unfortunately, the path
        # could exist in a subtree that's been copied/renamed at a much
        # higher level.  So, we go through all modify change types and force
        # them to identify their previous_path/previous_rev/previous_parent-
        # path values via the _check_modify_invariants() call...

        with self._track('_check_modify_invariants'):
            for change in self._modify.values():
                change._check_modify_invariants()

        # ....which means that NodeChange.previous_proplist() will work
        # properly for changes of type modify -- which is essential in this
        # next step, where we enumerate over all changes and tell them to
        # create relevant PropertyChange objects.
        with self._track('change._load_propchanges'):
            for change in self._all_changes.values():
                change._load_propchanges()

        # And then load our own propchanges.
        with self._track('_load_propchanges'):
            self._load_propchanges()

        # Thanks to the first step where we enumerate over all the removes,
        # by this stage, all the removes that were actually replacements or
        # renames have been, er, removed from self._remove, which means all
        # that should remain are legit removes against paths that we haven't
        # encountered yet.  ....which means they shouldn't exist in our all-
        # changes dict that's keyed by path.  The assert below is one of the
        # more important ones as it ensures our remove->(replace|rename)
        # logic (which is pretty complicated) is working properly.
        all_changes = dict(self.get_all_changes())
        for (path, remove) in self._remove.items():
            assert path not in all_changes
            self._all_changes[path] = remove

        # Final step: get rid of all the redundant placeholder directories.
        # We need to grab a copy of dirs as the __reduce() call may do some
        # reparenting, in which case, the set size will change mid-iteration,
        # which causes an exception to be raised.
        dirs = [ d for d in self.dirs ]
        for child in dirs:
            assert child.parent == self
            self.__reduce(child)

        # Determine the 'root' of the commit, defaulting to '/' if no common
        # root directory can be found.
        if self.has_dirs:
            paths = [ d.path for d in self.dirs ]
            self.__commit_root_path = get_root_path(paths)
        else:
            self.__commit_root_path = '/'

        self.__closed = True
        self.__process_action_roots()
        self.__load_end_time = time.time()
        self.__analyse()
        self.__cleanup()

    @property
    def _nocleanup(self):
        try:
            return (self.options.nocleanup == True)
        except AttributeError:
            return False

    @track_resource_usage
    def __cleanup(self):
        assert self.__closed is True and self.__analysis is not None

        if self._nocleanup:
            return

        # XXX TODO: everything below got commented out when we relocated our
        # cleanup logic to destroy().  We could probably deprecate __cleanup()
        # altogether.

        #del self._nada
        #del self._copy
        #del self._create
        #del self._modify
        #del self._remove
        #del self._replace
        #del self._copied_from
        #del self._renamed_from

        #del self.__roots

        #import rpdb
        #remote_debug = rpdb.Rdb()
        #remote_debug.set_trace()

        #self.__pool.destroy()

        #gc.collect()

    #@track_resource_usage
    def __process_action_roots(self):
        self.__action_roots = [
            ar for ar in self._all_changes.values()
                if ar.is_dir and ar.is_an_action_root
        ]
        if len(self.__action_roots) == 1:
            self.__action_root = self.__action_roots[0]

        self.__action_root_logic_initialised = True

    @property
    def load_time(self):
        if self.__load_time is None:
            assert self.__load_end_time is not None
            self.__load_time = '%.3fs' % (
                self.__load_end_time -
                self.__load_start_time
            )
        return self.__load_time

    @property
    def analysis_time(self):
        if self.__analysis_time is None:
            assert self.__analysis_end_time is not None
            self.__analysis_time = '%.3fs' % (
                self.__analysis_end_time -
                self.__analysis_start_time
            )
        return self.__analysis_time

    def __reduce(self, change):
        assert change.is_dir
        if not change.is_change:
            if change.is_empty:
                change.parent.remove(change)
            elif change.has_dirs:
                dirs = [ d for d in change.dirs ]
                for child in dirs:
                    if child not in change:
                        continue
                    child.reparent(change.parent)
                    if change in change.parent:
                        change.parent.remove(change)

                    self.__reduce(child)
        else:
            dirs = [ d for d in change.dirs ]
            for child in dirs:
                if child in change:
                    self.__reduce(child)

    def close_directory(self, change):
        change._close()

    def close_file(self, change, text_checksum):
        change._close(text_checksum)

    def _build_repr(self):
        r = (
            AbstractChange._build_repr(self) +
            AbstractChangeSet._build_repr(self)
        )
        r.append(("commit_root", self.commit_root_path))
        if self.__action_root_logic_initialised:
            if self.action_roots:
                l = len(self.action_roots)
                assert l >= 1
                if l == 1:
                    assert self.action_root
                    r.append(("action_root", self.action_root.path))
                    action_type = ChangeType[self.action_root.change_type]
                    r.append(("action_type", action_type))
                else:
                    r.append(("action_roots", str(l)))
        return r

    def __repr__(self):
        if not self.is_closed:
            return '<ChangeSet(<...>)>'
        else:
            return AbstractChange.__repr__(self)

    @track_resource_usage
    def __analyse(self):
        assert self.__analysis is None
        self.__analysis_start_time = time.time()
        k = Dict()
        k.change_count = len(self._all_changes)
        k.notes = self.notes
        k.errors = self.errors
        k.warnings = self.warnings

        k.load_time = self.load_time
        if self._replace:
            k.replace = True

        if SVN_PROP_MERGEINFO in self.__all_propchanges:
            k.mergeinfo = True

        k.commit_root = self.commit_root_path
        k.user = self.revprops.get(SVN_PROP_REVISION_AUTHOR, '<noauthor>')

        if self.action_roots:
            l = len(self.action_roots)
            assert l >= 1
            if l == 1:
                assert self.action_root
                k.action_root = self.action_root.path
                k.action_type = ChangeType[self.action_root.change_type]
            else:
                k.action_root_count = l

        self.__analysis_end_time = time.time()
        k.analysis_time = self.analysis_time
        self.__analysis = ChangeSetAnalysis(**k)

    @property
    def analysis(self):
        if not self.__opened_root:
            assert not self.__closed
            # Didn't think it was possible, but we've run into commits that
            # have absolutely no changes contained within them.  The initial
            # open_root() doesn't get called by svn.repos.replay2, which means
            # _close() never gets called, which means __analyse() never gets
            # called, which means we need to mock up a dummy analysis object
            # now.
            self.__analysis = ChangeSetAnalysis(
                change_count='0',
                load_time='0.000s',
                analysis_time='0.000s',
                commit_root=None,
                user=self.revprops.get(SVN_PROP_REVISION_AUTHOR, '<noauthor>')
            )
        assert self.__analysis is not None
        return self.__analysis

class ChangeSetAnalysis(object):
    def __init__(self, **kwds):
        k = DecayDict(kwds)
        self.change_count = k.change_count
        self.notes = k.get('notes')
        self.errors = k.get('errors')
        self.warnings = k.get('warnings')
        self.replace = k.get('replace')
        self.mergeinfo = k.get('mergeinfo')
        self.load_time = k.load_time
        self.analysis_time = k.analysis_time
        self.commit_root = k.commit_root
        self.action_root = k.get('action_root')
        if not self.action_root:
            self.action_root_count = k.get('action_root_count')
        else:
            self.action_type = k.action_type
        self.user = k.user
        k.assert_empty(self)

    @property
    def one_liner(self):
        return self.__get_one_liner()

    def __get_one_liner(self, is_repr=False):
        def n(s):
            try:
                if getattr(self, s) is not None:
                    return s
                else:
                    return None
            except AttributeError:
                return None

        def p(s):
            try:
                return str(getattr(self, s)) or None
            except AttributeError:
                return None

        def v(s):
            try:
                a = getattr(self, s)
                if a:
                    return '%s=%s' % (s, str(a))
                else:
                    return None
            except AttributeError:
                return None

        # Heh, so hacky.
        if is_repr:
            p = v
            n = v

        r = [
            p('load_time'),
            p('change_count'),
            p('user'),
            n('mergeinfo'),
            n('replace'),
            v('commit_root'),
            v('action_root'),
            v('action_type'),
            v('action_root_count'),
            v('notes'),
            v('errors'),
            v('warnings'),
        ]

        return ','.join(v for v in r if v)

    def __repr__(self):
        return '<%s(%s)>' % (
            self.__class__.__name__,
            self.__get_one_liner(is_repr=True).replace(',', ', ')
        )

# vim:set ts=8 sw=4 sts=4 tw=78 et:
