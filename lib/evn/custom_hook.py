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

class DebuggerCustomHook(CustomHook):
    """
    Launches an evn.debug.RemoteDebugSession upon entry into pre_commit or
    post_commit().
    """
    rdb = None
    commit = None
    def set_trace(self, commit):
        # Note: there's a slight flaw in this logic; it just tests for the
        # presence of rdb, it doesn't check that it's actually enabled for
        # whatever pre/post commit phase we're in.
        if not commit.rdb:
            from .command import CommandError
            raise CommandError(
                'Hook debugging has not been enabled.  Run `evnadmin '
                'enable-remote-debug -k pre-commit REPO_PATH` first, then '
                're-try your commit.'
            )
        self.commit = commit
        self.rdb = commit.rdb
        self.rdb.set_trace()

    def process_commit(self, commit, *args, **kwds):
        self.set_trace(commit)
        changeset = commit.changeset
        top = changeset.top
        root_details = top.root_details
        for change in changeset:
            change.change_type

    def pre_commit(self, commit, *args, **kwds):
        self.process_commit(commit, *args, **kwds)

    def post_commit(self, commit, *args, **kwds):
        # Uncomment to process post-commits as well:
        #self.process_commit(commit, *args, **kwds)
        pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
