#===============================================================================
# Imports
#===============================================================================

#===============================================================================
# Base Classes
#===============================================================================
class BlockPreCommit(BaseException):
    def __init__(self, reason):
        pass

class CustomHook(object):
    def pre_branch_or_trunk_modify(self, commit, branch_name, branch_path):
        pass

    def post_branch_or_trunk_modify(self, commit, branch_name, branch_path):
        pass

    def pre_tag_create(self, commit, tag_name, tag_path):
        pass

    def post_tag_create(self, commit, tag_name, tag_path):
        pass

#===============================================================================
# Examples
#===============================================================================
class ExampleCustomHook(CustomHook):
    def pre_branch_or_trunk_modify(self, commit, branch_name, branch_path):
        # If you only want to include/exclude trunk commits, test against
        # `branch_name`:
        if branch_name == 'trunk':
            pass

        # `branch_path` will be the full path of the known root that this
        # commit was associated with.
        if branch_path == '/widget/branches/foo-1.x/':
            # To stop processing, simply return.
            return

        # Commits can be blocked:
        if branch_path == '/gadget/trunk/':
            raise BlockPreCommit('gadget is temporarily frozen')

        # You can get everything else about the commit from the `commit`
        # object, which will be an instance of `evn.repo.RepositoryRevOrTxn`.
        # From here, you can get access to the `changeset` object, which will
        # be an instance of `evn.change.ChangeSet`, and from that, you can
        # get access to the `analysis` object, which is an instance of
        # `evn.change.ChangeSetAnalysis`.

        log_msg = commit.log_msg
        username = commit.user
        changeset = commit.changeset
        analysis = changeset.analysis


    def post_branch_or_trunk_modify(self, commit, branch_name, branch_path):
        # The difference between this method and the pre method above is that
        # this one will be run during post-commit.  You can't block the commit
        # via `raise BlockPreCommit('message')` here -- if you try... it will
        # bubble the error back to the user, but the commit will still go
        # through.
        pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
