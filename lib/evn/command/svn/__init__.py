#=============================================================================
# Imports
#=============================================================================
import svn.core

from evn.command import Command

#=============================================================================
# Commands
#=============================================================================
class SubversionCommand(Command):
    pool = None
    def _allocate(self):
        self.pool = svn.core.Pool()

    def _deallocate(self, *exc_info):
        self.pool.destroy()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
