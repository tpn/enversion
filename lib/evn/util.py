#===============================================================================
# Imports
#===============================================================================
import os
import sys
import shutil
import inspect
import datetime
import importlib
import itertools

import cStringIO as StringIO

from itertools import (
    chain,
    repeat,
)

from pprint import (
    pformat,
)

from functools import (
    wraps,
    partial,
)

from collections import (
    Hashable,
)

from subprocess import (
    Popen,
    PIPE,
)

#===============================================================================
# Helper Methods
#===============================================================================
def one(r):
    return bool(sum((1 if i else 0) for i in r) == 1)

def one_or_none(r):
    return bool(sum((1 if i else 0) for i in r) <= 1)

def none(r):
    return bool(sum((1 if i else 0) for i in r) == 0)

def bytes_to_mb(b):
    return '%0.3fMB' % (float(b)/1024.0/1024.0)

def bytes_to_kb(b):
    return '%0.3fKB' % (float(b)/1024.0)

def iterable(i):
    return (i,) if not hasattr(i, '__iter__') else i

def try_int(i):
    if not i:
        return
    try:
        i = int(i)
    except ValueError:
        return
    else:
        return i

def is_int(i):
    if i is None:
        return False
    try:
        int(i)
    except ValueError:
        return False
    else:
        return True

def requires_context(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        obj = args[0]
        fname = f.func_name
        n = '%s.%s' % (obj.__class__.__name__, fname)
        if not obj.entered:
            m = "%s must be called from within an 'with' statement." % n
            raise RuntimeError(m)
        elif obj.exited:
            allow = False
            try:
                allow = obj.allow_reentry_after_exit
            except AttributeError:
                pass
            if not allow:
                m = "%s can not be called after leaving a 'with' statement."
                raise RuntimeError(m % n)
            else:
                obj.exited = False
        return f(*args, **kwds)
    return wrapper

def implicit_context(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        obj = args[0]
        fname = f.func_name
        n = '%s.%s' % (obj.__class__.__name__, fname)
        if not obj.entered:
            with obj as obj:
                return f(*args, **kwds)
        else:
            return f(*args, **kwds)
    return wrapper

def add_linesep_if_missing(s):
    return s if s[-1] is os.linesep else s + os.linesep

def strip_linesep_if_present(s):
    if s.endswith('\r\n'):
        return s[:-2]
    elif s[-1] == '\n':
        return s[:-1]
    else:
        return s

def prepend_warning_if_missing(s):
    return add_linesep_if_missing(
        s if s.startswith('warning: ') else 'warning: ' + s
    )

def prepend_error_if_missing(s):
    return add_linesep_if_missing(
        s if s.startswith('error: ') else 'error: ' + s
    )

def render_text_table(rows, **kwds):
    banner = kwds.get('banner')
    footer = kwds.get('footer')
    output = kwds.get('output', sys.stdout)
    balign = kwds.get('balign', str.center)
    formats = kwds.get('formats')
    special = kwds.get('special')
    rows = list(rows)
    if not formats:
        formats = lambda: chain((str.ljust,), repeat(str.rjust))

    cols = len(rows[0])
    paddings = [
        max([len(str(r[i])) for r in rows]) + 2
            for i in xrange(cols)
    ]

    length = sum(paddings) + cols
    strip = '+%s+' % ('-' * (length-1))
    out = list()
    if banner:
        lines = iterable(banner)
        banner = [ strip ] + \
                 [ '|%s|' % balign(l, length-1) for l in lines ] + \
                 [ strip, ]
        out.append('\n'.join(banner))

    rows.insert(1, [ '-', ] * cols)
    out += [
        '\n'.join([
            k + '|'.join([
                fmt(str(column), padding, (
                    special if column == special else fill
                )) for (column, fmt, padding) in zip(row, fmts(), paddings)
            ]) + k for (row, fmts, fill, k) in zip(
                rows,
                chain(
                    repeat(lambda: repeat(str.center,), 1),
                    repeat(formats,)
                ),
                chain((' ',), repeat('-', 1), repeat(' ')),
                chain(('|', '+'), repeat('|'))
            )
        ] + [strip,])
    ]

    if footer:
        footers = iterable(footer)
        footer = [ strip ] + \
                 [ '|%s|' % balign(f, length-1) for f in footers ] + \
                 [ strip, '' ]
        out.append('\n'.join(footer))

    output.write(add_linesep_if_missing('\n'.join(out)))

def render_rst_grid(rows, **kwds):
    output  = kwds.get('output', sys.stdout)
    formats = kwds.get('formats')
    special = kwds.get('special')
    rows = list(rows)
    if not formats:
        formats = lambda: chain((str.ljust,), repeat(str.rjust))

    cols = len(rows[0])
    paddings = [
        max([len(str(r[i])) for r in rows]) + 2
            for i in xrange(cols)
    ]

    length = sum(paddings) + cols
    strip = '+%s+' % ('-' * (length-1))
    out = list()
    if banner:
        lines = iterable(banner)
        banner = [ strip ] + \
                 [ '|%s|' % balign(l, length-1) for l in lines ] + \
                 [ strip, ]
        out.append('\n'.join(banner))

    rows.insert(1, [ '-', ] * cols)
    out += [
        '\n'.join([
            k + '|'.join([
                fmt(str(column), padding, (
                    special if column == special else fill
                )) for (column, fmt, padding) in zip(row, fmts(), paddings)
            ]) + k for (row, fmts, fill, k) in zip(
                rows,
                chain(
                    repeat(lambda: repeat(str.center,), 1),
                    repeat(formats,)
                ),
                chain((' ',), repeat('-', 1), repeat(' ')),
                chain(('|', '+'), repeat('|'))
            )
        ] + [strip,])
    ]

    if footer:
        footers = iterable(footer)
        footer = [ strip ] + \
                 [ '|%s|' % balign(f, length-1) for f in footers ] + \
                 [ strip, '' ]
        out.append('\n'.join(footer))

    output.write(add_linesep_if_missing('\n'.join(out)))


def literal_eval(v):
    try:
        import ast
    except ImportError:
        return eval(v)
    else:
        return ast.literal_eval(v)

def load_propval(orig_value, propname, attempts):
    c = itertools.count(0)

    eval_value = None
    conv_value = None

    last_attempt = False

    attempt = attempts.next()

    try:
        if attempt == c.next():
            assert orig_value == literal_eval(orig_value)
            return orig_value

        if attempt == c.next():
            conv_value = pformat(orig_value)
            eval_value = literal_eval(conv_value)
            assert eval_value == orig_value
            return conv_value

        if attempt == c.next():
            conv_value = '"""%s"""' % pformat(orig_value)
            eval_value = literal_eval(conv_value)
            assert eval_value == orig_value
            return conv_value

        if attempt == c.next():
            conv_value = repr(orig_value)
            eval_value = literal_eval(conv_value)
            assert eval_value == orig_value
            return conv_value

        if attempt == c.next():
            conv_value = str(orig_value)
            eval_value = literal_eval(conv_value)
            assert eval_value == orig_value
            return conv_value

        last_attempt = True

    except:
        if not last_attempt:
            return load_propval(orig_value, propname, attempts)
        else:
            raise ValueError(
                "failed to convert property '%s' value: %s" % (
                    propname,
                    orig_value,
                )
            )

def lower(l):
    return [ s.lower() for s in l ]

def get_methods_in_order(obj, predicate=None):
    """
    Return a tuple consisting of two-pair tuples.  The first value is an
    integer starting at 0 and the second is the value of the method name.

    If predicate is not None, predicate(method_name) will be called with
    the method name (string).  Return True to add the value to the list.

    >>> class Test(object):
    ...     def __init__(self): pass
    ...     def xyz(self): pass
    ...     def abc(self): pass
    ...     def kef(self): pass
    >>>
    >>> t = Test()
    >>> get_methods_in_order(t)
    ((0, 'xyz'), (1, 'abc'), (2, 'kef'))
    >>> [ n for n in dir(t) if n[0] != '_' ]
    ['abc', 'kef', 'xyz']
    >>>

    >>> class PredicateTest(object):
    ...     def f_z(self): pass
    ...     def xyz(self): pass
    ...     def f_x(self): pass
    ...     def abc(self): pass
    ...     def f_a(self): pass
    ...     def kef(self): pass
    >>>
    >>> t = PredicateTest()
    >>> get_methods_in_order(t, lambda s: s.startswith('f_'))
    ((0, 'f_z'), (1, 'f_x'), (2, 'f_a'))
    >>> [ n for n in dir(t) if n[0] != '_' ]
    ['abc', 'f_a', 'f_x', 'f_z', 'kef', 'xyz']
    >>>
    """
    return tuple(
        (i, m) for (i, m) in enumerate(
              m[1] for m in sorted(
                  (m[1].im_func.func_code.co_firstlineno, m[0]) for m in (
                      inspect.getmembers(obj, lambda v:
                          inspect.ismethod(v) and
                          v.im_func.func_name[0] != '_'
                      )
                  )
              ) if not predicate or predicate(m[1])
        )
    )

def timestamp_string():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S-%f')

def touch_file(path):
    if os.path.exists(path):
        return

    with open(path, 'w') as f:
        f.truncate(0)
        f.flush()
        f.close()

    assert os.path.exists(path)

def file_exists_and_not_empty(path):
    """
    Returns an os.path.abspath()-version of `path` if it exists, is a file,
    and is not empty (i.e. has a size greater than zero bytes).
    """
    if not path:
        return

    path = os.path.abspath(path)

    if not os.path.isfile(path):
        return

    try:
        with open(path, 'r') as f:
            pass

        if os.stat(path).st_size > 0:
            return path
    except:
        return

def first_writable_file_that_preferably_exists(files):
    """
    Returns the first file in files (sequence of path names) that preferably
    exists and is writable.  "Preferably exists" means that two loops are done
    over the files -- the first loop returns the first file that exists and is
    writable.  If no files are found, a second loop is performed and the first
    file that can be opened for write is returned.  If that doesn't find
    anything, a RuntimeError is raised.

    Note that the "writability" test is literally conducted by attempting to
    open the file for writing (versus just checking for write permissions).
    """
    # Explicitly coerce into a list as we may need to enumerate over the
    # contents twice (which we couldn't do if we're passed a generator).
    files = [ f for f in filter(None, files) ]

    # First pass: look for files that exist and are writable.
    for f in files:
        if file_exists_and_not_empty(f):
            try:
                with open(f, 'w'):
                    return f
            except (IOError, OSError):
                pass

    # Second pass: just pick the first file we can find that's writable.
    for f in files:
        try:
            with open(f, 'w'):
                return f
        except (IOError, OSError):
            pass

    raise RuntimeError("no writable files found")

def try_remove_file(path):
    try:
        os.unlink(path)
    except:
        pass

def try_remove_file_atexit(path):
    import atexit
    atexit.register(try_remove_file, path)

def try_remove_dir(path):
    shutil.rmtree(path, ignore_errors=True)

def try_remove_dir_atexit(path):
    import atexit
    atexit.register(try_remove_dir, path)

def pid_exists(pid):
    if os.name == 'nt':
        import psutil
        return psutil.pid_exists(pid)
    else:
        try:
            os.kill(pid, 0)
        except OSError as e:
            import errno
            if e.errno == errno.ESRCH:
                return False
            else:
                raise
        else:
            return True

class chdir(object):
    def __init__(self, path):
        self.old_path = os.getcwd()
        self.path = path

    def __enter__(self):
        os.chdir(self.path)
        return self

    def __exit__(self, *exc_info):
        os.chdir(self.old_path)

def load_class(classname, default_modulename=None):
    """
    Uses importlib to load an instance of the class specified by
    ``classname``.  If ``default_modulename`` is not null, it will be
    prepended to the classname if no module is already present.
    If default_module is null and classname is not dotted, then
    globals()[classname] will be returned.
    """
    module = None
    n = classname
    if '.' in n:
        ix = n.rfind('.')
        classname = n[ix+1:]
        modulename = n[:ix]
        module = importlib.import_module(modulename)
    else:
        classname = n
        if default_module:
            module = importlib.import_module(default_modulename)

    if module:
        return getattr(module, classname)
    else:
        return globals()[classname]

def chargen(lineno, nchars=72):
    start = ord(' ')
    end = ord('~')
    c = lineno + start
    while c > end:
        c = (c % end) + start
    b = bytearray(nchars)
    for i in range(0, nchars-2):
        if c > end:
            c = start
        b[i] = c
        c += 1

    b[nchars-1] = ord('\n')

    return b

def bulk_chargen(nbytes):
    b = chargen(0, nbytes)
    for i in range(0, nbytes, 72):
        b[i] = '\n'
    return b

#===============================================================================
# Memoize Helpers (lovingly stolen from conda.utils)
#===============================================================================
class memoized(object):
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
    def __call__(self, *args):
        if not isinstance(args, Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value

# For instance methods only
class memoize(object): # 577452
    def __init__(self, func):
        self.func = func
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)
    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res

#===============================================================================
# Helper Classes
#===============================================================================
class UnexpectedCodePath(RuntimeError):
    pass

class NullObject(object):
    """
    This is a helper class that does its best to pretend to be forgivingly
    null-like.

    >>> n = NullObject()
    >>> n
    None
    >>> n.foo
    None
    >>> n.foo.bar.moo
    None
    >>> n.foo().bar.moo(True).cat().hello(False, abc=123)
    None
    >>> n.hornet(afterburner=True).shotdown(by=n().tomcat)
    None
    >>> n or 1
    1
    >>> str(n)
    ''
    >>> int(n)
    0
    >>> len(n)
    0
    """
    def __getattr__(self, name):
        return self

    def __getitem__(self, item):
        return self

    def __call__(self, *args, **kwds):
        return self

    def __nonzero__(self):
        return False

    def __repr__(self):
        return repr(None)

    def __str__(self):
        return ''

    def __int__(self):
        return 0

    def __len__(self):
        return 0

class Constant(dict):
    def __init__(self):
        items = self.__class__.__dict__.items()
        for (key, value) in filter(lambda t: t[0][:2] != '__', items):
            try:
                self[value] = key
            except:
                pass
    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

class ContextSensitiveObject(object):
    allow_reentry_after_exit = True

    def __init__(self, *args, **kwds):
        self.context_depth = 0
        self.entered = False
        self.exited = False

    def __enter__(self):
        assert self.entered is False
        if self.allow_reentry_after_exit:
            self.exited = False
        else:
            assert self.exited is False
        result = self._enter()
        self.entered = True
        assert isinstance(result, self.__class__)
        return result

    def __exit__(self, *exc_info):
        assert self.entered is True and self.exited is False
        self._exit()
        self.exited = True
        self.entered = False

    def _enter(self):
        raise NotImplementedError

    def _exit(self, *exc_info):
        raise NotImplementedError

class ImplicitContextSensitiveObject(object):

    def __init__(self, *args, **kwds):
        self.context_depth = 0

    def __enter__(self):
        self.context_depth += 1
        self._enter()
        return self

    def __exit__(self, *exc_info):
        self.context_depth -= 1
        self._exit(*exc_in)

    def _enter(self):
        raise NotImplementedError

    def _exit(self, *exc_info):
        raise NotImplementedError

class ConfigList(list):
    def __init__(self, parent, name, args):
        self._parent = parent
        self._name = name
        list.__init__(self, args)

    def append(self, value):
        list.append(self, value)
        self._parent._save(self._name, self)

class ConfigDict(dict):
    def __init__(self, parent, name, kwds):
        self._parent = parent
        self._name = name
        dict.__init__(self, kwds)

    def __getattr__(self, name):
        if name[0] == '_':
            return dict.__getattribute__(self, name)
        else:
            return self.__getitem__(name)

    def __setattr__(self, name, value):
        if name[0] == '_':
            dict.__setattr__(self, name, value)
        else:
            self.__setitem__(name, value)

    def __getitem__(self, name):
        i = dict.__getitem__(self, name)
        if isinstance(i, dict):
            return ConfigDict(self, name, i)
        elif isinstance(i, list):
            return ConfigList(self, name, i)
        else:
            return i

    def __delitem__(self, name):
        dict.__delitem__(self, name)
        self._parent._save(self._name, self)

    def __setitem__(self, name, value):
        dict.__setitem__(self, name, value)
        self._parent._save(self._name, self)

    def _save(self, name, value):
        self[name] = value


class Pool(object):
    def __init__(self, parent_pool=None):
        self.__parent_pool = parent_pool
        self.__pool = None

    def __enter__(self):
        import svn.core
        self.__pool = svn.core.Pool(self.__parent_pool)
        return self.__pool

    def __exit__(self, *exc_info):
        self.__pool.destroy()
        del self.__pool

class Options(dict):
    def __init__(self, values=dict()):
        assert isinstance(values, dict)
        dict.__init__(self, **values)

    def __getattr__(self, name):
        if name not in self:
            return False
        else:
            return self.__getitem__(name)

class Dict(dict):
    """
    A dict that allows direct attribute access to keys.
    """
    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)
        #self.__dict__.update(**kwds)
    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)


class DecayDict(Dict):
    """
    A dict that allows once-off direct attribute access to keys.  The key/
    attribute is subsequently deleted after a successful get.
    """
    def __getitem__(self, name):
        v = dict.__getitem__(self, name)
        del self[name]
        return v

    def get(self, name, default=None):
        v = dict.get(self, name, default)
        if name in self:
            del self[name]
        return v

    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

    def assert_empty(self, obj):
        if self:
            raise RuntimeError(
                "%s:%s: unexpected keywords: %s" % (
                    obj.__class__.__name__,
                    inspect.currentframe().f_back.f_code.co_name,
                    repr(self)
                )
            )

class MutexDecayDict(object):
    """
    Like DecayDict in that we provide once-off direct attribute access to
    keys, except we have an assert_once() method instead of assert_empty()
    that will, er, not assert iff one attribute has been accessed once.

    Only one attribute can be set to true:
        >>> m = MutexDecayDict()
        >>> m.foo = True
        >>> m.bar = True
        Traceback (most recent call last):
            ...
        AssertionError

    An attribute can only be set to True once:
        >>> m = MutexDecayDict()
        >>> m.foo = True
        >>> m.foo = True
        Traceback (most recent call last):
            ...
        AssertionError


    An attribute can only be set to False once:
        >>> m = MutexDecayDict()
        >>> m.foo = False
        >>> m.foo = False
        Traceback (most recent call last):
            ...
        AssertionError

    Testing can't begin until we've received our True attribute:
        >>> m = MutexDecayDict()
        >>> m.tomcat = False
        >>> with m as f:
        ...     f.tomcat
        Traceback (most recent call last):
            ...
        AssertionError

        >>> m = MutexDecayDict()
        >>> m.viper = False
        >>> m.eagle = True
        >>> with m as f:
        ...     f.viper
        ...     f.eagle
        False
        True

    You can't access attributes that haven't been set:
        >>> m = MutexDecayDict()
        >>> m.eagle = True
        >>> m.raptor
        Traceback (most recent call last):
            ...
        AssertionError
        >>> m = MutexDecayDict()
        >>> m.eagle = True
        >>> with m as f:
        ...     f.tomcat
        Traceback (most recent call last):
            ...
        AssertionError

    Once testing's begun, no more attribute assignment is allowed:
        >>> m = MutexDecayDict()
        >>> m.viper = False
        >>> m.eagle = True
        >>> with m as f:
        ...     f.tomcat = False
        Traceback (most recent call last):
            ...
        AssertionError

    Testing's finished once the True attribute has been accessed (if it hasn't
    been accessed, bomb out):

        >>> m = MutexDecayDict()
        >>> m.viper = True
        >>> with m as f:
        ...     f.viper
        True

        >>> m = MutexDecayDict()
        >>> m.viper = True
        >>> m.eagle = False
        >>> with m as f:
        ...     f.eagle
        Traceback (most recent call last):
            ...
        AssertionError

    Once testing's finished, no more attribute assignment or access is allowed
    (for any/all attributes):

        >>> m = MutexDecayDict()
        >>> m.viper = True
        >>> m.eagle = False
        >>> with m as f:
        ...     f.viper
        True
        >>> m.viper
        Traceback (most recent call last):
            ...
        AssertionError

    No assignment allowed after testing has completed:
        >>> m = MutexDecayDict()
        >>> m.viper = True
        >>> with m as f:
        ...     f.viper
        True
        >>> m.hornet = False
        Traceback (most recent call last):
            ...
        AssertionError

    No accessing attributes outside the context of an, er, context manager:
        >>> m = MutexDecayDict()
        >>> m.viper  = True
        >>> m.hornet = False
        >>> m.hornet
        Traceback (most recent call last):
            ...
        AssertionError
        >>> m = MutexDecayDict()
        >>> m.viper  = True
        >>> m.viper
        Traceback (most recent call last):
            ...
        AssertionError
        >>> m.viper = False
        Traceback (most recent call last):
            ...
        AssertionError

    A false attribute can only be accessed once during testing:
        >>> m = MutexDecayDict()
        >>> m.viper  = True
        >>> m.hornet = False
        >>> with m as f:
        ...     f.hornet
        ...     f.hornet
        Traceback (most recent call last):
            ...
        AssertionError

    If you haven't accessed the True attribute... you'll find out about it
    during the with statement's closure:

        >>> m = MutexDecayDict()
        >>> m.eagle  = False
        >>> m.viper  = True
        >>> with m as f:
        ...     m.eagle
        Traceback (most recent call last):
            ...
        AssertionError

        >>> m = MutexDecayDict()
        >>> m.eagle  = False
        >>> m.hornet = False
        >>> m.viper  = True
        >>> with m as f:
        ...     m.eagle
        ...     m.hornet
        Traceback (most recent call last):
            ...
        AssertionError

        >>> m = MutexDecayDict()
        >>> m.eagle  = False
        >>> m.hornet = False
        >>> m.viper  = True
        >>> with m as f:
        ...     m.viper
        ...     m.hornet
        Traceback (most recent call last):
            ...
        AssertionError

    Check that we can unlock after a successful run and that there are no
    restrictions on how many times we can access an element (make sure we
    still can't set stuff, though):

        >>> m = MutexDecayDict()
        >>> m.viper = False
        >>> m.eagle = True
        >>> with m as f:
        ...     f.viper
        ...     f.eagle
        False
        True
        >>> m._unlock()
        >>> m.viper
        False
        >>> m.eagle
        True
        >>> m.viper
        False
        >>> m.tomcat = False
        Traceback (most recent call last):
            ...
        AssertionError

    Test our ability to reset after unlocking:
        >>> m = MutexDecayDict()
        >>> m.viper = False
        >>> m.eagle = True
        >>> with m as f:
        ...     f.viper
        ...     f.eagle
        False
        True
        >>> m._unlock()
        >>> m.viper
        False
        >>> m.eagle
        True
        >>> m._reset()
        >>> m.hornet = False
        >>> with m as f:
        ...     m.hornet
        ...     m.viper
        ...     m.eagle
        False
        False
        True
        >>> m.hornet
        Traceback (most recent call last):
            ...
        AssertionError
        >>> m._unlock()
        >>> m.hornet
        False
        >>> m._unlock()
        Traceback (most recent call last):
            ...
        AssertionError
    """
    def __init__(self):
        self.__d = dict()
        self.__s = set()
        self._mode = 'setup'
        self._name = None
        self._have_true = False
        self._have_started = False

    @property
    def _is_setup(self):
        return (self._mode == 'setup')

    @property
    def _is_test(self):
        return (self._mode == 'test')

    @property
    def _is_end(self):
        return (self._mode == 'end')

    @property
    def _is_exit(self):
        return (self._mode == 'exit')

    @property
    def _is_unlocked(self):
        return (self._mode == 'unlocked')

    def __getattr__(self, name):
        assert name[0] != '_'

        d = self.__d
        s = self.__s

        if self._is_unlocked:
            return d[name]

        assert self._is_test

        assert name in s
        s.remove(name)
        value = d[name]
        if value == True:
            self._mode = 'end'
        return value

    def __setattr__(self, name, value):
        if name[0] == '_':
            return object.__setattr__(self, name, value)

        assert self._is_setup
        assert isinstance(value, bool)
        d = self.__d
        s = self.__s
        assert name not in s
        if value == True:
            assert not self._have_true
            self._have_true = True
            self._name = name
        d[name] = value
        s.add(name)

    def __enter__(self):
        assert self._is_setup
        assert self._have_true
        self._mode = 'test'
        return self

    def __exit__(self, *exc_info):
        if not exc_info or exc_info == (None, None, None):
            assert self._is_end
            self._mode = 'exit'

    def __repr__(self):
        return self._name

    def _unlock(self):
        assert self._is_exit
        self._mode = 'unlocked'

    def _reset(self):
        assert self._is_exit or self._is_unlocked
        self.__s = set(self.__d.keys())
        self._mode = 'setup'


class ProcessWrapper(object):
    def __init__(self, exe, *args, **kwds):
        self.exe      = exe
        self.rc       = int()
        self.cwd      = None
        self.wait     = True
        self.error    = str()
        self.output   = str()
        self.shell    = kwds.get('shell', False)
        self.ostream  = kwds.get('ostream', sys.stdout)
        self.estream  = kwds.get('estream', sys.stderr)
        self.verbose  = kwds.get('verbose', False)
        self.convert_command_name_underscores_to_dashes = (
            kwds.get('convert_command_name_underscores_to_dashes', True)
        )
        self.safe_cmd = None
        self.exception_class = RuntimeError
        self.raise_exception_on_error = True

    def __getattr__(self, attr):
        if not attr.startswith('_') and not attr == 'trait_names':
            return lambda *args, **kwds: self.execute(attr, *args, **kwds)
        else:
            raise AttributeError(attr)

    def __call__(self, *args, **kwds):
        return self.execute(*args, **kwds)

    def build_command_line(self, exe, action, *args, **kwds):
        if self.convert_command_name_underscores_to_dashes:
            action = action.replace('_', '-')

        cmd  = [ exe, action ]
        for (k, v) in kwds.items():
            cmd.append(
                '-%s%s' % (
                    '-' if len(k) > 1 else '', k.replace('_', '-')
                )
            )
            if not isinstance(v, bool):
                cmd.append(v)
        cmd += list(args)
        return cmd

    def kill(self):
        self.p.kill()

    def execute(self, *args, **kwds):
        self.rc = 0
        self.error = ''
        self.output = ''

        self.cmd = self.build_command_line(self.exe, *args, **kwds)

        if self.verbose:
            cwd = self.cwd or os.getcwd()
            cmd = ' '.join(self.safe_cmd or self.cmd)
            self.ostream.write('%s>%s\n' % (cwd, cmd))

        self.p = Popen(
            self.cmd,
            cwd=self.cwd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            shell=self.shell,
        )

        if not self.wait:
            return

        self.outbuf = StringIO.StringIO()
        self.errbuf = StringIO.StringIO()

        while self.p.poll() is None:
            out = self.p.stdout.read()
            self.outbuf.write(out)
            if self.verbose and out:
                self.ostream.write(out)

            err = self.p.stderr.read()
            self.errbuf.write(err)
            if self.verbose and err:
                self.estream.write(err)

        self.rc = self.p.returncode
        self.error = self.errbuf.getvalue()
        self.output = self.outbuf.getvalue()
        if self.rc != 0 and self.raise_exception_on_error:
            if self.error:
                error = self.error
            elif self.output:
                error = 'no error info available, output:\n' + self.output
            else:
                error = 'no error info available'
            printable_cmd = ' '.join(self.safe_cmd or self.cmd)
            raise self.exception_class(printable_cmd, error)
        if self.output and self.output.endswith('\n'):
            self.output = self.output[:-1]
        return self.output

    def clone(self):
        return self.__class__(self.exe)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
