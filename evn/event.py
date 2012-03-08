#=============================================================================
# Imports
#=============================================================================
from evn.util import (
    Constant,
)

class _EventType(Constant):
    Note    = 1
    Confirm = 2
    Warn    = 3
    Error   = 4
    Fatal   = 5
EventType = _EventType()

class Event(object):
    pass


# vim:set ts=8 sw=4 sts=4 tw=78 et:
