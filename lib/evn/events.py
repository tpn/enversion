#===============================================================================
# Imports
#===============================================================================
import os
import sys

from evn.event import (
    Event,
    EventType,
)

#===============================================================================
# Helpers
#===============================================================================
def get_next_event_id():
    """
    Get the next ID number to be used for a new event.

    This is a simple helper method intended to be used when adding new events.
    It reads the contents of this file, finds the highest ID being used (simply
    by looking for strings that start with '    _id_ = ', then returns one
    higher than that number.

    .. tip:: calling python against this file directly will run this method
             and print out the next highest ID to use for a new event.
    """
    n = os.path.abspath(__file__.replace('.pyc', '.py'))
    with open(n, 'r') as f:
        text = f.read()

    highest = None
    for line in text.splitlines():
        if not line.startswith('    _id_ ='):
            continue

        num = int(line[line.rfind('=')+2:])
        if num > highest:
            highest = num

    return highest + 1

def check_event_id_invariants():
    """
    This method enforces the following invariants:
        - All events defined in this file (events.py) use a unique ID.
        - The '    _id_ = n' line comes directly after the class definition.
        - All lines are <= 80 characters.

    This method is called every time this file is loaded/reloaded.
    """
    n = os.path.abspath(__file__.replace('.pyc', '.py'))
    with open(n, 'r') as f:
        text = f.read()

    seen = dict()
    classname = None
    id_should_be_on_next_line = False

    for (lineno, line) in enumerate(text.splitlines()):
        assert len(line) <= 80, "lineno: %d, len: %d" % (lineno, len(line))
        if line.startswith('class '):
            classname = line[6:line.rfind('(')]
            id_should_be_on_next_line = True

        elif line.startswith('    _id_ ='):
            id_should_be_on_next_line = False
            num = int(line[line.rfind('=')+2:])
            if num in seen:
                error = (
                    'error: duplicate ID detected for %d:\n'
                    '    line: %d, class: %s\n'
                    '    line: %d, class: %s\n' % (
                        num,
                        seen[num][0],
                        seen[num][1],
                        lineno,
                        classname,
                    )
                )
                raise RuntimeError(error)
            else:
                seen[num] = (lineno, classname)

        elif id_should_be_on_next_line:
            error = (
                "error: class '%s' has not been defined properly, "
                "was expecting '_id_' to be defined on line %d, but "
                "saw '%s' instead." % (
                    classname,
                    lineno,
                    line,
                )
            )
            raise RuntimeError(error)


check_event_id_invariants()

#===============================================================================
# Note
#===============================================================================
class MergeinfoRemovedFromRepositoryRoot(Event):
    _id_ = 1
    _type_ = EventType.Note

class SubtreeMergeinfoModified(Event):
    _id_ = 2
    _type_ = EventType.Note

class SubtreeMergeinfoRemoved(Event):
    _id_ = 3
    _type_ = EventType.Note

class Merge(Event):
    _id_ = 4
    _type_ = EventType.Note

class RootRemoved(Event):
    _id_ = 5
    _type_ = EventType.Note

class ValidMultirootCommit(Event):
    _id_ = 6
    _type_ = EventType.Note
    _desc_ = "valid multi-root commit"

class MultipleUnknownAndKnowRootsVerifiedByExternals(Event):
    _id_ = 7
    _type_ = EventType.Note
    _desc_ = "multiple known and unknown roots verified by svn:externals"

class BranchRenamed(Event):
    _id_ = 8
    _type_ = EventType.Note

class TrunkRelocated(Event):
    _id_ = 9
    _type_ = EventType.Note

class FileReplacedViaCopyDuringMerge(Event):
    _id_ = 10
    _type_ = EventType.Note

class FileUnchangedButParentCopyOrRenameBug(Event):
    _id_ = 11
    _type_ = EventType.Note
    _desc_ = "file is unchanged but there is a parent rename or copy action"

class DirUnchangedButParentCopyOrRenameBug(Event):
    _id_ = 12
    _type_ = EventType.Note
    _desc_ = (
        "directory is unchanged but there is a parent rename or copy action"
    )

class UnchangedFileDuringMerge(Event):
    _id_ = 13
    _type_ = EventType.Note
    _desc_ = "file unchanged during merge"

class UnchangedDirDuringMerge(Event):
    _id_ = 14
    _type_ = EventType.Note
    _desc_ = "dir unchanged during merge"

#===============================================================================
# Confirm
#===============================================================================
class KnownRootRemoved(Event):
    _id_ = 15
    _type_ = EventType.Warn

#===============================================================================
# Warn
#===============================================================================
class TagRenamed(Event):
    _id_ = 16
    _type_ = EventType.Warn

class TagModified(Event):
    _id_ = 17
    _type_ = EventType.Warn

class MultipleUnknownAndKnownRootsModified(Event):
    _id_ = 18
    _type_ = EventType.Warn
    _desc_ = "multiple known and unknown roots modified in the same commit"

class MixedRootNamesInMultiRootCommit(Event):
    _id_ = 19
    _type_ = EventType.Warn
    _desc_ = "mixed root names in multi-root commit"

class MixedRootTypesInMultiRootCommit(Event):
    _id_ = 20
    _type_ = EventType.Warn
    _desc_ = "mixed root types in multi-root commit"

class SubversionRepositoryCheckedIn(Event):
    _id_ = 21
    _type_ = EventType.Warn

class MergeinfoAddedToRepositoryRoot(Event):
    _id_ = 22
    _type_ = EventType.Warn
    _desc_ = "svn:mergeinfo added to repository root '/'"

class MergeinfoModifiedOnRepositoryRoot(Event):
    _id_ = 23
    _type_ = EventType.Warn
    _desc_ = "svn:mergeinfo modified on repository root '/'"

class SubtreeMergeinfoAdded(Event):
    _id_ = 24
    _type_ = EventType.Warn
    _desc_ = "svn:mergeinfo added to subtree"

class RootMergeinfoRemoved(Event):
    _id_ = 25
    _type_ = EventType.Warn
    _desc_ = "svn:mergeinfo removed from root"

class DirectoryReplacedDuringMerge(Event):
    _id_ = 26
    _type_ = EventType.Warn

class EmptyMergeinfoCreated(Event):
    _id_ = 27
    _type_ = EventType.Warn
    _desc_ = "empty svn:mergeinfo property set on path"

class MultipleRootsAffectedByRemove(Event):
    _id_ = 28
    _type_ = EventType.Warn

#===============================================================================
# Error
#===============================================================================
class TagDirectoryCreatedManually(Event):
    _id_ = 29
    _type_ = EventType.Error

class BranchDirectoryCreatedManually(Event):
    _id_ = 30
    _type_ = EventType.Error

class BranchRenamedToTrunk(Event):
    _id_ = 31
    _type_ = EventType.Error

class TrunkRenamedToBranch(Event):
    _id_ = 32
    _type_ = EventType.Error

class TrunkRenamedToTag(Event):
    _id_ = 33
    _type_ = EventType.Error

class BranchRenamedToTag(Event):
    _id_ = 34
    _type_ = EventType.Error

class BranchRenamedOutsideRootBaseDir(Event):
    _id_ = 35
    _type_ = EventType.Error
    _desc_ = "branch renamed to location outside root base dir"

class TagSubtreePathRemoved(Event):
    _id_ = 36
    _type_ = EventType.Error

class RenameAffectsMultipleRoots(Event):
    _id_ = 37
    _type_ = EventType.Error

class UncleanRenameAffectsMultipleRoots(Event):
    _id_ = 38
    _type_ = EventType.Error

class MultipleRootsCopied(Event):
    _id_ = 39
    _type_ = EventType.Error

class TagCopied(Event):
    _id_ = 40
    _type_ = EventType.Error

class UncleanCopy(Event):
    _id_ = 41
    _type_ = EventType.Error

class FileRemovedFromTag(Event):
    _id_ = 42
    _type_ = EventType.Error

class CopyKnownRootSubtreeToValidAbsRootPath(Event):
    _id_ = 43
    _type_ = EventType.Error
    _desc_ = "copy known root subtree to valid absolute root path"

class MixedRootsNotClarifiedByExternals(Event):
    _id_ = 44
    _type_ = EventType.Error
    _desc_ = (
        "multiple known and unknown roots in commit could not be "
        "clarified by svn:externals"
    )

class CopyKnownRootToIncorrectlyNamedRootPath(Event):
    _id_ = 45
    _type_ = EventType.Error
    _desc_ = "known root copied to an incorrectly-named new root path"

class CopyKnownRootSubtreeToIncorrectlyNamedRootPath(Event):
    _id_ = 46
    _type_ = EventType.Error
    _desc_ = "known root subtree copied to incorrectly-named new root path"

class UnknownPathRenamedToIncorrectlyNamedNewRootPath(Event):
    _id_ = 47
    _type_ = EventType.Error
    _desc_ = "unknown path renamed incorrectly to new root path name"

class RenamedKnownRootToIncorrectlyNamedRootPath(Event):
    _id_ = 48
    _type_ = EventType.Error

class MixedChangeTypesInMultiRootCommit(Event):
    _id_ = 49
    _type_ = EventType.Error
    _desc_ = "mixed change types in multi-root commit"

class CopyKnownRootToKnownRootSubtree(Event):
    _id_ = 50
    _type_ = EventType.Error

class UnknownPathCopiedToIncorrectlyNamedNewRootPath(Event):
    _id_ = 51
    _type_ = EventType.Error

class RenamedKnownRootToKnownRootSubtree(Event):
    _id_ = 52
    _type_ = EventType.Error
    _desc_ = "renamed root to known root subtree"

class FileUnchangedAndNoParentCopyOrRename(Event):
    _id_ = 53
    _type_ = EventType.Error
    _desc_ = (
        "file has no text or property changes, and no parent copy or rename "
        "actions can be found"
    )

class DirUnchangedAndNoParentCopyOrRename(Event):
    _id_ = 54
    _type_ = EventType.Error
    _desc_ = (
        "directory has not changed, and no parent copy or rename actions can "
        "be found"
    )

class EmptyChangeSet(Event):
    _id_ = 55
    _type_ = EventType.Error

class RenameRelocatedPathOutsideKnownRoot(Event):
    _id_ = 56
    _type_ = EventType.Error

class TagRemoved(Event):
    _id_ = 57
    _type_ = EventType.Error

class CopyKnownRootToUnknownPath(Event):
    _id_ = 58
    _type_ = EventType.Error
    _desc_ = "known root copied to unknown path"

class CopyKnownRootSubtreeToInvalidRootPath(Event):
    _id_ = 59
    _type_ = EventType.Error
    _desc_ = "known root copied to invalid root path"

class NewRootCreatedByRenamingUnknownPath(Event):
    _id_ = 60
    _type_ = EventType.Error

class UnknownPathCopiedToKnownRootSubtree(Event):
    _id_ = 61
    _type_ = EventType.Error

class NewRootCreatedByCopyingUnknownPath(Event):
    _id_ = 62
    _type_ = EventType.Error

class RenamedKnownRootToUnknownPath(Event):
    _id_ = 63
    _type_ = EventType.Error
    _desc_ = "known root renamed to unknown path"

class RenamedKnownRootSubtreeToUnknownPath(Event):
    _id_ = 64
    _type_ = EventType.Error
    _desc_ = "known root subtree renamed to unknown path"

class RenamedKnownRootSubtreeToValidRootPath(Event):
    _id_ = 65
    _type_ = EventType.Error
    _desc_ = "known root subtree renamed to valid root path"

class RenamedKnownRootSubtreeToIncorrectlyNamedRootPath(Event):
    _id_ = 66
    _type_ = EventType.Error
    _desc_ = "known root subtree renamed to incorrectly-named root path"

class UncleanRename(Event):
    _id_ = 67
    _type_ = EventType.Error

class PathCopiedFromOutsideRootDuringNonMerge(Event):
    _id_ = 68
    _type_ = EventType.Error
    _desc_ = "path copied from outside root during non-merge"

class UnknownDirReplacedViaCopyDuringNonMerge(Event):
    _id_ = 69
    _type_ = EventType.Error
    _desc_ = "unknown directory replaced via copy during non-merge"

class DirReplacedViaCopyDuringNonMerge(Event):
    _id_ = 70
    _type_ = EventType.Error
    _desc_ = "directory replaced via copy during non-merge"

class DirectoryReplacedDuringNonMerge(Event):
    _id_ = 71
    _type_ = EventType.Error
    _desc_ = "directory replaced during non-merge"

class PreviousPathNotMatchedToPathsInMergeinfo(Event):
    _id_ = 72
    _type_ = EventType.Error
    _desc_ = "previous path not matched to paths in mergeinfo"

class PreviousRevDiffersFromParentCopiedFromRev(Event):
    _id_ = 73
    _type_ = EventType.Error
    _desc_ = "previous rev differs from parent copied-from rev"

class PreviousPathDiffersFromParentCopiedFromPath(Event):
    _id_ = 74
    _type_ = EventType.Error
    _desc_ = "previous path differs from parent copied-from path"

class PreviousRevDiffersFromParentRenamedFromRev(Event):
    _id_ = 75
    _type_ = EventType.Error
    _desc_ = "previous rev differs from parent renamed-from rev"

class PreviousPathDiffersFromParentRenamedFromPath(Event):
    _id_ = 76
    _type_ = EventType.Error
    _desc_ = "previous path differs from parent renamed-from path"

class KnownRootPathReplacedViaCopy(Event):
    _id_ = 77
    _type_ = EventType.Error

class BranchesDirShouldBeCreatedManuallyNotCopied(Event):
    _id_ = 78
    _type_ = EventType.Error
    _desc_ = "'branches' directory should be created manually not copied"

class TagsDirShouldBeCreatedManuallyNotCopied(Event):
    _id_ = 79
    _type_ = EventType.Error
    _desc_ = "'tags' directory should be created manually not copied"

class CopiedFromPathNotMatchedToPathsInMergeinfo(Event):
    _id_ = 80
    _type_ = EventType.Error
    _desc_ = "copied-from path not matched to paths in mergeinfo"

class InvariantViolatedModifyContainsMismatchedPreviousPath(Event):
    _id_ = 81
    _type_ = EventType.Error
    _desc_ = "invariant violated: modify contains mismatched previous path"

class InvariantViolatedModifyContainsMismatchedPreviousRev(Event):
    _id_ = 82
    _type_ = EventType.Error
    _desc_ = "invariant violated: modify contains mismatched previous path"

class InvariantViolatedCopyNewPathInRootsButNotReplace(Event):
    _id_ = 83
    _type_ = EventType.Error
    _desc_ = (
        "invariant violated: the new path name created (via copy) is already "
        "a known root, but the change isn't marked as a replace."
    )

class AbsoluteRootOfRepositoryCopied(Event):
    _id_ = 84
    _type_ = EventType.Error

class RootAncestorRenamedToKnownRootSubtree(Event):
    _id_ = 101
    _type_ = EventType.Fatal
    _desc_ = "root ancestor renamed to known-root subtree"

#===============================================================================
# Fatal
#===============================================================================
class InvariantViolatedDieCalledWithoutErrorInfo(Event):
    _id_ = 85
    _type_ = EventType.Fatal
    _desc_ = (
        "invariant violated: Repository.die() method called without any error "
        "information being set."
    )

class VersionMismatch(Event):
    _id_ = 86
    _type_ = EventType.Fatal
    _desc_ = (
        "version mismatch: we are at version %d, but the 'evn:version'"
        "revision property found on revision 0 reports the repository is at "
        "version %d"
    )

class MissingOrEmptyRevPropOnRev0(Event):
    _id_ = 87
    _type_ = EventType.Fatal
    _desc_ = "missing or empty 'evn:%s' revision property on revision 0"

class InvalidIntegerRevPropOnRev0(Event):
    _id_ = 88
    _type_ = EventType.Fatal
    _desc_ = (
        "invalid value for 'evn:%s' revision property on revision 0; "
        "expected an integer greater than or equal to %d, got: %s"
    )

class PropertyValueConversionFailed(Event):
    _id_ = 89
    _type_ = EventType.Fatal
    _desc_ = "failed to convert property %s's value: %s"

class PropertyValueLiteralEvalFailed(Event):
    _id_ = 90
    _type_ = EventType.Fatal
    _desc_ = "invalid value for property '%s': %s"

class LastRevTooHigh(Event):
    _id_ = 91
    _type_ = EventType.Fatal
    _desc_ = (
        "the value for the revision property 'evn:last_rev' on revision 0 "
        "of the repository is too high; it indicates the last processed "
        "revision was %d, however, the highest revision in the repository is "
        "only %d"
    )
    last_processed_rev = int
    high_rev_in_repo = int

class RepositoryOutOfSyncTxn(Event):
    _id_ = 92
    _type_ = EventType.Fatal
    _desc_ = (
        "the repository is out of sync and can not be committed to at this "
        "time (base revision for this transaction: %d, repository last "
        "synchronised at revision: %d, current repository revision: %d)"
    )

class LastRevNotSetToBaseRevDuringPostCommit(Event):
    _id_ = 93
    _type_ = EventType.Fatal
    _desc_ = (
        "the repository is out of sync (last_rev is not set to base_rev "
        "during post-commit), preventing post-commit processing of this "
        "revision; is the pre-commit hook enabled? (this revision: %d, "
        "base revision: %d, repository last synchronised at revision: %d, "
        "current repository revision: %d)"
    )

class OutOfOrderRevisionProcessingAttempt(Event):
    _id_ = 94
    _type_ = EventType.Fatal
    _desc_ = (
        "unable to process repository revision %d until the base revision "
        "%d has been processed; however, the last processed revision "
        "reported by the repository is %d (current repository revision: %d)"
    )

class RootsMissingFromBaseRevTxn(Event):
    _id_ = 95
    _type_ = EventType.Fatal
    _desc_ = (
        "missing or empty 'evn:roots' revision property on base revision "
        "(this transaction: %s, base revision: %d, repository last "
        "synchronised at revision: %d, current repository revision: %d)"
    )

class RootsMissingFromBaseRevDuringPostCommit(Event):
    _id_ = 96
    _type_ = EventType.Fatal
    _desc_ = (
        "missing or empty 'evn:roots' revision property on base revision, "
        "preventing post-commit processing of this revision; is the pre-"
        "commit hook enabled? (this revision: %d, base revision: %d, "
        "repository last synchronised at revision: %d, current repository "
        "revision: %d)"
    )

class ChangeSetOnlyApplicableForRev1AndHigher(Event):
    _id_ = 97
    _type_ = EventType.Fatal
    _desc_ = "changeset only applicable to revisions 1 and higher"

class InvalidRootsForRev(Event):
    _id_ = 98
    _type_ = EventType.Fatal
    _desc_ = (
        "invalid value for 'evn:roots' revision property on revision "
        "(this revision: %d, base revision: %d, repository last "
        "synchronised at revision: %d, current repository revision: %d)"
    )

class StaleTxnProbablyDueToHighLoad(Event):
    _id_ = 99
    _type_ = EventType.Fatal
    _desc_ = (
        "please re-try your commit -- the repository is under load and your "
        "transaction became out-of-date while it was being queued for "
        "processing (base revision for this transaction: %d, repository "
        "last synchronised at revision: %d, current repository revision: %d)"
    )

class PropertyChangedButOldAndNewValuesAreSame(Event):
    _id_ = 100
    _type_ = EventType.Fatal
    _desc_ = (
        "the property '%s' is recorded as having changed, but the old "
        "value and new value are identical ('%s')"
    )


#===============================================================================
# Main
#===============================================================================
if __name__ == '__main__':
    import sys
    sys.stdout.write('next event id: %d\n' % get_next_event_id())

# vim:set ts=8 sw=4 sts=4 tw=0 et:
