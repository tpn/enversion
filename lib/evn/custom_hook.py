#===============================================================================
# Classes
#===============================================================================
class CustomHook(object):
    def pre_commit(self, commit, *args, **kwds):
        """
        Called after Enversion's pre-commit hook has run.

        @commit: instance of `evn.hook.RepositoryHook`.
        @args:   not currently used
        @kwds:   not currently used
        """
        pass

    def post_commit(self, commit, *args, **kwds):
        """
        Called after Enversion's post-commit hook has run.

        @commit: instance of `evn.hook.RepositoryHook`.
        @args:   not currently used
        @kwds:   not currently used
        """
        pass

class DummyCustomHook(CustomHook):
    """
    Default custom hook class invoked by Enversion automatically.
    Override via the 'custom-hook-classname' configuration property.
    """
    def pre_commit(self, commit, *args, **kwds):
        pass

    def post_commit(self, commit, *args, **kwds):
        pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
