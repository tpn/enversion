#===============================================================================
# Imports
#===============================================================================
import sys

from ..command import (
    CommandError,
)

from ..custom_hook import (
    CustomHook,
    DebuggerCustomHook,
)

#===============================================================================
# Classes
#===============================================================================
class ChangeSetPropertyTesterCustomHook(DebuggerCustomHook):
    def pre_commit(self, commit, *args, **kwds):
        #self.set_trace(commit)

        s = None

        changeset = commit.changeset
        top = changeset.top

        if changeset.is_tag_create:
            s = 'is_tag_create: %s' % top.path
        elif changeset.is_tag_remove:
            s = 'is_tag_remove: %s' % top.path
        elif changeset.is_branch_create:
            s = 'is_branch_create: %s' % top.path
        elif changeset.is_branch_remove:
            s = 'is_branch_remove: %s' % top.path

        if s:
            raise CommandError(s)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
