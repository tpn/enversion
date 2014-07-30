#===============================================================================
# Imports
#===============================================================================
from abc import (
    ABCMeta,
    abstractmethod,
)

from evn.util import (
    Constant,
)

class _EventType(Constant):
    """
    .. _events-toplevel:

    ======
    Events
    ======

    Event Types
    -----------

    .. _events-note:

        Note
        ----

        The original intent of notes was to mark commits that contained
        interesting or unexpected metadata that wasn't considered to be
        erroneous (i.e. the commit didn't need to be blocked).

        In practice, though, this information has never been consulted,
        mainly because there were no facilities provided to harvest notes
        into a form that could be easily understood.

        For this reason, notes may be deprecated in the future unless a
        compelling use case can be demonstrated (or sufficient 'note
        harvesting' facilities are provided).

        (That being said, notes are useful if you want to perform the
        ultimate demotion of any event (although demoting 'confirmations'
        is the most likely use case).)

    .. _events-confirm:

        Confirm
        -------

        Overridable by: anyone.

        This is a new event type that, when encountered, blocks the commit
        and provides a user with an explanation of what they're doing, why
        it's been blocked, and how to re-commit if they really want to do it.

        In that respect, it's identical to warnings below (with a slightly
        less confrontational error message). The only difference is that any
        repository user with read/write access can confirm the commit (i.e.
        it's not limited to repository admins).

        This event type is intended to catch common user errors that would
        benefit from an extra 'safety' check.

    .. _events-warn:

        Warn
        ----

        Overridable by: super-users, admins.

        Warnings now represent erroneous conditions that can be overridden by
        repository super-users (who can no longer override errors, see below).

        Out of the box, there is only one warning: known root removed. The
        rest are either errors or fatal - which can no longer be overridden by
        repository super-users.

        As errors can be re-mapped to warnings on a per-repository basis, this
        event type provides administrators with the facility to demote certain
        errors to warnings based on a comprehensive review of the team's
        SCM/Subversion usage.

    .. _events-error:

        Error
        -----

        Overridable by: admins, super-users (if an admin has explicitly
        allowed the error to be overridable in the repository's Enversion
        configuration)

        The vast majority of things that were considered errors in esvn.py
        will be brought straight over to evn.py as errors, too. The main
        difference is that repository super-users will now no longer be able
        to override errors by default.

        Errors that you want a super-user to be able to override should be
        demoted to warnings in the per-repository configuration file.

            .. note:: There has also been discussion of using some sort of a
                      token-based system as a backup.

    .. _events-fatal:

        Fatal
        -----

        A fatal event will block a commit, and it can't be overridden by
        anyone, including administrators. These events will be limited to a
        small subset of existing errors that deal with Enversion invariants
        being broken, or unexpected but catastrophic issues like runtime
        exceptions/assertions.

    """
    Note    = 1
    Confirm = 2
    Warn    = 3
    Error   = 4
    Fatal   = 5
EventType = _EventType()

class _Phase(Constant):
    ChangeSet                = 1
    ChangeSetMergeinfo       = 2
    ChangeSetRoots           = 3
    Change                   = 4
    ChangeMergeinfo          = 5

    Copy                     = 6
    Create                   = 7
    Modify                   = 8
    Remove                   = 9
    Rename                   = 10

    Replace                  = 11

    PropertyChange           = 12

    Merge                    = 13

Phase = _Phase()


class Event:
    __metaclass__ = ABCMeta
    @property
    def desc(self):
        return self._desc_
    description = desc

    @property
    def id(self):
        return self._id_

    @property
    def type(self):
        return self._type_

class RootEvent(Event):
    """
    An event that affects a root.

    """
    pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
