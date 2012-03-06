
#=============================================================================
# Commands
#=============================================================================
class CommandError(Exception):
    pass

class Command:
    __metaclass__ = ABCMeta

    def __init__(self, ostream, estream):
        self.ostream = ostream
        self.estream = estream

        self.conf = None
        self.args = None
        self.result = None
        self.options = None

        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        self._allocate()
        return self

    def __exit__(self, *exc_info):
        self.exited = True
        self._deallocate()

    def _flush(self):
        self.ostream.flush()
        self.estream.flush()

    def _err(self, msg):
        self.estream.write(add_linesep_if_missing(msg))

    def _allocate(self):
        pass

    def _deallocate(self):
        pass

    @property
    def _verbose(self):
        try:
            return (self.options.verbose == True)
        except AttributeError:
            return False

    def _out(self, msg):
        if not self._verbose:
            return
        self.ostream.write(add_linesep_if_missing(msg))

    def _warn(self, msg):
        self.ostream.write(add_linesep_if_missing(msg))

    @abstractmethod
    def run(self):
        raise NotImplementedError

    @classmethod
    def prime(cls, src, dst_class):
        c = dst_class(src.ostream, src.estream)
        c.conf = src.conf
        c.options = src.options
        return c



