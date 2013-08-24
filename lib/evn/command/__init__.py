#=============================================================================
# Imports
#=============================================================================
import os

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from evn.util import (
    add_linesep_if_missing,
    prepend_error_if_missing,
    prepend_warning_if_missing,
    implicit_context,
    Dict,
    Pool,
    ImplicitContextSensitiveObject,
)

#=============================================================================
# Commands
#=============================================================================
class CommandError(Exception):
    pass

class Command(ImplicitContextSensitiveObject):
    __metaclass__ = ABCMeta

    __first_command__ = None
    __active_command__ = None

    def __init__(self, istream, ostream, estream):
        self.istream = istream
        self.ostream = ostream
        self.estream = estream

        self.conf = None
        self.args = None
        self.result = None
        self.options = None

        self.entered = False
        self.exited = False

        self.is_first = False
        self.first = None
        self.prev = None
        self.next = None

        self._next_commands = []

        self._stash = None
        self._quiet = None

    def __enter__(self):
        if not Command.__active_command__:
            Command.__first_command__ = self
            self.is_first = True
            self.first = self
            self._stash = Dict()
        else:
            active = Command.__active_command__
            self.first = Command.__first_command__
            self.prev = active
            active.next = self

        Command.__active_command__ = self
        self.entered = True
        self._allocate()
        return self

    def __exit__(self, *exc_info):
        self.exited = True
        suppress = self._deallocate(*exc_info)
        self.formatter.end(suppress, *exc_info)
        if not suppress and self._next_commands:
            self.run_next()
        Command.__active_command__ = self.prev
        if not self.prev:
            assert self.is_first
            assert self.first == Command.get_first_command()
            Command.__first_command__ = None

    def _flush(self):
        self.ostream.flush()
        self.estream.flush()

    def _allocate(self):
        """
        Called by `__enter__`.  Subclasses should implement this method if
        they need to do any context-sensitive allocations.  (`_deallocate`
        should also be implemented if this method is implemented.)
        """
        pass

    def _deallocate(self, *exc_info):
        """
        Called by `__exit__`.  Subclasses should implement this method if
        they've implemented `_allocate` in order to clean up any resources
        they've allocated once the context has been left.
        """
        pass

    def _verbose(self, msg):
        """
        Writes `msg` to output stream if '--verbose'.

        Does not prepend anything to `msg`.
        Adds trailing linesep to `msg` if there's not one already.
        """
        if self.options.verbose:
            self.ostream.write(add_linesep_if_missing(msg))

    def _out(self, msg):
        """
        Write `msg` to output stream if not '--quiet'.

        Does not prepend anything to `msg`.
        Adds trailing linesep to `msg` if there's not one already.
        """
        if not self.options.quiet:
            self.ostream.write(add_linesep_if_missing(msg))

    def _warn(self, msg):
        """
        Write `msg` to output stream regardless of '--quiet'.

        Prepends 'warning: ' to `msg` if it's not already present.
        Adds trailing linesep to `msg` if there's not one already.
        """
        self.ostream.write(prepend_warning_if_missing(msg))

    def _err(self, msg):
        """
        Write `msg` to error stream regardless of '--quiet'.


        Prepends 'error: ' to `msg` if it's not already present.
        Adds trailing linesep to `msg` if there's not one already.
        """
        self.estream.write(prepend_error_if_missing(msg))

    @property
    def is_quiet(self):
        if self._quiet is not None:
            return self._quiet
        else:
            return self.options.quiet

    @abstractmethod
    def run(self):
        raise NotImplementedError

    def after(self):
        pass

    def run_next(self):
        seen = set()
        for cls in iterable(self._next_commands):
            if cls in seen:
                continue
            command = self.prime(cls)
            with command:
                command.run()
            command.after()
            seen.add(cls)

    @classmethod
    def prime_class(cls, src, dst_class):
        c = dst_class(src.istream, src.ostream, src.estream)
        c.conf = src.conf
        c.options = src.options
        return c

    def prime(self, cls):
        """
        Create a new instance of ``cls``, primed with the same values as this
        command instance.
        """
        c = cls(self.istream, self.ostream, self.estream)
        c.conf = self.conf
        c.options = self.options
        self_cls = self.__class__
        attrs = [
            d for d in dir(cls) if (
                d[0] != '_' and
                d[0].islower() and (
                    hasattr(self, d) and
                    bool(getattr(self, d)) and
                    getattr(cls, d) is None
                )
            )
        ]
        for attr in attrs:
            setattr(c, attr, getattr(self, attr))

        return c

    @classmethod
    def get_active_command(cls):
        return Command.__active_command__

    @classmethod
    def get_first_command(cls):
        return Command.__first_command__

# vim:set ts=8 sw=4 sts=4 tw=78 et:
