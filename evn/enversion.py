#!/usr/bin/env python
"""
enversion.py: Enterprise Subversion Python Library.
"""
#=============================================================================
# Futures
#=============================================================================
from __future__ import with_statement

#=============================================================================
# Imports
#=============================================================================
import sys
IS_25 = sys.version_info[:2] == (2, 5)

import os
import gc
import re
import pdb
import stat
import time
import shutil
import socket
import pickle
import psutil
import inspect
import logging
import datetime
import optparse
import tempfile
import traceback
import itertools
import cStringIO as StringIO
import subprocess
import logging as log
from abc import ABCMeta, abstractmethod, abstractproperty
from glob import glob, iglob
from textwrap import dedent
from itertools import chain, repeat, count
from functools import wraps
from collections import namedtuple

from pprint import pprint, pformat
import ConfigParser as configparser
ConfigParser = configparser.RawConfigParser

#remote_debug = rpdb.Rdb()
#remote_debug.set_trace()

def __init_svn_libraries(g):
    import svn
    import svn.fs
    import svn.ra
    import svn.core
    import svn.delta
    import svn.repos
    import svn.client

    from svn.core import SVN_AUTH_PARAM_DEFAULT_USERNAME
    from svn.core import SVN_PROP_EXTERNALS
    from svn.core import SVN_PROP_MERGEINFO
    from svn.core import SVN_PROP_REVISION_AUTHOR
    from svn.core import SVN_INVALID_REVNUM

    from svn.core import svn_auth_open
    from svn.core import svn_auth_set_parameter
    from svn.core import svn_auth_get_username_provider

    from svn.core import svn_mergeinfo_diff
    from svn.core import svn_mergeinfo_parse
    from svn.core import svn_rangelist_to_string

    from svn.core import svn_node_dir
    from svn.core import svn_node_file
    from svn.core import svn_node_none
    from svn.core import svn_node_unknown

    from svn.core import SubversionException

    g['svn'] = svn
    #g['svn.fs'] = svn.fs
    #g['svn.ra'] = svn.ra
    #g['svn.core'] = svn.core
    #g['svn.delta'] = svn.delta
    #g['svn.repos'] = svn.repos
    #g['svn.client'] = svn.client
    g['SVN_AUTH_PARAM_DEFAULT_USERNAME'] = SVN_AUTH_PARAM_DEFAULT_USERNAME
    g['SVN_PROP_EXTERNALS'] = SVN_PROP_EXTERNALS
    g['SVN_PROP_MERGEINFO'] = SVN_PROP_MERGEINFO
    g['SVN_PROP_REVISION_AUTHOR'] = SVN_PROP_REVISION_AUTHOR
    g['SVN_INVALID_REVNUM'] = SVN_INVALID_REVNUM
    g['svn_auth_open'] = svn_auth_open
    g['svn_auth_set_parameter'] = svn_auth_set_parameter
    g['svn_auth_get_username_provider'] = svn_auth_get_username_provider
    g['svn_mergeinfo_diff'] = svn_mergeinfo_diff
    g['svn_mergeinfo_parse'] = svn_mergeinfo_parse
    g['svn_rangelist_to_string'] = svn_rangelist_to_string
    g['svn_node_dir'] = svn_node_dir
    g['svn_node_file'] = svn_node_file
    g['svn_node_none'] = svn_node_none
    g['svn_node_unknown'] = svn_node_unknown

    g['svn_node_types'] = (
        svn_node_dir,
        svn_node_file,
        svn_node_none,
        svn_node_unknown,
    )

    g['SubversionException'] = SubversionException

def init_svn_libraries(g=None):
    failed = True
    if g is None:
        g = globals()
    try:
        __init_svn_libraries(g)
        failed = False
    except ImportError as e:
        pass

    if not failed:
        return

    msg = dedent("""\
        failed to import Python Subversion bindings.

        Make sure Python Subversion bindings are installed before continuing.

        If you *have* installed the bindings, your current shell environment
        isn't configured correctly.  You need to alter either your env vars
        (i.e. PATH, PYTHONPATH) or Python installation (lib/site-packages/
        svn-python.pth) such that the libraries can be imported.

        Re-run this command once you've altered your environment to determine
        if you've fixed the problem.  Alternatively, you can simply run the
        following from the command line:

            python -c 'from svn import core'

        If that doesn't return an error, the problem has been fixed.

        Troubleshooting tips:

            1. Is the correct Python version accessible in your PATH?  (Type
               'which python' to see which version is getting picked up.  If
               it is incorrect, alter your PATH accordingly.)

            2. Have the Python Subversion bindings been installed into the
               site-packages directory of the Python instance referred to
               above?  If they have, then this should work:

                    % python -c 'from svn import core'

               ....but it didn't work when we just tried it, so there is a
               problem with your Python site configuration.

            3. If the Python Subversion bindings have been installed into a
               different directory, there should be a file 'svn-python.pth'
               located in your Python 'lib/site-packages' directory that
               tells Python where to load the bindings from.

            4. If you know where the bindings are but can't alter your
               Python installation's site-packages directory, try setting
               PYTHONPATH instead.

            5. LDLIBRARYPATH needs to be set correctly on some platforms for
               Python to be able to load the Subversion bindings.
        """)

    raise ImportError(msg)

#=============================================================================
# Notes, Warnings and Errors
#=============================================================================

class _Notes(Constant):
    MergeinfoRemovedFromRepositoryRoot = 'svn:mergeinfo removed from repository root'
    SubtreeMergeinfoModified = 'subtree svn:mergeinfo modified'
    SubtreeMergeinfoRemoved = 'subtree svn:mergeinfo removed'
    Merge = 'merge'
    RootRemoved = 'root removed'
    ValidMultirootCommit = 'valid multi-root commit'
    MultipleUnknownAndKnowRootsVerifiedByExternals = 'multiple known and unknown roots verified by svn:externals'
    BranchRenamed = 'branch renamed'
    TrunkRelocated = 'trunk relocated'
    FileReplacedViaCopyDuringMerge = 'file replaced via copy during merge'
    FileUnchangedButParentCopyOrRenameBug = 'file is unchanged but there is a parent rename or copy action'
    DirUnchangedButParentCopyOrRenameBug = 'directory is unchanged but there is a parent rename or copy action'
    UnchangedFileDuringMerge = 'file unchanged during merge'
    UnchangedDirDuringMerge = 'dir unchanged during merge'

n = _Notes()

class _Warnings(Constant):
    KnownRootRemoved = 'known root removed'

w = _Warnings()

class _Errors(Constant):
    TagRenamed = 'tag renamed'
    TagModified = 'tag modified'
    MultipleUnknownAndKnownRootsModified = 'multiple known and unknown roots modified in the same commit'
    MixedRootNamesInMultiRootCommit = 'mixed root names in multi-root commit'
    MixedRootTypesInMultiRootCommit = 'mixed root types in multi-root commit'
    SubversionRepositoryCheckedIn = 'subversion repository checked in'
    MergeinfoAddedToRepositoryRoot = "svn:mergeinfo added to repository root '/'"
    MergeinfoModifiedOnRepositoryRoot = "svn:mergeinfo modified on repository root '/'"
    SubtreeMergeinfoAdded = 'svn:mergeinfo added to subtree'
    RootMergeinfoRemoved = 'svn:mergeinfo removed from root'
    DirectoryReplacedDuringMerge = 'directory replaced during merge'
    EmptyMergeinfoCreated = 'empty svn:mergeinfo property set on path'
    TagDirectoryCreatedManually = 'tag directory created manually'
    BranchDirectoryCreatedManually = 'branch directory created manually'
    BranchRenamedToTrunk = 'branch renamed to trunk'
    TrunkRenamedToBranch = 'trunk renamed to branch'
    TrunkRenamedToTag = 'trunk renamed to tag'
    BranchRenamedToTag = 'branch renamed to tag'
    BranchRenamedOutsideRootBaseDir = 'branch renamed to location outside root base dir'
    TagSubtreePathRemoved = 'tag subtree path removed'
    RenameAffectsMultipleRoots = 'rename affects multiple roots'
    UncleanRenameAffectsMultipleRoots = 'unclean rename affects multiple roots'
    MultipleRootsCopied = 'multiple roots copied'
    TagCopied = 'tag copied'
    UncleanCopy = 'unclean copy'
    FileRemovedFromTag = 'file removed from tag'
    CopyKnownRootSubtreeToValidAbsRootPath = 'copy known root subtree to valid absolute root path'
    MixedRootsNotClarifiedByExternals = 'multiple known and unknown roots in commit could not be clarified by svn:externals'
    CopyKnownRootToIncorrectlyNamedRootPath = 'known root copied to an incorrectly-named new root path'
    CopyKnownRootSubtreeToIncorrectlyNamedRootPath = 'known root subtree copied to incorrectly-named new root path'
    UnknownPathRenamedToIncorrectlyNamedNewRootPath = 'unknown path renamed incorrectly to new root path name'
    RenamedKnownRootToIncorrectlyNamedRootPath = 'renamed known root to incorrectly named root path'
    MixedChangeTypesInMultiRootCommit = 'mixed change types in multi-root commit'
    CopyKnownRootToKnownRootSubtree = 'copy known root to known root subtree'
    UnknownPathCopiedToIncorrectlyNamedNewRootPath = 'unknown path copied to incorrectly named new root path'
    RenamedKnownRootToKnownRootSubtree = 'renamed root to known root subtree'
    FileUnchangedAndNoParentCopyOrRename = 'file has no text or property changes, and no parent copy or rename actions can be found'
    DirUnchangedAndNoParentCopyOrRename = 'directory has not changed, and no parent copy or rename actions can be found'
    EmptyChangeSet = 'empty change set'
    RenameRelocatedPathOutsideKnownRoot = 'rename relocated path outside known root'
    TagRemoved = 'tag removed'
    CopyKnownRootToUnknownPath = 'known root copied to unknown path'
    CopyKnownRootSubtreeToInvalidRootPath = 'known root copied to invalid root path'
    NewRootCreatedByRenamingUnknownPath = 'new root created by renaming unknown path'
    UnknownPathCopiedToKnownRootSubtree = 'unknown path copied to known root subtree'
    NewRootCreatedByCopyingUnknownPath = 'new root created by copying unknown path'
    RenamedKnownRootToUnknownPath = 'known root renamed to unknown path'
    RenamedKnownRootSubtreeToUnknownPath = 'known root subtree renamed to unknown path'
    RenamedKnownRootSubtreeToValidRootPath = 'known root subtree renamed to valid root path'
    RenamedKnownRootSubtreeToIncorrectlyNamedRootPath = 'known root subtree renamed to incorrectly-named root path'
    UncleanRename = 'unclean rename'
    PathCopiedFromOutsideRootDuringNonMerge = 'path copied from outside root during non-merge'
    UnknownDirReplacedViaCopyDuringNonMerge = 'unknown directory replaced via copy during non-merge'
    DirReplacedViaCopyDuringNonMerge = 'directory replaced via copy during non-merge'
    DirectoryReplacedDuringNonMerge = 'directory replaced during non-merge'
    PreviousPathNotMatchedToPathsInMergeinfo = 'previous path not matched to paths in mergeinfo'
    PreviousRevDiffersFromParentCopiedFromRev = 'previous rev differs from parent copied-from rev'
    PreviousPathDiffersFromParentCopiedFromPath = 'previous path differs from parent copied-from path'
    PreviousRevDiffersFromParentRenamedFromRev = 'previous rev differs from parent renamed-from rev'
    PreviousPathDiffersFromParentRenamedFromPath = 'previous path differs from parent renamed-from path'
    KnownRootPathReplacedViaCopy = 'known root path replaced via copy'
    BranchesDirShouldBeCreatedManuallyNotCopied = "'branches' directory should be created manually not copied"
    TagsDirShouldBeCreatedManuallyNotCopied = "'tags' directory should be created manually not copied"
    CopiedFromPathNotMatchedToPathsInMergeinfo = 'copied-from path not matched to paths in mergeinfo'
    InvariantViolatedModifyContainsMismatchedPreviousPath = 'invariant violated: modify contains mismatched previous path'
    InvariantViolatedModifyContainsMismatchedPreviousRev = 'invariant violated: modify contains mismatched previous path'
    InvariantViolatedCopyNewPathInRootsButNotReplace = "invariant violated: the new path name created (via copy) is already a known root, but the change isn't marked as a replace."
    MultipleRootsAffectedByRemove = 'multiple roots affected by remove'
    InvariantViolatedDieCalledWithoutErrorInfo = "invariant violated: Repository.die() method called without any error information being set"
    VersionMismatch = "version mismatch: we are at version %d, but the 'evn:version' revision property found on revision 0 reports the repository is at version %d"
    MissingOrEmptyRevPropOnRev0 = "missing or empty 'evn:%s' revision property on revision 0"
    InvalidIntegerRevPropOnRev0 = "invalid value for 'evn:%s' revision property on revision 0; expected an integer greater than or equal to %d, got: %s"
    PropertyValueConversionFailed = "failed to convert property %s's value: %s"
    PropertyValueLiteralEvalFailed = "invalid value for property '%s': %s"
    LastRevTooHigh = "the value for the revision property 'evn:last_rev' on revision 0 of the repository is too high; it indicates the last processed revision was %d, however, the highest revision in the repository is only %d"
    RepositoryOutOfSyncTxn = "the repository is out of sync and can not be committed to at this time (base revision for this transaction: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    LastRevNotSetToBaseRevDuringPostCommit = "the repository is out of sync (last_rev is not set to base_rev during post-commit), preventing post-commit processing of this revision; is the pre-commit hook enabled? (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    OutOfOrderRevisionProcessingAttempt = "unable to process repository revision %d until the base revision %d has been processed; however, the last processed revision reported by the repository is %d (current repository revision: %d)"
    RootsMissingFromBaseRevTxn = "missing or empty 'evn:roots' revision property on base revision (this transaction: %s, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    RootsMissingFromBaseRevDuringPostCommit = "missing or empty 'evn:roots' revision property on base revision, preventing post-commit processing of this revision; is the pre-commit hook enabled? (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    ChangeSetOnlyApplicableForRev1AndHigher = "changeset only applicable to revisions 1 and higher"
    InvalidRootsForRev = "invalid value for 'evn:roots' revision property on revision (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    StaleTxnProbablyDueToHighLoad = "please re-try your commit -- the repository is under load and your transaction became out-of-date while it was being queued for processing (base revision for this transaction: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    AbsoluteRootOfRepositoryCopied = "absolute root of repository copied"
    PropertyChangedButOldAndNewValuesAreSame = "the property '%s' is recorded as having changed, but the old value and new value are identical ('%s')"

e = _Errors()

#=============================================================================
# Constants
#=============================================================================


#=============================================================================
# Process ID Testing (hacky)
#=============================================================================
def pid_exists(pid):
    if os.name == 'nt':
        import psutil
        return psutil.pid_exists(pid)
    else:
        try:
            os.kill(pid, 0)
        except OSError as e:
            import errno
            if e.errno == errno.ESRCH:
                return False
            else:
                raise
        else:
            return True

# Force a test during module loading in order to catch any issues up-front.
assert pid_exists(os.getpid())

#=============================================================================
# Aliases, Globals
#=============================================================================

PIPE = subprocess.PIPE
Popen = subprocess.Popen

svnwc = None
global verbose
verbose = os.getenv('ESVN_VERBOSE') == '1'

class UnexpectedCodePath(RuntimeError):
    pass


#=============================================================================
# Helper Classes
#=============================================================================

#=============================================================================
# Main
#=============================================================================

def main():
    CLI(sys.argv[1:])

if __name__ == '__main__':
    main()


# vi:set ts=8 sw=4 sts=4 expandtab tw=78:
