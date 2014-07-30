
#===============================================================================
# Imports
#===============================================================================

from evn.path import (
    format_dir,
    PathMatcher,
)

from evn.util import (
    ConfigList,
    ConfigDict,
)

#===============================================================================
# Classes
#===============================================================================
class RootDetails(object):
    def __init__(self, **kwds):
        singular_root_types = kwds.get(
            'singular_root_types', (
                'tag',
                'trunk',
                'branch',
                'absolute',
                'unknown',
            )
        )

        for s in singular_root_types:
            setattr(self, 'is_' + s, False)

        self.version = None
        self.rootmatcher = None

        for (k, v) in kwds.items():
            if k == 'singular_root_types':
                continue
            setattr(self, k, v)

        setattr(self, 'is_' + self.root_type, True)

        if self.is_absolute:
            assert self.root_path == '/'

        if not self.is_absolute and not self.is_unknown:
            assert self.root_name

    def __repr__(self):
        return '%s<%s>' % (self.__class__.__name__, ', '.join(
            "%s='%s'" % (k.replace('root_', ''), v) for (k, v) in (
                (d, getattr(self, d)) for d in dir(self) if d[0] != '_'
            )
        ))

AbsoluteRootDetails = RootDetails(root_type='absolute', root_path='/')

class RootPathMatcher(PathMatcher):
    def get_root_details(self, path):
        results = self.get_root_details_tuple(path)
        if results:
            (root_path, root_type, root_name) = results
            root_details = RootDetails(
                root_name=root_name,
                root_type=root_type,
                root_path=root_path,
            )
        else:
            root_details = RootDetails(
                root_path=path,
                root_type='unknown',
            )
        return root_details

class SimpleRootMatcher(object):
    def __init__(self, roots):
        assert isinstance(roots, set)

        self.__version = 0
        self.__roots = set()
        self.__roots_removed = set()
        self.__root_details = dict()
        self.__root_dirs_by_length = dict()
        self.__reversed_root_dir_lengths = None

        self.__pathmatcher = RootPathMatcher()

        for p in roots:
            self.add_root_path(p)

    @property
    def version(self):
        return self.__version

    @property
    def roots(self):
        return self.__roots

    @property
    def roots_removed(self):
        return self.__roots_removed

    @property
    def pathmatcher(self):
        return self.__pathmatcher

    @property
    def reversed_root_dir_lengths(self):
        if self.__reversed_root_dir_lengths is None:
            lengths = reversed(sorted(self.__root_dirs_by_length.keys()))
            # We add one to each of the lengths because get_root_details(),
            # the primary consumer of this property, expects lengths to be
            # representative of how many '/' slashes there are in a path, not
            # how many directory parts are in the path (which will always be
            # one less).
            self.__reversed_root_dir_lengths = [ l+1 for l in lengths ]
        return self.__reversed_root_dir_lengths

    def add_root_path(self, path):
        """
        >>> rm = SimpleRootMatcher(set(['/trunk/']))

        >>> rm.add_root_path('/trunk/')
        Traceback (most recent call last):
            ...
        AssertionError

        >>> rm.add_root_path('/trunk/foo/')
        Traceback (most recent call last):
            ...
        AssertionError

        >>> rm.add_root_path('//foo/')
        Traceback (most recent call last):
            ...
        AssertionError

        >>> rm.add_root_path('//')
        Traceback (most recent call last):
            ...
        AssertionError

        >>> rm.add_root_path('/trunk/foo/trunk/')
        Traceback (most recent call last):
            ...
        AssertionError
        """

        p = path
        assert (
            p == format_dir(p) and
            p not in self.__roots and
            p.count('/') >= 2 and p != '//'
        )

        # Lop off the first and last empty elements via the [1:-1] splice.
        dirs = p.split('/')[1:-1]
        length = len(dirs)
        assert length >= 1

        # Make sure there are no overlapping roots.  For example, if we're
        # adding the root '/src/foo/bar/trunk/', we make sure that none of
        # the following roots exist: '/src/foo/bar/', '/src/foo/', '/src/'.
        for i in range(length, 0, -1):
            roots = self.__root_dirs_by_length.get(i)
            if roots:
                s = '/%s/' % '/'.join(dirs[:i])
                #if s in self.__root_dirs_by_length[i]:
                #    import ipdb
                #    ipdb.set_trace()
                assert s not in self.__root_dirs_by_length[i]

        roots = self.__root_dirs_by_length.get(length)
        if roots is None:
            # Force reversed lengths to be recalculated when the property is
            # next accessed by get_root_details().
            self.__reversed_root_dir_lengths = None
            self.__root_dirs_by_length[length] = set()
        else:
            # Force a __nonzero__ test to catch if we're an empty set().
            assert roots
            assert p not in roots
            assert p not in self.__root_details

        self.__root_dirs_by_length[length].add(p)
        self.__roots.add(p)
        self.__version += 1

    def remove_root_path(self, path):
        p = path
        assert p in self.__roots
        length = p.count('/')-1
        assert length >= 1

        roots = self.__root_dirs_by_length[length]
        assert roots and p in roots
        roots.remove(p)
        if not roots:
            # Do extra cleanup if that was the last root at this length.
            del self.__root_dirs_by_length[length]
            self.__reversed_root_dir_lengths = None

        self.__roots.remove(p)
        if p in self.__root_details:
            del self.__root_details[p]

        self.__roots_removed.add(p)
        self.__version += 1

    def get_root_details(self, path):
        assert path and path[0] == '/'
        # The first element in the split will be '' because our path starts
        # with '/', so skip it via the [1:] slice.
        parts = path.split('/')[1:]
        parts_length = len(parts)
        assert parts_length >= 1

        if parts_length == 1:
            return AbsoluteRootDetails

        reversed_root_dir_lengths = self.reversed_root_dir_lengths

        use_unknown_root_details = (
            not self.__roots or
            parts_length < reversed_root_dir_lengths[-1]
        )

        if use_unknown_root_details:
            return RootDetails(
                root_type='unknown',
                root_path=path,
                version=self.version,
                rootmatcher=self,
            )

        root_name = parts[-1]
        if root_name == '':
            root_name = parts[-2]

        for r in reversed_root_dir_lengths:
            if r > parts_length:
                continue

            root_path = '/%s/' % '/'.join(parts[:r-1])
            if root_path in self.__roots:
                root_details = self.__root_details.get(root_path)
                if not root_details:
                    # The only thing PathMatcher will definitely get right is
                    # the root type, which is tricky when you've got ambiguous
                    # paths like /branches/trunk/ or /trunk/foo/tags/1.0 etc.
                    pm = self.pathmatcher
                    root_type = pm.get_root_details(root_path).root_type

                    # Treat unknown roots as branches.
                    if root_type == 'unknown':
                        root_type = 'branch'

                    root_details = RootDetails(
                        root_name=root_name,
                        root_path=root_path,
                        root_type=root_type,
                        version=self.version,
                        rootmatcher=self,
                    )
                    self.__root_details[root_path] = root_details

                return root_details

        # If we get this far, the path doesn't match any of our known root
        # base dirs, so return unknown.
        return RootDetails(
            root_type='unknown',
            root_path=path,
            version=self.version,
            rootmatcher=self,
        )

    def find_roots_under_path(self, path):
        """
        Return a list of all the roots that start with the path @path.
        """
        p = path
        assert p and p[0] == '/' and p[-1] == '/'
        return [ r for r in self.__roots if r != p and r.startswith(p) ]

    def __repr__(self):
        return repr(self.__roots)

class Roots(ConfigDict):

    def __init__(self, parent, roots):
        ConfigDict.__init__(self, parent, 'roots', roots)

    def __getitem__(self, name):
        i = dict.__getitem__(self, name)
        return Root(self, name, i)

class Root(ConfigDict):

    def _add_copy(self, copied_from_rev, copied_to_path, rev):
        copy = (copied_to_path, rev)
        if 'copies' in self:
            copies = self['copies']
            if copied_from_rev in copies:
                l = copies[copied_from_rev]
                if (copied_to_path, rev) not in l:
                    l.append((copied_to_path, rev))
            else:
                copies[copied_from_rev] = [ (copied_to_path, rev), ]
        else:
            ConfigDict.__setitem__(
                self,
                'copies',
                { copied_from_rev : [ (copied_to_path, rev), ] }
            )

# vim:set ts=8 sw=4 sts=4 tw=78 et:
