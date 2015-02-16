#===============================================================================
# Imports
#===============================================================================
from evn.util import (
    Constant,
)

#===============================================================================
# Notes, Warnings and Errors
#===============================================================================
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
    RootReplaced = 'root replaced'
    RootAncestorRemoved = 'root ancestor removed'
    RootAncestorReplaced = 'root ancestor replaced'
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
    TrunkRenamedToUnknownPath = 'trunk renamed to unknown path'
    BranchRenamedToTag = 'branch renamed to tag'
    BranchRenamedToUnknown = 'branch renamed to unknown'
    BranchRenamedOutsideRootBaseDir = 'branch renamed to location outside root base dir'
    TagSubtreePathRemoved = 'tag subtree path removed'
    TagSubtreeCopied = 'tag subtree copied'
    TagSubtreeRenamed = 'tag subtree renamed'
    RenameAffectsMultipleRoots = 'rename affects multiple roots'
    UncleanRenameAffectsMultipleRoots = 'unclean rename affects multiple roots'
    MultipleRootsCopied = 'multiple roots copied'
    TagCopied = 'tag copied'
    UncleanCopy = 'unclean copy'
    FileRemovedFromTag = 'file removed from tag'
    CopyKnownRootSubtreeToValidAbsoluteRootPath = 'copy known root subtree to valid absolute root path'
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
    RenameRelocatedPathOutsideKnownRootDuringNonMerge = 'rename relocated path outside known root during non-merge'
    RenameRelocatedPathBetweenKnownRootsDuringMerge = 'rename relocated path between known roots during merge'
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
    RootAncestorRenamedToKnownRootSubtree = "root ancestor renamed to known-root subtree"
    PathCopiedFromOutsideRootDuringNonMerge = 'path copied from outside root during non-merge'
    PathCopiedFromUnrelatedKnownRootDuringMerge = 'path copied from unrelated known root during merge'
    PathCopiedFromUnrelatedRevisionDuringMerge = 'path copied from unrelated revision root during merge'
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
    FileExceedsMaxSize = "file size (%d bytes, %0.2fMB) exceeds limit (%d bytes, %0.2fMB)"
    InvalidTopLevelRepoDirectoryCreated = "invalid top-level repository directory (valid top-level directories: %s)"
    TopLevelRepoDirectoryRemoved = "top-level repository directories cannot be removed"
    TopLevelRepoDirectoryReplaced = "top-level repository directories cannot be replaced"
    InvalidTopLevelRepoComponentDirectoryCreated = "invalid top-level repository directory created for component '%s' (valid top-level directories: %s)"
    TopLevelRepoComponentDirectoryRemoved = "top-level repository directories cannot be removed for component '%s'"
    TopLevelRepoComponentDirectoryReplaced = "top-level repository directories cannot be replaced for component '%s'"
    StandardLayoutTopLevelDirectoryCreatedInMultiComponentRepo = "standard layout top-level directories must be created within a component as this is a multi-component repository (i.e. try mkdir /foo/trunk instead of mkdir /trunk)"
    BlockedFileExtension = "blocked file extension"

e = _Errors()

#===============================================================================
# Globals
#===============================================================================
EVN_RPROPS_SCHEMA_VERSION = 1
EVN_RPROPS_SCHEMA = {
    1 : {
        'roots'     : dict,
        'notes'     : str,
        'errors'    : str,
        'warnings'  : str,
    },
}
assert EVN_RPROPS_SCHEMA_VERSION in EVN_RPROPS_SCHEMA

EVN_BRPROPS_SCHEMA_VERSION = 1
EVN_BRPROPS_SCHEMA = {
    1 : {
        'last_rev' : int,
        'version'  : int,
    },
}
assert EVN_BRPROPS_SCHEMA_VERSION in EVN_BRPROPS_SCHEMA

EVN_ERROR_CONFIRMATIONS = {
    e.RenameAffectsMultipleRoots : 'CONFIRM MULTI-ROOT RENAME',
}

EVN_ERROR_CONFIRMATION_BLURB = (
    "%s (if you're sure you want to perform this action, you can override"
    " this restriction by including the following text anywhere in the"
    " commit message: %s)"
)

#===============================================================================
# Helpers
#===============================================================================
def format_file_exceeds_max_size_error(filesize_in_bytes, max_size_in_bytes):
    return e.FileExceedsMaxSize % (
        filesize_in_bytes,
        float(filesize_in_bytes) / 1024.0 / 1024.0,
        max_size_in_bytes,
        float(max_size_in_bytes) / 1024.0 / 1024.0,
    )

# vim:set ts=8 sw=4 sts=4 tw=0 et:
