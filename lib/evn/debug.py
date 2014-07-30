#===============================================================================
# Imports
#===============================================================================
import os
import sys
import pdb
import socket

from evn.path import (
    join_path,
)

from evn.util import (
    touch_file,
    literal_eval,
    timestamp_string,
    try_remove_file_atexit,
    DecayDict,
)

#===============================================================================
# Classes
#===============================================================================
class RemoteDebugSessionStatus(object):
    pid = int()
    host = str()
    port = int()
    state = str()
    dst_host = str()
    dst_port = int()
    hook_name = str()
    session_file = str()

    def __init__(self, **kwds):
        k = DecayDict(**kwds)
        object.__init__(self)
        for name in self._names:
            value = getattr(self.__class__, name).__class__(getattr(k, name))
            setattr(self, name, value)
        k.assert_empty(k)

    @property
    def _names(self):
        return (n for n in dir(self.__class__) if n[0] != '_')

    @classmethod
    def _load(self, filename):
        with open(filename, 'r') as f:
            return RemoteDebugSessionStatus(**literal_eval(f.read()))

class RemoteDebugSession(pdb.Pdb):
    def __init__(self, host, port, hook_name, hook_dir, options, conf):
        assert os.path.isdir(hook_dir)
        timestamp = timestamp_string()
        self.pid = os.getpid()
        fn = '%s-%s-%s-%s.%d' % (
            conf.svn_hook_enabled_prefix,
            hook_name,
            conf.svn_hook_remote_debug_suffix,
            timestamp_string(),
            self.pid,
        )
        path = join_path(hook_dir, fn)
        assert not os.path.exists(path)
        touch_file(path)
        try_remove_file_atexit(path)

        self.path = self.session_file = path
        self.conf = conf
        self.hook_name = hook_name
        self.options = options
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        (self.host, self.port) = self.sock.getsockname()
        self.dst_host = ''
        self.dst_port = 0
        self.state = 'listening'
        self._dump_state()

        self.sock.listen(1)
        (clientsocket, address) = self.sock.accept()
        (self.dst_host, self.dst_port) = address
        self.state = 'connected'
        self._dump_state()

        handle = clientsocket.makefile('rw')
        k = self.conf.remote_debug_complete_key
        pdb.Pdb.__init__(self, completekey=k, stdin=handle, stdout=handle)
        sys.stdout = sys.stdin = handle

    def __repr__(self):
        return repr(dict(
            (k, getattr(self, k))
                for k in dir(RemoteDebugSessionStatus)
                    if k[0] != '_'
        ))

    def __str__(self):
        return repr(self)

    def _dump_state(self):
        with open(self.path, 'w') as f:
            f.write(repr(self))
            f.flush()
            f.close()

    def __disabled__do_continue(self, *arg):
        self.state = 'finished'
        self._dump_state()
        sys.stdout = self.old_stdout
        sys.stdin = self.old_stdin
        self.sock.close()
        self.set_continue()
        return 1

# vim:set ts=8 sw=4 sts=4 tw=78 et:
