#=============================================================================
# Imports
#=============================================================================
import os
import re
import sys
import inspect
import datetime
import itertools
import linecache

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
)

from subprocess import (
    Popen,
    PIPE,
)

#=============================================================================
# Helper Methods
#=============================================================================
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

def first(i, then=None):
    i = iterable(i)
    value = None
    success = False
    try:
        value = i[0]
        success = True
    except:
        try:
            for v in i:
                value = v
                success = True
                break
        except:
            pass
    if success and then:
        return then(value)
    else:
        return value

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
        s if s.startsiwth('warning: ') else 'warning: ' + s
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

def try_remove_file(path):
    try:
        os.unlink(path)
    except:
        pass

def try_remove_file_atexit(path):
    import atexit
    atexit.register(try_remove_file, path)

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

def which(name, flags=os.X_OK):
    # From twisted.python.procutils.py.
    """Search PATH for executable files with the given name.

    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.

    @type name: C{str}
    @param name: The name for which to search.

    @type flags: C{int}
    @param flags: Arguments to L{os.access}.

    @rtype: C{list}
    @param: A list of the full paths to files found, in the
    order in which they were found.
    """
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result

#=============================================================================
# Helper Classes
#=============================================================================
class UnexpectedCodePath(RuntimeError):
    pass

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

class Invariant(BaseException):
    __filter = lambda _, n: (n[0] != '_' and n not in ('message', 'args'))
    __keys = lambda _, n: (
        n[0] != '_' and n not in {
            'args',
            'actual',
            'message',
            'expected',
        }
    )

    def _test_regex(self):
        return bool(self._pattern.match(self.actual))

    def _test_simple_equality(self):
        return (self.actual == self.expected)

    def __check_existing(self):
        obj = self._obj
        name = self._name
        actual = self.actual

        check_existing = (
            not hasattr(self, '_check_existing_') or (
                hasattr(self, '_check_existing_') and
                self._check_existing_
            )
        )

        has_existing = (
            hasattr(obj, '_existing') and
            obj._existing
        )

        if not has_existing:
            return

        ex_obj = obj._existing
        existing = getattr(ex_obj, name)
        existing_str = existing
        actual_str = str(actual)

        if isiterable(existing):
            existing_str = ','.join(str(e) for e in existing)

        elif isinstance(existing, datetime.date):
            existing_str = existing.strftime(self._date_format)

        elif isinstance(existing, datetime.datetime):
            existing_str = existing.strftime(self._datetime_format)

        elif not isinstance(existing, str):
            existing_str = str(existing)

        self._existing = existing
        self._existing_str = existing_str

        if not check_existing:
            return

        if not (existing_str != actual_str):
            message = "%s already has a value of '%s'"
            BaseException.__init__(self, message % (name, actual_str))
            raise self

    def __init__(self, obj, name, actual):
        self._obj = obj
        self._name = name
        self.actual = actual
        self._existing = None
        self._existing_str = None
        n = self.__class__.__name__.replace('Error', '').lower()
        if hasattr(self, '_regex'):
            self._pattern = re.compile(self._regex)
            if not hasattr(self, 'expected'):
                self.expected = "%s to match regex '%s'" % (n, self._regex)
            self._test = self._test_regex

        self.__check_existing()

        if not hasattr(self, '_test'):
            self._test = self._test_simple_equality

        result = self._test()
        if result not in (True, False):
            raise RuntimeError(
                "invalid return value from %s's validation "
                "routine, expected True/False, got: %s (did "
                "you forget to 'return True'?)" % (self._name, repr(result))
            )

        if not result:
            if hasattr(self, 'message') and self.message:
                message = self.message
                prefix = ''
            else:
                keys = [
                    'expected',
                    'actual'
                ] + sorted(filter(self.__keys, dir(self)))
                f = lambda k: 'got' if k == 'actual' else k
                items = ((f(k), repr(getattr(self, k))) for k in keys)
                message = ', '.join('%s: %s' % (k, v) for (k, v) in items)
                prefix = "%s is invalid: " % self._name
            BaseException.__init__(self, prefix + message)
            raise self

class StringInvariant(Invariant):
    _type = str
    _type_desc = 'string'
    _maxlen = None
    _minlen = 2
    @property
    def expected(self):
        assert isinstance(self._maxlen, int) and self._maxlen > 0
        return '%s with length between %d and %d characters' % (
            self._type_desc,
            self._minlen,
            self._maxlen
        )

    def _test(self):
        if not isinstance(self.actual, self._type):
            return False

        l = len(self.actual)
        return (
            l >= self._minlen and
            l <= self._maxlen
        )

class UnicodeInvariant(StringInvariant):
    _type = unicode
    _type_desc = 'unicode string'

class PositiveIntegerInvariant(Invariant):
    expected = "an integer greater than 0"

    def _test(self):
        try:
            return (int(self.actual) > 0)
        except:
            return False

class InvariantAwareObject(object):
    _existing_ = None

    __filter = lambda _, n: (n[0] != '_' and n.endswith('Error'))
    __convert = lambda _, n: '_'.join(t.lower() for t in n[:-1])
    __pattern = re.compile('[A-Z][^A-Z]*')
    __inner_classes_pattern = re.compile(r'    class ([^\s]+Error)\(.*')

    def __init__(self, *args, **kwds):
        f = self.__filter
        c = self.__convert
        p = self.__pattern

        invariants = dict(
            (c(t), getattr(self, n)) for (n, t) in [
                (n, p.findall(n)) for n in filter(f, dir(self))
            ]
        )

        names = dict((v.__name__, k) for (k, v) in invariants.items())

        cls = self.__class__
        classname = cls.__name__
        filename = inspect.getsourcefile(cls)
        lines = linecache.getlines(filename)
        lines_len = len(lines)
        prefix = 'class %s(' % classname
        found = False
        for i in range(lines_len):
            line = lines[i]
            if prefix in line:
                found = i
                break

        if not found:
            raise IOError('could not find source code for class')

        block = inspect.getblock(lines[found:])
        text = ''.join(block)
        classes = self.__inner_classes_pattern

        order = [
            (i, names[n]) for (i, n) in enumerate(classes.findall(text))
        ]


        self._invariants = invariants
        self._invariant_names = names
        self._invariant_order = order

        self._invariants_processed = list()

    def __setattr__(self, name, new_value):
        object.__setattr__(self, name, new_value)
        if hasattr(self, '_invariants') and name in self._invariants:
            invariant_class = self._invariants[name]
            existing = (self._existing_ or (None, None))
            (existing_obj_attr, dependencies) = existing
            if not dependencies or name in dependencies:
                invariant = invariant_class(self, name, new_value)
                self._invariants_processed.append(invariant)
                return

            # All necessary dependencies have been set (assuming the class has
            # correctly ordered the invariant classes), so set the object's
            # '_existing' attribute, which signals to future invariants that
            # they are to begin checking existing values during the the normal
            # setattr interception and validation.
            if not self._existing:
                self._existing = getattr(self, existing_obj_attr)

            invariant = invariant_class(self, name, new_value)

            # And make a note of the existing value as well as the new value
            # in the 'processed' list.  This is done for convenience of the
            # subclass that may want easy access to the old/new values down
            # the track (i.e. for logging purposes).
            old_value = invariant._existing_str
            self._invariants_processed.append(invariant)


class ProcessWrapper(object):
    def __init__(self, exe, *args, **kwds):
        self.exe      = exe
        self.rc       = int()
        self.cwd      = None
        self.wait     = True
        self.error    = str()
        self.output   = str()
        self.ostream  = kwds.get('ostream', sys.stdout)
        self.estream  = kwds.get('estream', sys.stderr)
        self.verbose  = kwds.get('verbose', False)
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

        self.p = Popen(self.cmd, executable=self.exe, cwd=self.cwd,
                       stdin=PIPE, stdout=PIPE, stderr=PIPE)
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
