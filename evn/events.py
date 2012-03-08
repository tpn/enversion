
#=============================================================================
# Imports
#=============================================================================
from evn.event import (
    Event,
    EventType,
)

#=============================================================================
# Note
#=============================================================================
class MergeinfoRemovedFromRepositoryRoot(Event):
    _severity_ = EventType.Note

class SubtreeMergeinfoModified(Event):
    _severity_ = EventType.Note

class SubtreeMergeinfoRemoved(Event):
    _severity_ = EventType.Note

class Merge(Event):
    _severity_ = EventType.Note

class RootRemoved(Event):
    _severity_ = EventType.Note

class ValidMultirootCommit(Event):
    _severity_ = EventType.Note
    _desc_ = "valid multi-root commit"

class MultipleUnknownAndKnowRootsVerifiedByExternals(Event):
    _severity_ = EventType.Note
    _desc_ = "multiple known and unknown roots verified by svn:externals"

class BranchRenamed(Event):
    _severity_ = EventType.Note

class TrunkRelocated(Event):
    _severity_ = EventType.Note

class FileReplacedViaCopyDuringMerge(Event):
    _severity_ = EventType.Note

class FileUnchangedButParentCopyOrRenameBug(Event):
    _severity_ = EventType.Note
    _desc_ = "file is unchanged but there is a parent rename or copy action"

class DirUnchangedButParentCopyOrRenameBug(Event):
    _severity_ = EventType.Note
    _desc_ = "directory is unchanged but there is a parent rename or copy action"

class UnchangedFileDuringMerge(Event):
    _severity_ = EventType.Note
    _desc_ = "file unchanged during merge"

class UnchangedDirDuringMerge(Event):
    _severity_ = EventType.Note
    _desc_ = "dir unchanged during merge"

#=============================================================================
# Confirm
#=============================================================================
class KnownRootRemoved(Event):
    _severity_ = EventType.Warn

#=============================================================================
# Warn
#=============================================================================
class TagRenamed(Event):
    _severity_ = EventType.Warn

class TagModified(Event):
    _severity_ = EventType.Warn

class MultipleUnknownAndKnownRootsModified(Event):
    _severity_ = EventType.Warn
    _desc_ = "multiple known and unknown roots modified in the same commit"

class MixedRootNamesInMultiRootCommit(Event):
    _severity_ = EventType.Warn
    _desc_ = "mixed root names in multi-root commit"

class MixedRootTypesInMultiRootCommit(Event):
    _severity_ = EventType.Warn
    _desc_ = "mixed root types in multi-root commit"

class SubversionRepositoryCheckedIn(Event):
    _severity_ = EventType.Warn

class MergeinfoAddedToRepositoryRoot(Event):
    _severity_ = EventType.Warn
    _desc_ = "svn:mergeinfo added to repository root '/'"

class MergeinfoModifiedOnRepositoryRoot(Event):
    _severity_ = EventType.Warn
    _desc_ = "svn:mergeinfo modified on repository root '/'"

class SubtreeMergeinfoAdded(Event):
    _severity_ = EventType.Warn
    _desc_ = "svn:mergeinfo added to subtree"

class RootMergeinfoRemoved(Event):
    _severity_ = EventType.Warn
    _desc_ = "svn:mergeinfo removed from root"

class DirectoryReplacedDuringMerge(Event):
    _severity_ = EventType.Warn

class EmptyMergeinfoCreated(Event):
    _severity_ = EventType.Warn
    _desc_ = "empty svn:mergeinfo property set on path"

#=============================================================================
# Error
#=============================================================================
class TagDirectoryCreatedManually(Event):
    _severity_ = EventType.Warn

class BranchDirectoryCreatedManually(Event):
    _severity_ = EventType.Warn

class BranchRenamedToTrunk(Event):
    _severity_ = EventType.Warn

class TrunkRenamedToBranch(Event):
    _severity_ = EventType.Warn

class TrunkRenamedToTag(Event):
    _severity_ = EventType.Warn

class BranchRenamedToTag(Event):
    _severity_ = EventType.Warn

class BranchRenamedOutsideRootBaseDir(Event):
    _severity_ = EventType.Warn
    _desc_ = "branch renamed to location outside root base dir"

class TagSubtreePathRemoved(Event):
    _severity_ = EventType.Warn

class RenameAffectsMultipleRoots(Event):
    _severity_ = EventType.Warn

class UncleanRenameAffectsMultipleRoots(Event):
    _severity_ = EventType.Warn

class MultipleRootsCopied(Event):
    _severity_ = EventType.Warn

class TagCopied(Event):
    _severity_ = EventType.Warn

class UncleanCopy(Event):
    _severity_ = EventType.Warn

class FileRemovedFromTag(Event):
    _severity_ = EventType.Warn

class CopyKnownRootSubtreeToValidAbsRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "copy known root subtree to valid absolute root path"

class MixedRootsNotClarifiedByExternals(Event):
    _severity_ = EventType.Warn
    _desc_ = "multiple known and unknown roots in commit could not be clarified by svn:externals"

class CopyKnownRootToIncorrectlyNamedRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root copied to an incorrectly-named new root path"

class CopyKnownRootSubtreeToIncorrectlyNamedRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root subtree copied to incorrectly-named new root path"

class UnknownPathRenamedToIncorrectlyNamedNewRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "unknown path renamed incorrectly to new root path name"

class RenamedKnownRootToIncorrectlyNamedRootPath(Event):
    _severity_ = EventType.Warn

class MixedChangeTypesInMultiRootCommit(Event):
    _severity_ = EventType.Warn
    _desc_ = "mixed change types in multi-root commit"

class CopyKnownRootToKnownRootSubtree(Event):
    _severity_ = EventType.Warn

class UnknownPathCopiedToIncorrectlyNamedNewRootPath(Event):
    _severity_ = EventType.Warn

class RenamedKnownRootToKnownRootSubtree(Event):
    _severity_ = EventType.Warn
    _desc_ = "renamed root to known root subtree"

class FileUnchangedAndNoParentCopyOrRename(Event):
    _severity_ = EventType.Warn
    _desc_ = "file has no text or property changes, and no parent copy or rename actions can be found"

class DirUnchangedAndNoParentCopyOrRename(Event):
    _severity_ = EventType.Warn
    _desc_ = "directory has not changed, and no parent copy or rename actions can be found"

class EmptyChangeSet(Event):
    _severity_ = EventType.Warn

class RenameRelocatedPathOutsideKnownRoot(Event):
    _severity_ = EventType.Warn

class TagRemoved(Event):
    _severity_ = EventType.Warn

class CopyKnownRootToUnknownPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root copied to unknown path"

class CopyKnownRootSubtreeToInvalidRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root copied to invalid root path"

class NewRootCreatedByRenamingUnknownPath(Event):
    _severity_ = EventType.Warn

class UnknownPathCopiedToKnownRootSubtree(Event):
    _severity_ = EventType.Warn

class NewRootCreatedByCopyingUnknownPath(Event):
    _severity_ = EventType.Warn

class RenamedKnownRootToUnknownPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root renamed to unknown path"

class RenamedKnownRootSubtreeToUnknownPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root subtree renamed to unknown path"

class RenamedKnownRootSubtreeToValidRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root subtree renamed to valid root path"

class RenamedKnownRootSubtreeToIncorrectlyNamedRootPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "known root subtree renamed to incorrectly-named root path"

class UncleanRename(Event):
    _severity_ = EventType.Warn

class PathCopiedFromOutsideRootDuringNonMerge(Event):
    _severity_ = EventType.Warn
    _desc_ = "path copied from outside root during non-merge"

class UnknownDirReplacedViaCopyDuringNonMerge(Event):
    _severity_ = EventType.Warn
    _desc_ = "unknown directory replaced via copy during non-merge"

class DirReplacedViaCopyDuringNonMerge(Event):
    _severity_ = EventType.Warn
    _desc_ = "directory replaced via copy during non-merge"

class DirectoryReplacedDuringNonMerge(Event):
    _severity_ = EventType.Warn
    _desc_ = "directory replaced during non-merge"

class PreviousPathNotMatchedToPathsInMergeinfo(Event):
    _severity_ = EventType.Warn
    _desc_ = "previous path not matched to paths in mergeinfo"

class PreviousRevDiffersFromParentCopiedFromRev(Event):
    _severity_ = EventType.Warn
    _desc_ = "previous rev differs from parent copied-from rev"

class PreviousPathDiffersFromParentCopiedFromPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "previous path differs from parent copied-from path"

class PreviousRevDiffersFromParentRenamedFromRev(Event):
    _severity_ = EventType.Warn
    _desc_ = "previous rev differs from parent renamed-from rev"

class PreviousPathDiffersFromParentRenamedFromPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "previous path differs from parent renamed-from path"

class KnownRootPathReplacedViaCopy(Event):
    _severity_ = EventType.Warn

class BranchesDirShouldBeCreatedManuallyNotCopied(Event):
    _severity_ = EventType.Warn
    _desc_ = "'branches' directory should be created manually not copied"

class TagsDirShouldBeCreatedManuallyNotCopied(Event):
    _severity_ = EventType.Warn
    _desc_ = "'tags' directory should be created manually not copied"

class CopiedFromPathNotMatchedToPathsInMergeinfo(Event):
    _severity_ = EventType.Warn
    _desc_ = "copied-from path not matched to paths in mergeinfo"

class InvariantViolatedModifyContainsMismatchedPreviousPath(Event):
    _severity_ = EventType.Warn
    _desc_ = "invariant violated: modify contains mismatched previous path"

class InvariantViolatedModifyContainsMismatchedPreviousRev(Event):
    _severity_ = EventType.Warn
    _desc_ = "invariant violated: modify contains mismatched previous path"

class InvariantViolatedCopyNewPathInRootsButNotReplace(Event):
    _severity_ = EventType.Warn
    _desc_ = "invariant violated: the new path name created (via copy) is already a known root, but the change isn't marked as a replace."

class MultipleRootsAffectedByRemove(Event):
    _severity_ = EventType.Warn

class AbsoluteRootOfRepositoryCopied(Event):
    _severity_ = EventType.Error

#=============================================================================
# Fatal
#=============================================================================
class InvariantViolatedDieCalledWithoutErrorInfo(Event):
    _severity_ = EventType.Fatal
    _desc_ = "invariant violated: Repository.die() method called without any error information being set."

class VersionMismatch(Event):
    _severity_ = EventType.Fatal
    _desc_ = "version mismatch: we are at version %d, but the 'evn:version' revision property found on revision 0 reports the repository is at version %d"

class MissingOrEmptyRevPropOnRev0(Event):
    _severity_ = EventType.Fatal
    _desc_ = "missing or empty 'evn:%s' revision property on revision 0"

class InvalidIntegerRevPropOnRev0(Event):
    _severity_ = EventType.Fatal
    _desc_ = "invalid value for 'evn:%s' revision property on revision 0; expected an integer greater than or equal to %d, got: %s"

class PropertyValueConversionFailed(Event):
    _severity_ = EventType.Fatal
    _desc_ = "failed to convert property %s's value: %s"

class PropertyValueLiteralEvalFailed(Event):
    _severity_ = EventType.Fatal
    _desc_ = "invalid value for property '%s': %s"

class LastRevTooHigh(Event):
    _severity_ = EventType.Fatal
    _desc_ = "the value for the revision property 'evn:last_rev' on revision 0 of the repository is too high; it indicates the last processed revision was %d, however, the highest revision in the repository is only %d"
    last_processed_rev = int
    high_rev_in_repo = int

class RepositoryOutOfSyncTxn(Event):
    _severity_ = EventType.Fatal
    _desc_ = "the repository is out of sync and can not be committed to at this time (base revision for this transaction: %d, repository last synchronised at revision: %d, current repository revision: %d)"

class LastRevNotSetToBaseRevDuringPostCommit(Event):
    _severity_ = EventType.Fatal
    _desc_ = "the repository is out of sync (last_rev is not set to base_rev during post-commit), preventing post-commit processing of this revision; is the pre-commit hook enabled? (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"

class OutOfOrderRevisionProcessingAttempt(Event):
    _severity_ = EventType.Fatal
    _desc_ = "unable to process repository revision %d until the base revision %d has been processed; however, the last processed revision reported by the repository is %d (current repository revision: %d)"

class RootsMissingFromBaseRevTxn(Event):
    _severity_ = EventType.Fatal
    _desc_ = "missing or empty 'evn:roots' revision property on base revision (this transaction: %s, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"

class RootsMissingFromBaseRevDuringPostCommit(Event):
    _severity_ = EventType.Fatal
    _desc_ = "missing or empty 'evn:roots' revision property on base revision, preventing post-commit processing of this revision; is the pre-commit hook enabled? (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"

class ChangeSetOnlyApplicableForRev1AndHigher(Event):
    _severity_ = EventType.Fatal
    _desc_ = "changeset only applicable to revisions 1 and higher"

class InvalidRootsForRev(Event):
    _severity_ = EventType.Fatal
    _desc_ = "invalid value for 'evn:roots' revision property on revision (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"

class StaleTxnProbablyDueToHighLoad(Event):
    _severity_ = EventType.Fatal
    _desc_ = "please re-try your commit -- the repository is under load and your transaction became out-of-date while it was being queued for processing (base revision for this transaction: %d, repository last synchronised at revision: %d, current repository revision: %d)"

class PropertyChangedButOldAndNewValuesAreSame(Event):
    _severity_ = EventType.Fatal
    _desc_ = "the property '%s' is recorded as having changed, but the old value and new value are identical ('%s')"


# vim:set ts=8 sw=4 sts=4 tw=0 et:
