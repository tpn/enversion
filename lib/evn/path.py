#===============================================================================
# Imports
#===============================================================================
import os
import re

from os.path import (
    join,
    abspath,
    dirname,
    normpath,
)

#===============================================================================
# Helper Methods
#===============================================================================
def get_base_dir(path):
    p = path
    pc = p.count('/')
    assert p and p[0] == '/' and pc >= 1
    if p == '/' or pc == 1 or (pc == 2 and p[-1] == '/'):
        return '/'

    assert pc >= 2
    return dirname(p[:-1] if p[-1] == '/' else p) + '/'

def reduce_path(p):
    assert p and p[0] == '/'
    r = list()
    end = p.rfind('/')
    while end != -1:
        r.append(p[:end+1])
        end = p.rfind('/', 0, end)
    return r

def join_path(*args):
    return abspath(normpath(join(*args)))

def format_path(path, is_dir=None):
    """
    >>> format_path('src', True)
    '/src/'

    >>> format_path('src', False)
    '/src'

    >>> format_path('src/foo', True)
    '/src/foo/'

    >>> format_path('///src///foo///mexico.txt//', False)
    '/src/foo/mexico.txt'

    >>> format_path('///src///foo///mexico.txt//')
    '/src/foo/mexico.txt/'

    >>> format_path('///src///foo///mexico.txt')
    '/src/foo/mexico.txt'

    >>> format_path(r'\\the\\quick\\brown\\fox.txt', False)
    '/\\\\the\\\\quick\\\\brown\\\\fox.txt'

    >>> format_path('/')
    '/'

    >>> format_path('/', True)
    '/'

    >>> format_path('/', False)
    Traceback (most recent call last):
        ...
    AssertionError

    >>> format_path('/a')
    '/a'

    >>> format_path('/ab')
    '/ab'

    >>> format_path(None)
    Traceback (most recent call last):
        ...
    AssertionError

    >>> format_path('//')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> format_path('/', True)
    '/'

    # On Unix, '\' is a legitimate file name.  Trying to wrangle the right
    # escapes when testing '/' and '\' combinations is an absolute 'mare;
    # so we use ord() instead to compare numerical values of characters.
    >>> _w = lambda p: [ ord(c) for c in p ]
    >>> b = chr(92) # forward slash
    >>> f = chr(47) # backslash
    >>> foo = [102, 111, 111] # ord repr for 'foo'
    >>> b2 = b*2
    >>> _w(format_path('/'+b))
    [47, 92]

    >>> _w(format_path('/'+b2))
    [47, 92, 92]

    >>> _w(format_path('/'+b2, is_dir=False))
    [47, 92, 92]

    >>> _w(format_path('/'+b2, is_dir=True))
    [47, 92, 92, 47]

    >>> _w(format_path(b2*2))
    [47, 92, 92, 92, 92]

    >>> _w(format_path(b2*2, is_dir=True))
    [47, 92, 92, 92, 92, 47]

    >>> _w(format_path('/foo/'+b))
    [47, 102, 111, 111, 47, 92]

    >>> _w(format_path('/foo/'+b, is_dir=False))
    [47, 102, 111, 111, 47, 92]

    >>> _w(format_path('/foo/'+b, is_dir=True))
    [47, 102, 111, 111, 47, 92, 47]

    """
    assert (
        path and
        path not in ('//', '///') and
        is_dir in (True, False, None)
    )

    if path == '/':
        assert is_dir in (True, None)
        return '/'

    p = path
    while True:
        if re.search('//', p):
            p = p.replace('//', '/')
        else:
            break

    if p == '/':
        assert is_dir in (True, None)
        return '/'

    if p[0] != '/':
        p = '/' + p

    if is_dir is True:
        if p[-1] != '/':
            p += '/'
    elif is_dir is False:
        if p[-1] == '/':
            p = p[:-1]

    return p

def format_dir(path):
    return format_path(path, is_dir=True)

def format_file(path):
    return format_path(path, is_dir=False)

def assert_no_file_dir_clash(paths):
    """
    >>> assert_no_file_dir_clash('lskdjf')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> assert_no_file_dir_clash(False)
    Traceback (most recent call last):
        ...
    AssertionError

    >>> assert_no_file_dir_clash(['/src/', '/src/'])
    Traceback (most recent call last):
        ...
    AssertionError

    >>> assert_no_file_dir_clash(['/src', '/src/'])
    Traceback (most recent call last):
        ...
    AssertionError

    >>> assert_no_file_dir_clash(['/sr', '/src/', '/srcb/'])
    >>>

    """
    assert paths and hasattr(paths, '__iter__')
    seen = set()
    for p in paths:
        assert not p in seen
        seen.add(p)

    assert all(
        (p[:-1] if p[-1] == '/' else p + '/') not in seen
            for p in paths
    )


def get_root_path(paths):
    """
    Given a list of paths (directories or files), return the root directory or
    an empty string if no root can be found.

    >>> get_root_path(['/src/', '/src/trunk/', '/src/trunk/test.txt'])
    '/src/'
    >>> get_root_path(['/src/', '/src/trk/', '/src/trk/test.txt', '/src/a'])
    '/src/'
    >>> get_root_path(['/', '/laksdjf', '/lkj'])
    '/'
    >>> get_root_path(['/'])
    '/'
    >>> get_root_path(['/a'])
    '/'
    >>>
    >>> get_root_path(['/src/trunk/foo.txt', '/src/tas/2009.01.00/foo.txt'])
    '/src/'
    >>> get_root_path(['/src/branches/foo/'])
    '/src/branches/foo/'

    >>> get_root_path(['',])
    Traceback (most recent call last):
        ...
    AssertionError

    >>> get_root_path(['lskdjf',])
    Traceback (most recent call last):
        ...
    AssertionError

    >>> get_root_path(['src/trunk/',])
    Traceback (most recent call last):
        ...
    AssertionError

    >>> get_root_path(['/src/trunk/', '/src/trunk'])
    Traceback (most recent call last):
        ...
    AssertionError
    """
    assert (
        hasattr(paths, '__iter__')   and
        #len(paths) >= 1              and
        all(d and d[0] == '/' for d in paths)
    )

    #if len(paths) == 1 and paths[0] == '/':
    #    return '/'

    def _parts(p):
        parts = p.split('/')
        return parts if p[-1] == '/' else parts[:-1]

    paths = [ format_path(p) for p in paths ]
    assert_no_file_dir_clash(paths)

    common = _parts(paths[0])

    for j in range(1, len(paths)):
        parts =  _parts(paths[j])
        for i in range(len(common)):
            if i == len(parts) or common[i] != parts[i]:
                del common[i:]
                break
    if not common or (len(common) == 1 and common[0] == ''):
        return '/'

    return format_dir('/'.join(common))


def build_tree(tree, prefix=''):
    jp = lambda k: join_path(prefix, k)
    for (f, d) in ((jp(k), v) for (k, v) in tree.items()):
        if not d:
            try:
                os.makedirs(f)
            except OSError:
                pass
        else:
            try:
                os.makedirs(dirname(f))
            except OSError:
                pass
            with open(f, 'w') as fp:
                fp.write(d)

def extract_component_name(path):
    """
    >>> extract_component_name('/foo/trunk/bar.txt')
    'foo'
    >>> extract_component_name('/foo/trunk/')
    'foo'
    >>> extract_component_name('/foo/branches/1.x/abcd.txt')
    'foo'

    >>> extract_component_name('/foo')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> extract_component_name('/foo/')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> extract_component_name('foo/')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> extract_component_name('/foo')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> extract_component_name('/foo/trunk')
    Traceback (most recent call last):
        ...
    AssertionError

    >>> extract_component_name(None)
    Traceback (most recent call last):
        ...
    AssertionError

    >>> extract_component_name('')
    Traceback (most recent call last):
        ...
    AssertionError

    """
    assert path and path[0] == '/'
    assert path.count('/') >= 3
    return path[1:path.find('/', 2)]


#===============================================================================
# Path Matching
#===============================================================================
class PathMatcherConfig(object):
    singular    = tuple()
    plural      = tuple()
    match       = tuple()
    ending      = tuple()

class DefaultPathMatcherConfig(PathMatcherConfig):
    singular = ('tag',        'branch',   'trunk')
    plural   = ('tags',       'branches', 'trunks')
    match    = ('tags',       'branches', 'trunk')
    ending   = ('([^/]+)/',   '([^/]+)/', None)

class PathMatcher(object):

    def __init__(self, config=None, *args, **kwds):
        if not config:
            config = DefaultPathMatcherConfig

        self.__dict__.update(
            (k, getattr(config, k)) for k in dir(config)
                if not k.startswith('_')
        )

        self.singular_to_plural = dict()
        self.plural_to_singular = dict()

        data = zip(self.singular, self.plural, self.match, self.ending)
        for (singular, plural, match, ending) in data:
            setattr(self, plural, [])
            self.singular_to_plural[singular] = plural
            self.plural_to_singular[plural] = singular
            p = '.+?%s/' % match
            if ending:
                p += ending
            getattr(self, plural).append(p)

        functions = list()
        for (s, p) in zip(self.singular, self.plural):
            functions += [
                (p, 'is_%s' % s, '_is_xxx'),
                (p, 'get_%s' % s, '_get_xxx'),
                (p, 'is_%s_path' % s, '_is_xxx_path'),
                (p, 'get_%s_path' % s, '_get_xxx_path'),
                (p, 'find_%s_paths' % s, '_find_xxx_paths'),
            ]

        class _method_wrapper(object):
            """Helper class for wrapping our key (is|get|find)_xxx methods."""
            def __init__(self, **kwds):
                self.__dict__.update(**kwds)

            def __call__(self, paths):
                return getattr(self.s, self.f)(paths, self.p)

        for (p, n, f) in functions:
            self.__dict__.setdefault(f + '_methods', []).append(n)
            setattr(self, n, _method_wrapper(s=self, p=p, n=n, f=f))

    def _get_xxx(self, path, xxx):
        assert isinstance(path, str)
        for pattern in getattr(self, xxx):
            found = re.findall(pattern + '$', path)
            if found:
                return found

    def _is_xxx(self, path, xxx):
        return bool(self._get_xxx(path, xxx))

    def _get_xxx_path(self, path, xxx):
        assert isinstance(path, str)
        for pattern in getattr(self, xxx):
            found = re.findall(pattern, path)
            if found:
                return found

    def _is_xxx_path(self, path, xxx):
        return bool(self._get_xxx_path(path, xxx))

    def _find_xxx_paths(self, paths, xxx):
        assert isinstance(paths, (list, tuple))
        f = dict()
        for pattern in getattr(self, xxx):
            for path in paths:
                m = re.search(pattern, path)
                if m:
                    f.setdefault('/'.join(m.groups()), []).append(m.group(0))
        return f

    def is_unknown_orig(self, path):
        """
        Returns true if all the is_xxx methods return false.
        """
        return all(
            not getattr(self, attr)(path)
                for attr in dir(self)
                    if attr != 'is_unknown' and
                       attr.startswith('is_') and
                       not attr.endswith('_path')
        )

    def is_unknown(self, path):
        """
        Returns true if all the is_xxx methods return false.
        """
        return all(
            not getattr(self, method_name)(path)
                for method_name in self._is_xxx_methods
        )

    def get_root_dir(self, path):
        """
        >>> pm = PathMatcher()
        >>> pm.get_root_dir('/src/trunk/foo.txt')
        '/src/trunk/'
        >>> pm.get_root_dir('/src/trunk/')
        '/src/trunk/'
        >>> pm.get_root_dir('/src/trunk/foo/bar/mexico/tijuana.txt')
        '/src/trunk/'
        >>> pm.get_root_dir('/src/branches/GLB02030120-pricing/java/Foo.java')
        '/src/branches/GLB02030120-pricing/'
        >>> pm.get_root_dir('/src/joe.txt')
        >>>
        >>> pm.get_root_dir('/src/branches')
        >>>
        >>> pm.get_root_dir('/src/branches/')
        >>>
        >>> pm.get_root_dir('/src/tags')
        >>>
        >>> pm.get_root_dir('/src/tags/')
        >>>
        >>> pm.get_root_dir('/src/trunk')
        >>>
        >>> pm.get_root_dir('/src/trunk/trunk')
        '/src/trunk/'
        >>> pm.get_root_dir('/src/trunk/trunk/')
        '/src/trunk/'
        >>> pm.get_root_dir('/src/trunk/foobar/src/trunk/test.txt')
        '/src/trunk/'
        >>> pm.get_root_dir('/branches/foo/')
        '/branches/foo/'
        >>> pm.get_root_dir('/branches/trunk/')
        '/branches/trunk/'
        >>> pm.get_root_dir('/branches/trunk/foo')
        '/branches/trunk/'
        >>> pm.get_root_dir('/tags/trunk/')
        '/tags/trunk/'
        >>> pm.get_root_dir('/tags/trunk/foo')
        '/tags/trunk/'
        >>>
        """
        assert isinstance(path, str)
        assert path[0] == '/' if path else True
        root = None
        min_root_length = None
        for plural in self.plural:
            patterns = [
                '^(%s)(.*)$' % p.replace('(', '').replace(')', '')
                    for p in getattr(self, plural)
            ]
            for pattern in patterns:
                match = re.search(pattern, path)
                if match:
                    groups = match.groups()
                    assert len(groups) in (1, 2)
                    r = groups[0]
                    l = len(r)
                    if root is None:
                        root = r
                        min_root_length = l
                    else:
                        # The only way we could possibly have multiple matches
                        # with the exact same length for the root path is for
                        # paths like '/branches/trunk/' or '/tags/trunk/'.
                        if l == min_root_length:
                            assert r.endswith('trunk/')
                        elif l < min_root_length:
                            root = r
                            min_root_length = l
                        else:
                            assert l > min_root_length

        return root

    def get_root_details_tuple(self, path):
        """
        >>> pm = PathMatcher()
        >>> pm.get_root_details_tuple('/src/trunk/')
        ('/src/trunk/', 'trunk', 'trunk')
        >>> pm.get_root_details_tuple('/src/trunk/trunk')
        ('/src/trunk/', 'trunk', 'trunk')
        >>> pm.get_root_details_tuple('/src/trunk/branches/foo/')
        ('/src/trunk/', 'trunk', 'trunk')

        >>> pm.get_root_details_tuple('/src/branches/GLB02051234/')
        ('/src/branches/GLB02051234/', 'branch', 'GLB02051234')
        >>> pm.get_root_details_tuple('/src/branches/foo/tags')
        ('/src/branches/foo/', 'branch', 'foo')
        >>> pm.get_root_details_tuple('/src/branches/foo/tags/1.0')
        ('/src/branches/foo/', 'branch', 'foo')
        >>> pm.get_root_details_tuple('/src/branches/foo/tags/1.0/')
        ('/src/branches/foo/', 'branch', 'foo')
        >>> pm.get_root_details_tuple('/branches/foo/')
        ('/branches/foo/', 'branch', 'foo')
        >>> pm.get_root_details_tuple('/branches/trunk/')
        ('/branches/trunk/', 'branch', 'trunk')

        >>> pm.get_root_details_tuple('/src/tags/2009.01.1/')
        ('/src/tags/2009.01.1/', 'tag', '2009.01.1')
        >>> pm.get_root_details_tuple('/src/tags/2009.01.1/asldkjf/lkjd/')
        ('/src/tags/2009.01.1/', 'tag', '2009.01.1')
        >>> pm.get_root_details_tuple('/src/tags/2009.01.1/lkjf/ljd/test.txt')
        ('/src/tags/2009.01.1/', 'tag', '2009.01.1')
        >>> pm.get_root_details_tuple('/tags/1.0.0/')
        ('/tags/1.0.0/', 'tag', '1.0.0')
        >>> pm.get_root_details_tuple('/tags/trunk/')
        ('/tags/trunk/', 'tag', 'trunk')
        >>> pm.get_root_details_tuple('/')
        ('/', 'absolute', '/')
        """
        if path == '/':
            return ('/', 'absolute', '/')
        found = False
        matches = list()
        root_dir = self.get_root_dir(path)
        if not root_dir:
            return
        root_type = None
        root_name = None
        for method_name in self._get_xxx_methods:
            match = getattr(self, method_name)(root_dir)
            if match:
                if found:
                    # Yet more hackery to support crap like /branches/trunk/
                    # and /tags/trunk/.  We're relying on the fact that the
                    # 'get_trunks' method will be called last.
                    assert 'trunk' in method_name
                    continue
                found = True
                assert len(match) == 1
                m = match[0]
                if m == root_dir:
                    # This feels a bit hacky but eh...  Basically, if our
                    # regex matched one root dir, then the thing we're
                    # matching didn't supply an ending regex, so we use the
                    # last directory name in the path as the root name.  In
                    # practise, this is used for matching trunk paths and
                    # returning 'trunk' as the root_name, versus, say,
                    # returning 2009.01 if we matched against /tags/2009.01.
                    assert m[-1] == '/'
                    root_name = m[m[:-1].rfind('/')+1:-1]
                else:
                    root_name = m
                root_type = method_name.replace('get_', '')

        if not found:
            return None
        else:
            assert (
                root_type in self.singular and
                root_dir and root_name
            )
            return (root_dir, root_type, root_name)

# vim:set ts=8 sw=4 sts=4 tw=78 et:
