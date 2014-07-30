# This file is a dumping ground for old/deprecated/scratch code.  It isn't
# intended to ever be even close to a working/parseable state.  Go nuts.

def __init_svn_libraries(g):
    import svn
    import svn.fs
    import svn.ra
    import svn.core
    import svn.delta
    import svn.repos
    import svn.client

    from svn.core import SVN_AUTH_PARAM_DEFAULT_USERNAME
    from svn.core import SVN_PROP_EXTERNALS
    from svn.core import SVN_PROP_MERGEINFO
    from svn.core import SVN_PROP_REVISION_AUTHOR
    from svn.core import SVN_INVALID_REVNUM

    from svn.core import svn_auth_open
    from svn.core import svn_auth_set_parameter
    from svn.core import svn_auth_get_username_provider

    from svn.core import svn_mergeinfo_diff
    from svn.core import svn_mergeinfo_parse
    from svn.core import svn_rangelist_to_string

    from svn.core import svn_node_dir
    from svn.core import svn_node_file
    from svn.core import svn_node_none
    from svn.core import svn_node_unknown

    from svn.core import SubversionException

    g['svn'] = svn
    #g['svn.fs'] = svn.fs
    #g['svn.ra'] = svn.ra
    #g['svn.core'] = svn.core
    #g['svn.delta'] = svn.delta
    #g['svn.repos'] = svn.repos
    #g['svn.client'] = svn.client
    g['SVN_AUTH_PARAM_DEFAULT_USERNAME'] = SVN_AUTH_PARAM_DEFAULT_USERNAME
    g['SVN_PROP_EXTERNALS'] = SVN_PROP_EXTERNALS
    g['SVN_PROP_MERGEINFO'] = SVN_PROP_MERGEINFO
    g['SVN_PROP_REVISION_AUTHOR'] = SVN_PROP_REVISION_AUTHOR
    g['SVN_INVALID_REVNUM'] = SVN_INVALID_REVNUM
    g['svn_auth_open'] = svn_auth_open
    g['svn_auth_set_parameter'] = svn_auth_set_parameter
    g['svn_auth_get_username_provider'] = svn_auth_get_username_provider
    g['svn_mergeinfo_diff'] = svn_mergeinfo_diff
    g['svn_mergeinfo_parse'] = svn_mergeinfo_parse
    g['svn_rangelist_to_string'] = svn_rangelist_to_string
    g['svn_node_dir'] = svn_node_dir
    g['svn_node_file'] = svn_node_file
    g['svn_node_none'] = svn_node_none
    g['svn_node_unknown'] = svn_node_unknown

    g['svn_node_types'] = (
        svn_node_dir,
        svn_node_file,
        svn_node_none,
        svn_node_unknown,
    )

    g['SubversionException'] = SubversionException

def init_svn_libraries(g=None):
    failed = True
    if g is None:
        g = globals()
    try:
        __init_svn_libraries(g)
        failed = False
    except ImportError as e:
        pass

    if not failed:
        return

    msg = dedent("""\
        failed to import Python Subversion bindings.

        Make sure Python Subversion bindings are installed before continuing.

        If you *have* installed the bindings, your current shell environment
        isn't configured correctly.  You need to alter either your env vars
        (i.e. PATH, PYTHONPATH) or Python installation (lib/site-packages/
        svn-python.pth) such that the libraries can be imported.

        Re-run this command once you've altered your environment to determine
        if you've fixed the problem.  Alternatively, you can simply run the
        following from the command line:

            python -c 'from svn import core'

        If that doesn't return an error, the problem has been fixed.

        Troubleshooting tips:

            1. Is the correct Python version accessible in your PATH?  (Type
               'which python' to see which version is getting picked up.  If
               it is incorrect, alter your PATH accordingly.)

            2. Have the Python Subversion bindings been installed into the
               site-packages directory of the Python instance referred to
               above?  If they have, then this should work:

                    % python -c 'from svn import core'

               ....but it didn't work when we just tried it, so there is a
               problem with your Python site configuration.

            3. If the Python Subversion bindings have been installed into a
               different directory, there should be a file 'svn-python.pth'
               located in your Python 'lib/site-packages' directory that
               tells Python where to load the bindings from.

            4. If you know where the bindings are but can't alter your
               Python installation's site-packages directory, try setting
               PYTHONPATH instead.

            5. LDLIBRARYPATH needs to be set correctly on some platforms for
               Python to be able to load the Subversion bindings.
        """)

    raise ImportError(msg)

import re
class EventConverter(object):
    pattern = re.compile('[A-Z][^A-Z]*')
    def __init__(self, line):
        self.line = line
        (self.name, t) = self.line.split(' = ')
        self.text = t[1:-1]
        self.tokens = self.pattern.findall(self.name)
        self.lower = [ n.lower() for n in self.tokens ]
        for (i, t) in enumerate(self.tokens):
            if t == 'Mergeinfo':
                self.lower[i] = 'svn:mergeinfo'
        self.auto = ' '.join(self.lower)
        self.skip_desc = bool(self.auto == self.text)

        s = '\n'.join([
            'class %s(Event):' % self.name,
            '    _severity_ = EventType.Error',
        ])
        if not self.skip_desc:
            s += '\n    _desc_ = "%s"' % self.text

        self.as_class = s

class RepositoryConfig(dict):
    def __init__(self, repo):
        self._repo = repo
        self._propname_prefix = repo.conf.get('main', 'propname-prefix')
        self._propname_roots = repo.conf.get('main', 'propname-prefix')

        self._username = '%s (%s@$Rev: 83781 $)' % (
            self.__class__.__name__,
            os.path.abspath(__file__),
        )

        self._reload()

    def __repr__(self):
        # Override dict's representation and use object's, as it's far, far
        # less confusing to see this:
        #
        #   In [10]: evn.RepositoryConfig('foo')
        #   Out[11]: <evn.RepositoryConfig object at 0x02A1E290>
        #
        # Than this:
        #
        #   In [10]: evn.RepositoryConfig('foo')
        #   Out[11]: {}
        return object.__repr__(self)

    def __delattr__(self, name):
        if name.startswith('_'):
            return dict.__delattr__(name)
        else:
            return self._del(name)

    def __delitem__(self, name):
        if name.startswith('_'):
            return dict.__delitem__(name)
        else:
            return self._del(name)

    def __getattr__(self, name):
        if name.startswith('_'):
            return dict.__getattribute__(self, name)
        else:
            return self.__getitem__(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            dict.__setattr__(self, name, value)
        else:
            self._set(name, value)

    def __setitem__(self, name, value):
        if name.startswith('_'):
            dict.__setattr__(self, name, value)
        else:
            self._set(name, value)

    def _del(self, name, default=False, skip_reload=False):
        # Deleting a property is done by propset'ing a None value.
        self._set(name, None, default=default, skip_reload=skip_reload)

    def _format_propname(self, name):
        assert name and name[0] != '_'
        propname_prefix = self.conf.propname_prefix
        if not name.startswith(propname_prefix + ':'):
            return ':'.join((propname_prefix, name))
        else:
            return name

    def _unformat_propname(self, name):
        propname_prefix = self.conf.propname_prefix + ':'
        if name and name.startswith(propname_prefix):
            name = name[len(propname_prefix):]

        assert name and name[0] != '_'
        return name

    def _set(self, name, value, default=False, skip_reload=False):
        name = self._format_propname(name)

        def _try_convert(orig_value, propname, attempts):
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
                    return _try_convert(orig_value, propname, attempts)
                else:
                    raise ValueError(
                        "failed to convert property '%s' value: %s" % (
                            propname,
                            orig_value,
                        )
                    )


        attempts = itertools.count(0)
        value = _try_convert(value, name, itertools.count(0))

        commit_msg = '%s -> %s' % (name, value)
        ctx = create_simple_context(self._username)
        ctx.log_msg_func3 = svn.client.svn_swig_py_get_commit_log_func
        ctx.log_msg_baton3 = lambda *args: commit_msg

        svn.client.propset3(name, value, self._repo.uri,
                            svn.core.svn_depth_empty,
                            True, self._rev(), None, None, ctx)

        if not skip_reload:
            self._reload()

    def _rev(self):
        return svn.fs.youngest_rev(self._repo.fs)

    def _root(self):
        return svn.fs.revision_root(self._repo.fs, self._rev())

    def _proplist(self):
        return svn.fs.node_proplist(self._root(), '')

    def _reload(self):
        d = dict()
        prefix = self.conf.propname_prefix
        for (key, value) in self._proplist().items():
            if not key.startswith(prefix):
                continue

            try:
                v = literal_eval(value)

            except:
                raise ValueError(
                    "invalid value for property '%s':\n%s" % (key, value)
                )

            d[self._unformat_propname(key)] = v

        # Add stubs for standard property names.
        for (key, value) in self._default.items():
            rawkey = self._unformat_propname(key)
            if not rawkey in d:
                if isinstance(value, dict):
                    value = ConfigDict(self, key, value)
                d[rawkey] = value
            if not key in d:
                d[key] = None

        self.clear()
        self.update(d)

    @property
    def _default(self):
        return dict()

def create_simple_context(username):
    c = svn.client.create_context()
    c.auth_baton = svn_auth_open([svn_auth_get_username_provider()])
    args = (c.auth_baton, SVN_AUTH_PARAM_DEFAULT_USERNAME, username)
    svn_auth_set_parameter(*args)
    return c

_repo_fs_cache = dict()
def get_repo_fs(path):
    path = os.path.abspath(path)
    global _repo_fs_cache
    if path not in _repo_fs_cache:
        _repo_fs_cache[path] = svn.repos.fs(svn.repos.open(path))
    return _repo_fs_cache[path]

class ProcessRevOrTxnCommand(RepositoryCommand):
    repo = None
    rev_or_txn = None

    @requires_context
    def run(self):
        RepositoryCommand.run(self)
        assert self.rev_or_txn

        with RepositoryRevOrTxn(**k) as r:
            r.process_rev_or_txn(rev_or_txn)

class RunProcessCommand(Command):
    def __init__(self, ostream, estream):
        Command.__init__(self, ostream, estream)
        self.__process = None
        self.exe  = None
        self.args = list()
        self.kwds = dict()
        self.verbose = False

    def run(self):
        assert self.exe and isinstance(self.exe, str)
        k = Dict()
        k.ostream = self.ostream
        k.estream = self.estream
        k.verbose = self.verbose
        p = ProcessWrapper(self.exe, **k)
        p.exception_class = CommandError
        p.execute(*self.args, **self.kwds)
        assert p.rc == 0


#===============================================================================
# Wild refactoring...
#===============================================================================

def editor_method_orig(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        obj = args[0]
        obj.results.append((f.func_name, args[1:-1]))
        return f(*args, **kwds)
    return wrapper

def editor_method(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        # args[1:-1] = grab everything after the first self argument and
        # before the final pool argument.
        args[0].results.append((f.func_name,) + tuple(args[1:-1]))
        return f(*args, **kwds)
    return wrapper

def proxy_method(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        # args[1:-1] = grab everything after the first self argument and
        # before the final pool argument.
        #args[0].parent.results.append((f.func_name,) + tuple(args[1:-1]))
        getattr(args[0].parent, f.func_name)(*args[1:])
        return f(*args, **kwds)
    return wrapper

def slash_prefix(f):
    @wraps(f)
    def wrapper(*a, **k):
        return f(*((a[0],) + ('/' + a[1],) + tuple(a[2:-1])), **k)
    return wrapper

def slash_prefix_and_suffix(f):
    @wraps(f)
    def wrapper(*a, **k):
        return f(*((a[0],) + ('/' + a[1] + '/',) + tuple(a[2:-1])), **k)
    return wrapper

import textwrap
RESULTS_DB_SQL = textwrap.dedent("""\
    create table action (
        id integer primary key asc,
        name text not null,
        path text not null
    );

    create table add_entry (
        id integer primary key asc,
        path text not null,
        copied_from_path text,
        copied_from_rev integer
    );

    create table delete_entry (
        id integer primary key asc,
        path text not null
    );

    create table change_prop (
        id integer primary key asc,
        path text not null,
        name text not null,
        value text
    );

    create table apply_textdelta (
        id integer primary key asc,
        path text not null,
        checksum text not null
    );

    create table close_file (
        id integer primary key asc,
        path text not null,
        checksum text not null
    );

""")

def save_editor_results_to_db(results, db_path):
    import sqlite3
    con = sqlite3.connect(db_path)
    con.isolation_level = None

    con.executescript(RESULTS_DB_SQL)

    sql = "insert into action values (?, ?, ?)"
    data = (r[0:3] for r in results)
    con.executemany(sql, data)

    f = lambda r: (r[0],) + tuple(r[2:])
    sql = "insert into add_entry values (?, ?, ?, ?)"
    data = (f(r) for r in results if r[1][1] == 'd')
    con.executemany(sql, data)

    sql = "insert into delete_entry values (?, ?)"
    data = (f(r) for r in results if r[1][0] == 'd')
    con.executemany(sql, data)

    sql = "insert into change_prop values (?, ?, ?, ?)"
    data = (f(r) for r in results if r[1][1] == 'h')
    con.executemany(sql, data)

    sql = "insert into apply_textdelta values (?, ?, ?)"
    data = (f(r) for r in results if r[1][1] == 'p')
    con.executemany(sql, data)

    sql = "insert into close_file values (?, ?, ?)"
    data = (f(r) for r in results if r[1][1] == 'l')
    con.executemany(sql, data)

    return con

class ChangeSetEditorBasic(object):
    def __init__(self, results):
        self.results = results

    @editor_method
    def set_target_revision(self, target_rev, pool=None):
        pass

    @editor_method
    def open_root(self, base_rev, dir_pool=None):
        return None

    @slash_prefix
    @editor_method
    def delete_entry(self, path, rev, parent, pool=None):
        pass

    @slash_prefix_and_suffix
    @editor_method
    def add_directory(self, path, parent, copied_from_path,
                      copied_from_rev, dir_pool=None):
        return path

    @slash_prefix_and_suffix
    @editor_method
    def open_directory(self, path, parent, base_rev, dir_pool=None):
        return path

    @editor_method
    def change_dir_prop(self, change, name, value, pool=None):
        pass

    @editor_method
    def close_directory(self, change, pool=None):
        pass

    @slash_prefix
    @editor_method
    def add_file(self, path, parent, copied_from_path,
                 copied_from_rev, file_pool=None):
        return path

    @slash_prefix
    @editor_method
    def open_file(self, path, parent, base_rev, file_pool=None):
        return path

    @editor_method
    def apply_textdelta(self, change, base_checksum, pool=None):
        return None

    @editor_method
    def change_file_prop(self, change, name, value, pool=None):
        pass

    @editor_method
    def close_file(self, change, text_checksum, pool=None):
        pass

    @editor_method
    def close_edit(self, pool=None):
        pass

    @editor_method
    def abort_edit(self, pool=None):
        pass

class ChangeSetEditorProxy(object):
    def __init__(self, parent):
        self.parent = parent

    def set_target_revision(self, target_rev, pool=None):
        pass

    def open_root(self, base_rev, dir_pool=None):
        return None

    @slash_prefix
    @proxy_method
    def delete_entry(self, path, rev, parent, pool=None):
        pass

    @slash_prefix_and_suffix
    #@convert_args(path=1, is_dir=True, ignore=2)
    @proxy_method
    def add_directory(self, path, parent, copied_from_path,
                      copied_from_rev, dir_pool=None):
        return path

    @slash_prefix_and_suffix
    def open_directory(self, path, parent, base_rev, dir_pool=None):
        return path

    @proxy_method
    def change_dir_prop(self, change, name, value, pool=None):
        pass

    def close_directory(self, path, pool=None):
        pass

    @slash_prefix
    @proxy_method
    def add_file(self, path, parent, copied_from_path,
                 copied_from_rev, file_pool=None):
        return path

    @slash_prefix
    def open_file(self, path, parent, base_rev, file_pool=None):
        return path

    @proxy_method
    def apply_textdelta(self, path, base_checksum, pool=None):
        return None

    @proxy_method
    def change_file_prop(self, path, name, value, pool=None):
        pass

    @proxy_method
    def close_file(self, path, text_checksum, pool=None):
        pass

    @proxy_method
    def close_edit(self, pool=None):
        pass

    @proxy_method
    def abort_edit(self, pool=None):
        pass


class ChangeSetEditor(object):
    def __init__(self, results):
        self.results = results
        self.counter = itertools.count(0)
        self.modify = dict()
        self.copied_from = dict()
        self.copied_files = dict()
        self.copied_dirs  = dict()
        self.pending_deletes = dict()

    def set_target_revision(self, target_rev, pool=None):
        pass

    def open_root(self, base_rev, dir_pool=None):
        return None

    def delete_entry(self, path, rev, parent, pool=None):
        count = self.counter.next()
        assert path not in self.pending_deletes
        self.pending_deletes[path] = count
        self.results.append((
            count,
            'remove',
            '/' + path
        ))

    def add_directory(self, path, parent, copied_from_path,
                      copied_from_rev, dir_pool=None):
        assert copied_from_path and copied_from_rev != -1
        path = '/' + path + '/'

        count = self.counter.next()
        assert path not in self.copied_dirs
        self.copied_dirs[count] = path

        self.copied_from.setdefault(copied_from_path, {})     \
                        .setdefault(copied_from_rev,  set())  \
                        .add(count)

        dpath = path[:-1]
        ix = self.pending_deletes.get(dpath, None)
        if ix is not None:
            if ix == count-1:
                self.results[ix] = (ix, 'remove', path)
                del self.pending_deletes[dpath]

        self.results.append((
            count,
            'copy',
            path,
            copied_from_path + '/',
            copied_from_rev,
        ))

        return path

    def open_directory(self, path, parent, base_rev, dir_pool=None):
        return '/' + path + '/'

    def change_dir_prop(self, path, name, value, pool=None):
        self.results.append((
            self.counter.next(),
            'propchange',
            path,
            name,
            value
        ))

        assert not self.is_replace
        if self.old_value == self.new_value:
            # Yup, this can happen.
            return ExtendedPropertyChangeType.\
                PropertyChangedButOldAndNewValuesAreSame
        elif self.new_value is not None:
            if self.old_value is None:
                if self.new_value != '':
                    return ExtendedPropertyChangeType.\
                        PropertyCreatedWithValue
                else:
                    return ExtendedPropertyChangeType.\
                        PropertyCreatedWithoutValue
            elif self.old_value != '':
                if self.new_value != '':
                    return ExtendedPropertyChangeType.\
                        ExistingPropertyValueChanged
                else:
                    return ExtendedPropertyChangeType.\
                        ExistingPropertyValueCleared
            else:
                assert self.new_value
                return ExtendedPropertyChangeType.\
                    ValueProvidedForPreviouslyEmptyProperty
        else:
            assert self.old_value is not None
            return ExtendedPropertyChangeType.PropertyRemoved


    def close_directory(self, change, pool=None):
        pass

    def add_file(self, path, parent, copied_from_path,
                 copied_from_rev, file_pool=None):
        count = self.counter.next()
        assert path not in self.copied_files
        self.copied_files[count] = path
        self.results.append((
            count,
            'copy',
            '/' + path,
            copied_from_path,
            copied_from_rev,
        ))
        return '/' + path

    def open_file(self, path, parent, base_rev, file_pool=None):
        return '/' + path

    def change_file_prop(self, path, name, value, pool=None):
        self.results.append((
            self.counter.next(),
            'propchange',
            path,
            name,
            value
        ))

    def apply_textdelta(self, path, base_checksum, pool=None):
        if base_checksum:
            assert path not in self.modify
            count = self.counter.next()
            self.modify[path] = count
            self.results.append((
                count,
                'modify',
                path,
                base_checksum,
                None,
            ))
        return None

    def close_file(self, path, text_checksum, pool=None):
        if text_checksum:
            if not path in self.modify:
                self.results.append((
                    self.counter.next(),
                    'modify',
                    path,
                    None,
                    text_checksum,
                ))
            else:
                ix = self.modify[path]
                r = self.results[ix]
                self.results[ix] = (ix, 'modify', path, r[3], text_checksum)
                del r
                del self.modify[path]

    def close_edit(self, pool=None):
        self._cleanup()

    def abort_edit(self, pool=None):
        self._cleanup()

    def _cleanup(self):
        del self.counter
        assert not self.modify
        del self.modify

class ChangeSetDatabase(object):
    CREATE_SQL = textwrap.dedent("""\
        create table changeset (
            rev_or_txn text,
            rev int,
            txn text,
            base_rev int
        );

        create table action (
            id integer primary key asc,
            name text not null,
            path text not null
        );
        create index action_path_ix on action(path);

        create table copy (
            id integer primary key asc,
            path text not null,
            from_path text,
            from_rev integer
        );
        create index copy_path_ix on copy(path);

        create table replace (
            id integer primary key asc,
            path text not null,
            from_path text,
            from_rev integer
        );
        create index replace_path_ix on replace(path);

        create table remove (
            id integer primary key asc,
            path text not null
        );
        create index remove_path_ix on remove(path);

        create table propchange (
            id integer primary key asc,
            path text not null,
            name text not null,
            change_type integer not null,
            extended_change_type integer not null,
            old_value text,
            new_value text
        );
        create index propchange_path_ix on propchange(path);
        create index propchange_name_ix on propchange(name);

        create table mergeinfo (
            id integer primary key asc,
            path text not null,
            merged text,
            reverse_merged text
        );
        create index mergeinfo_path_ix on mergeinfo(path);

        create table modify (
            id integer primary key asc,
            path text not null,
            base_checksum text,
            checksum text
        );
        create index modify_path_ix on modify(path);

    """)

    def __init__(self, fs, root):

        self.__roots = dict()
        self.revprops = dict()

        pool = svn.core.Pool()

        self.fs = fs
        self.root = root
        self.pool = pool

        if svn.fs.is_revision_root(root):
            self.__is_rev = True
            self.__rev = svn.fs.revision_root_revision(root)
            self.__base_rev = self.rev - 1
            self.revprops = svn.fs.revision_proplist(fs, self.rev, pool)
        else:
            self.__is_rev = False
            self.__txn_name = svn.fs.txn_root_name(root, pool)
            self.__txn = svn.fs.open_txn(fs, self.txn_name, pool)
            self.__base_rev = svn.fs.txn_base_revision(self.txn)
            self.revprops = svn.fs.txn_proplist(self.txn, pool)

        if self.base_rev != -1:
            self.base_root = self._get_root(self.base_rev)

        self.__base_revprops = dict()

        self.results = list()
        cs = ChangeSetEditorProxy(self)

        editor_pool = svn.core.Pool(pool)
        replay_pool = svn.core.Pool(pool)

        (editor, baton) = svn.delta.make_editor(cs, editor_pool)

        svn.repos.replay2(
            root,                   # root
            '',                     # base_dir
            SVN_INVALID_REVNUM,     # low_water_mark
            True,                   # send_deltas
            editor,                 # editor
            baton,                  # edit_baton
            None,                   # authz_read_func
            replay_pool,            # pool
        )

        cs.parent = None
        del cs

        del editor
        del baton

        editor_pool.destroy()
        replay_pool.destroy()
        del editor_pool
        del replay_pool

        pool.destroy()
        del pool
        self.pool = None

    def _get_proplist(self, path, rev=None):
        """
        Returns a dict() of properties, where keys represent property names
        and values are corresponding property values.  If @rev is None, the
        node's proplist in the current root (which is either a rev or a txn)
        is used.
        """
        root = self.root if rev is None else self._get_root(rev)
        return svn.fs.node_proplist(root, path, self.pool)

    def _get_root(self, rev):
        if rev not in self.__roots:
            self.__roots[rev] = svn.fs.revision_root(self.fs, rev, self.pool)
        return self.__roots[rev]

    @property
    def is_rev(self):
        return self.__is_rev

    @property
    def is_txn(self):
        return not self.__is_rev

    @property
    def rev(self):
        assert self.is_rev
        return self.__rev

    @property
    def base_rev(self):
        return self.__base_rev

    @property
    def txn_name(self):
        assert self.is_txn
        return self.__txn_name

    @property
    def txn(self):
        assert self.is_txn
        return self.__txn

    def set_target_revision(self, target_rev, pool=None):
        pass

    def open_root(self, base_rev, dir_pool=None):
        return None

    def delete_entry(self, path, rev, parent, pool=None):
        self.results.append((
            self.counter.next(),
            'delete_entry',
            '/' + path
        ))

    def add_directory(self, path, parent, copied_from_path,
                      copied_from_rev, dir_pool=None):
        self.results.append((
            self.counter.next(),
            'add_entry',
            '/' + path,
            copied_from_path,
            copied_from_rev,
        ))
        return '/' + path

    def open_directory(self, path, parent, base_rev, dir_pool=None):
        return '/' + path

    def change_dir_prop(self, path, name, value, pool=None):
        self.results.append((
            self.counter.next(),
            'change_prop',
            path,
            name,
            value
        ))

    def close_directory(self, change, pool=None):
        pass

    def add_file(self, path, parent, copied_from_path,
                 copied_from_rev, file_pool=None):
        self.results.append((
            self.counter.next(),
            'add_entry',
            '/' + path,
            copied_from_path,
            copied_from_rev,
        ))
        return '/' + path

    def open_file(self, path, parent, base_rev, file_pool=None):
        return '/' + path

    def apply_textdelta(self, path, base_checksum, pool=None):
        if base_checksum:
            self.results.append((
                self.counter.next(),
                'apply_textdelta',
                path,
                base_checksum
            ))
        return None

    def change_file_prop(self, path, name, value, pool=None):
        self.results.append((
            self.counter.next(),
            'change_prop',
            path,
            name,
            value
        ))

    def close_file(self, path, text_checksum, pool=None):
        if text_checksum:
            self.results.append((
                self.counter.next(),
                'close_file',
                path,
                text_checksum
            ))

    def close_edit(self, pool=None):
        del self.counter

    def abort_edit(self, pool=None):
        del self.counter

class ChangeSetDatabase(object):
    CREATE_SQL = textwrap.dedent("""\
        create table changeset (
            rev_or_txn text,
            rev int,
            txn text,
            base_rev int
        );

        create table action (
            id integer primary key asc,
            name text not null,
            path text not null
        );
        create index action_path_ix on action(path);

        create table copy (
            id integer primary key asc,
            path text not null,
            from_path text,
            from_rev integer
        );
        create index copy_path_ix on copy(path);

        create table replace (
            id integer primary key asc,
            path text not null,
            from_path text,
            from_rev integer
        );
        create index replace_path_ix on replace(path);

        create table remove (
            id integer primary key asc,
            path text not null
        );
        create index remove_path_ix on remove(path);

        create table propchange (
            id integer primary key asc,
            path text not null,
            name text not null,
            change_type integer not null,
            extended_change_type integer not null,
            old_value text,
            new_value text
        );
        create index propchange_path_ix on propchange(path);
        create index propchange_name_ix on propchange(name);

        create table mergeinfo (
            id integer primary key asc,
            path text not null,
            merged text,
            reverse_merged text
        );
        create index mergeinfo_path_ix on mergeinfo(path);

        create table modify (
            id integer primary key asc,
            path text not null,
            base_checksum text,
            checksum text
        );
        create index modify_path_ix on modify(path);

    """)

    #def __init__(self, fs, root, results):
    def __init__(self, path, rev_or_txn, results, parent_pool):

        self.__roots = dict()
        self.revprops = dict()

        pool = svn.core.Pool(parent_pool)
        repo = svn.repos.open(os.path.abspath(path), pool)
        fs = svn.repos.fs(repo)

        self.fs = fs
        self.pool = pool
        self.results = results
        self.rev_or_txn = rev_or_txn

        try:
            self.__rev = int(rev_or_txn)
            self.__is_rev = True
            self.__base_rev = self.rev - 1
            self.revprops = svn.fs.revision_proplist(fs, self.rev, pool)
            self.root     = svn.fs.revision_root(fs, self.rev, pool)
        except:
            assert isinstance(rev_or_txn, str)
            self.__is_rev = False
            self.__txn_name = rev_or_txn
            self.__txn = svn.fs.open_txn(fs, self.txn_name, pool)
            self.__base_rev = svn.fs.txn_base_revision(self.txn)
            self.revprops = svn.fs.txn_proplist(self.txn, pool)
            self.root     = svn.fs.txn_root(self.txn, p)

        if self.base_rev != -1:
            self.base_root = self._get_root(self.base_rev)

        self._pending_deletes_resolved = 0
        self.results = results
        self.counter = itertools.count(0)

        self.modify = dict()
        self.copied_from = dict()
        self.copied_files = dict()
        self.copied_dirs  = dict()
        self.pending_deletes = dict()

        self.merged = dict()
        self.reverse_merged = dict()

        self.__base_revprops = dict()

        cs = ChangeSetEditorProxy(self)

        editor_pool = svn.core.Pool(pool)
        replay_pool = svn.core.Pool(pool)

        (editor, baton) = svn.delta.make_editor(cs, editor_pool)

        svn.repos.replay2(
            self.root,              # root
            '',                     # base_dir
            SVN_INVALID_REVNUM,     # low_water_mark
            True,                   # send_deltas
            editor,                 # editor
            baton,                  # edit_baton
            None,                   # authz_read_func
            replay_pool,            # pool
        )

        cs.parent = None
        del cs


        del editor
        del baton

        editor_pool.destroy()
        replay_pool.destroy()
        del editor_pool
        del replay_pool

        pool.destroy()
        del pool

        del fs
        del self.root
        del self.base_root
        del self.__roots

        del self.merged
        del self.reverse_merged
        del self.__base_revprops

        self.fs = None
        self.pool = None
        self.root = None
        self.__roots = None
        self.results = None
        self.base_root = None

        self.merged = None
        self.reverse_merged = None
        self.__base_revprops = None

    def _get_proplist(self, path, rev=None):
        """
        Returns a dict() of properties, where keys represent property names
        and values are corresponding property values.  If @rev is None, the
        node's proplist in the current root (which is either a rev or a txn)
        is used.
        """
        root = self.root if rev is None else self._get_root(rev)
        return svn.fs.node_proplist(root, path, self.pool)

        if (path, rev) not in self.__base_revprops:
            root = self.root if rev is None else self._get_root(rev)
            args = (root, path, self.pool)
            self.__base_revprops[(path, rev)] = svn.fs.node_proplist(*args)
        return self.__base_revprops[(path, rev)]

    def _get_root(self, rev):
        if rev not in self.__roots:
            self.__roots[rev] = svn.fs.revision_root(self.fs, rev, self.pool)
        return self.__roots[rev]

    def _base_node_kind(self, path):
        return svn.fs.check_path(self.base_root, path, self.pool)

    @property
    def is_rev(self):
        return self.__is_rev

    @property
    def is_txn(self):
        return not self.__is_rev

    @property
    def rev(self):
        assert self.is_rev
        return self.__rev

    @property
    def base_rev(self):
        return self.__base_rev

    @property
    def txn_name(self):
        assert self.is_txn
        return self.__txn_name

    @property
    def txn(self):
        assert self.is_txn
        return self.__txn

    def delete_entry(self, path, rev, pool=None):
        assert rev == -1
        count = self.counter.next()
        assert path not in self.pending_deletes
        self.pending_deletes[path] = count

        self.results.append((count, 'remove', path))

    def add_directory(self, path, parent, copied_from_path, copied_from_rev):
        assert copied_from_path and copied_from_rev != -1

        count = self.counter.next()

        assert path not in self.copied_dirs
        self.copied_dirs[count] = path

        self.copied_from.setdefault(copied_from_path, {})     \
                        .setdefault(copied_from_rev,  set())  \
                        .add(count)

        dpath = path[:-1]
        ix = self.pending_deletes.get(dpath, None)
        if ix is not None:
            if ix == count-1:
                # Update the delete path now that we know it's a dir.
                self.results[ix] = (ix, 'remove', path)
                del self.pending_deletes[dpath]
                self._pending_deletes_resolved += 1

        self.results.append((
            count,
            'copy',
            path,
            copied_from_path + '/',
            copied_from_rev,
        ))

    def add_file(self, path, parent, copied_from_path, copied_from_rev):
        assert copied_from_path and copied_from_rev != -1
        assert path not in self.copied_files

        count = self.counter.next()
        self.copied_files[count] = path

        ix = self.pending_deletes.get(path, None)
        if ix is not None:
            if ix == count-1:
                # Remove the deleted path from pending now that we know it's
                # a file.
                del self.pending_deletes[path]
                self._pending_deletes_resolved += 1

        self.results.append((
            count,
            'copy',
            path,
            copied_from_path,
            copied_from_rev,
        ))


    def change_dir_prop(self, path, name, new_value, pool=None):
        self._change_prop(path, name, new_value)

    def change_file_prop(self, path, name, value, pool=None):
        self._change_prop(path, name, new_value)

    def __parse_mergeinfo(self, old_value, new_value, merged, reverse_merged):
        assert old_value is not None
        assert new_value is not None

        import pdb
        dbg = pdb.Pdb()
        dbg.set_trace()

        pool = svn.core.Pool(self.pool)

        old = svn_mergeinfo_parse(old_value, pool)
        new = svn_mergeinfo_parse(new_value, pool)
        consider_inheritance = True
        args = (old, new, consider_inheritance, pool)

        diff = deleted = added = None
        diff = svn_mergeinfo_diff(*args)
        (deleted, added) = diff


        for (k, v) in deleted.items():
            assert k not in reverse_merged
            string = svn_rangelist_to_string(v, pool)
            buf = StringIO.StringIO()
            buf.write(string)
            del string
            buf.seek(0)
            string = str(buf.read())
            buf.reset()
            del buf
            reverse_merged[k] = string
            #reverse_merged[k] = str(svn_rangelist_to_string(v, pool))

        for (k, v) in added.items():
            assert k not in merged
            string = svn_rangelist_to_string(v, pool)
            buf = StringIO.StringIO()
            buf.write(string)
            del string
            buf.seek(0)
            string = str(buf.read())
            buf.reset()
            del buf
            merged[k] = string
            #merged[k] = str(svn_rangelist_to_string(v, pool))

        del old
        del new
        del deleted
        del added
        del diff
        del args

        pool.destroy()
        del pool
        gc.collect()

        #return (merged, reverse_merged)

    def _change_prop(self, path, name, new_value):
        count = self.counter.next()

        mergeinfo = None
        node_kind = svn_node_dir if path[-1] == '/' else svn_node_file
        old_value = '<pending>'
        if node_kind == self._base_node_kind(path):
            base_props = self._get_proplist(path, self.base_rev)
            if name not in base_props:
                old_value = '<absent>'
            else:
                old_value = base_props[name]
                if count == 0 and name == SVN_PROP_MERGEINFO:
                    self.__parse_mergeinfo(
                        old_value,
                        new_value,
                        self.merged,
                        self.reverse_merged,
                    )
                    self.results.append((
                        count,
                        'merge',
                        path,
                        self.merged or '',
                        self.reverse_merged or '',
                    ))
                    return

        self.results.append((
            count,
            'propchange',
            path,
            name,
            old_value,
            new_value
        ))

    def apply_textdelta(self, path, base_checksum):
        if base_checksum:
            assert path not in self.modify
            count = self.counter.next()
            self.modify[path] = count
            self.results.append((
                count,
                'modify',
                path,
                base_checksum,
                None,
            ))

    def close_file(self, path, text_checksum, pool=None):
        if text_checksum:
            if not path in self.modify:
                self.results.append((
                    self.counter.next(),
                    'checksum',
                    path,
                    text_checksum,
                ))
            else:
                ix = self.modify[path]
                r = self.results[ix]
                self.results[ix] = (ix, 'modify', path, r[3], text_checksum)
                del r
                del self.modify[path]

    def close_edit(self):
        pass

    def abort_edit(self):
        pass

class ChangeSetEditorBorked(object):
    def __init__(self, results):
        self.results = results

    @editor_method
    def set_target_revision(self, target_rev, pool=None):
        pass

    @editor_method
    def open_root(self, base_rev, dir_pool=None):
        return '/'

    @editor_method
    def delete_entry(self, path, rev, parent, pool=None):
        pass

    @editor_method
    def add_directory(self, path, parent, copied_from_path,
                      copied_from_rev, dir_pool=None):
        return parent + '/' + path + '/'

    @editor_method
    def open_directory(self, path, parent, base_rev, dir_pool=None):
        return parent + '/' + path + '/'

    @editor_method
    def change_dir_prop(self, change, name, value, pool=None):
        pass

    @editor_method
    def close_directory(self, change, pool=None):
        pass

    @editor_method
    def add_file(self, path, parent, copied_from_path,
                 copied_from_rev, file_pool=None):
        return parent + '/' + path

    @editor_method
    def open_file(self, path, parent, base_rev, file_pool=None):
        return parent + '/' + path

    @editor_method
    def apply_textdelta(self, change, base_checksum, pool=None):
        return None

    @editor_method
    def change_file_prop(self, change, name, value, pool=None):
        pass

    @editor_method
    def close_file(self, change, text_checksum, pool=None):
        pass

    @editor_method
    def close_edit(self, pool=None):
        pass

    @editor_method
    def abort_edit(self, pool=None):
        pass



def replay(path, rev, results):
    pool = svn.core.Pool()
    repo = svn.repos.open(os.path.abspath(path), pool)
    fs   = svn.repos.fs(repo)
    root = svn.fs.revision_root(fs, int(rev), pool)

    cs = ChangeSetEditor(results)
    (editor, baton) = svn.delta.make_editor(cs, pool)

    svn.repos.replay2(
        root,                   # root
        '',                     # base_dir
        SVN_INVALID_REVNUM,     # low_water_mark
        True,                   # send_deltas
        editor,                 # editor
        baton,                  # edit_baton
        None,                   # authz_read_func
        pool,                   # pool
    )

    del editor
    del baton
    del root
    del repo
    del fs
    del pool

    cs.results = None
    del cs

def replay_into_db(path, rev, db_name):
    pool = svn.core.Pool()
    repo = svn.repos.open(os.path.abspath(path), pool)
    fs   = svn.repos.fs(repo)
    root = svn.fs.revision_root(fs, int(rev), pool)

    cs = ChangeSetEditor(results)
    (editor, baton) = svn.delta.make_editor(cs, pool)

    svn.repos.replay2(
        root,                   # root
        '',                     # base_dir
        SVN_INVALID_REVNUM,     # low_water_mark
        True,                   # send_deltas
        editor,                 # editor
        baton,                  # edit_baton
        None,                   # authz_read_func
        pool,                   # pool
    )

    del editor
    del baton
    del root
    del repo
    del fs
    del pool

    cs.results = None
    del cs

def render_changeset_results_to_text_table(results, output=None):
    rows = [(
        'Action',
        'Path',
        'Checksum',
        'Propname',
        'Copy From?',
        'Copy Rev?',
    )] + [
        ((r[0],
          r[1],
          '' if r[0] not in ('apply_textdelta', 'close_file') else r[2],
          '' if not r[0].endswith('prop') else r[2],) + (
            ('', '') if not r[0].startswith('add') else (r[2], r[3])
        )) for r in results
    ]

    render_text_table(rows, banner='ChangeSet', output=output)


def _process_rename_dir(self, c):
    assert c.is_rename
    assert not c.path in self.rootmatcher.roots
    assert c.renamed_from_rev == c.changeset.base_rev
    assert c.renamed_from_rev == self.base_rev

    rm = self.rootmatcher
    pm = self.pathmatcher

    rd = c.root_details

    src_path = sp = c.renamed_from_path
    src_rev  = sr = c.renamed_from_rev
    src_roots = rm.find_roots_under_path(sp)
    src_root_details = srd = rm.get_root_details(sp)

    dst_path  = dp = c.path
    dst_roots = rm.find_roots_under_path(dp)
    dst_root_details = drd = pm.get_root_details(dp)

    src_has_roots_under_it = bool(src_roots)
    dst_has_roots_under_it = bool(dst_roots)

    src_roots_len = len(src_roots)
    dst_roots_len = len(dst_roots)

    # src begin
    src = logic.Mutex()
    # junk/foo/bar/ ->
    src.unknown = (
        srd.is_unknown and
        not src_has_roots_under_it
    )

    # trunk/, branches/2.0.x/ ->
    src.known_root = (
        not srd.is_unknown and
        srd.root_path == src_path
    )

    # trunk/UI/foo/ -> (where 'trunk' is a known root)
    src.known_root_subtree = (
        not srd.is_unknown and
        srd.root_path != src_path and
        src_path.startswith(srd.root_path)
    )

    # /xyz/foo/ ->, where the following roots exist:
    #       /xyz/foo/trunk
    #       /xyz/foo/branches/1.0.x
    src.root_ancestor = (
        srd.is_unknown and
        bool(src_has_roots_under_it)
    )
    # src end

    # dst begin
    dst = logic.Mutex()
    # -> junk/foo/bar/
    dst.unknown = (
        rd.is_unknown and
        drd.is_unknown and
        not dst_roots
    )

    # -> trunk/ (where 'trunk/' is a known root)
    dst.known_root = (
        c.is_replace and
        not rd.is_unknown and
        rd.root_path == dst_path
    )

    # -> trunk/UI/foo/ (where 'trunk/' is a known root)
    dst.known_root_subtree = (
        not rd.is_unknown and
        rd.root_path != dst_path and
        dst_path.startswith(rd.root_path)
    )

    # -> tags/2.0.x/, branches/foo/, trunk/
    dst.valid_root = (
        rd.is_unknown and
        not drd.is_unknown and
        drd.root_path == dst_path
    )

    # -> branches/bugs/8101 (where 'branches/bugs/' is not a known root)
    dst.valid_root_subtree = (
        rd.is_unknown and
        not drd.is_unknown and
        drd.root_path != dst_path and
        dst_path.startswith(drd.root_path)
    )

    # -> /xyz/foo/, where the following roots already exist:
    #       /xyz/foo/trunk
    #       /xyz/foo/branches/1.0.x
    dst.root_ancestor = (
        c.is_replace and
        rd.is_unknown and
        dst_has_roots_under_it
    )
    # dst end

    clean_check  = True

    new_root     = False
    remove_root  = False
    create_root  = False
    replace_root = False

    import ipdb
    ipdb.set_trace()

    with contextlib.nested(src, dst) as (src, dst):

        if src.unknown:

            if dst.unknown:
                clean_check = False

            elif dst.known_root:
                assert c.is_dir
                assert c.is_replace
                self.__processed_replace(c)

                rm.remove_root_path(dst_root)
                create_root = True
                replace_root = True

                CopyOrRename.UnknownToKnownRoot(c)

            elif dst.known_root_subtree:
                CopyOrRename.UnknownToKnownRootSubtree(c)

            elif dst.valid_root:
                CopyOrRename.UnknownToValidRoot(c)
                if drd.is_trunk:
                    create_root = True

            elif dst.valid_root_subtree:
                CopyOrRename.UnknownToValidRootSubtree(c)

            elif dst.root_ancestor:
                assert c.is_dir
                replace_roots = True
                CopyOrRename.UnknownToRootAncestor(c)

            else:
                raise UnexpectedCodePath

        elif src.known_root:
            assert c.is_dir
            new_root = True

            if srd.is_tag:
                # Always flag attempts to copy or rename tags.
                c.error(getattr(e, 'Tag' + en))

            if dst.unknown:
                CopyOrRename.KnownRootToUnknown(c)

            elif dst.known_root:
                CopyOrRename.KnownRootToKnownRoot(c)

            elif dst.known_root_subtree:
                new_root = False
                remove_root = True
                CopyOrRename.KnownRootToKnownRootSubtree(c)

            elif dst.valid_root:
                if c.is_rename:
                    paths = (sp, dp)
                    root_details = (srd, drd)
                    args = (c, paths, root_details)
                    self.__known_root_renamed(*args)

            elif dst.valid_root_subtree:
                CopyOrRename.KnownRootToValidRootSubtree(c)

            elif dst.root_ancestor:
                CopyOrRename.KnownRootToRootAncestor(c)

            else:
                raise UnexpectedCodePath

        elif src.known_root_subtree:

            if srd.is_tag:
                # Always flag attempts to copy or rename tag subtrees.
                c.error(getattr(e, 'TagSubtree' + en))

            if dst.unknown:
                CopyOrRename.KnownRootSubtreeToUnknown(c)

            elif dst.known_root:
                CopyOrRename.KnownRootSubtreeToKnownRoot(c)

            elif dst.known_root_subtree:
                if srd.root_path != drd.root_path:
                    CopyOrRename.\
                        KnownRootSubtreeToUnrelatedKnownRootSubtree(c)
                else:
                    clean_check = False

            elif dst.root_ancestor:
                CopyOrRename.KnownRootSubtreeToRootAncestor(c)

            if dst.valid_root:
                CopyOrRename.KnownRootToValidRoot(c)
                if drd.is_trunk:
                    create_root = True

            elif dst.valid_root_subtree:
                CopyOrRename.KnownRootSubtreeToValidRootSubtree(c)

            else:
                raise UnexpectedCodePath

        elif src.root_ancestor:
            rename_root = True

            if dst.unknown:
                CopyOrRename.RootAncestorToUnknown(c)

            elif dst.known_root:
                replace_root = True
                CopyOrRename.RootAncestorReplacesKnownRoot(c)

            elif dst.known_root_subtree:
                import ipdb
                ipdb.set_trace()
                CopyOrRename.RootAncestorToKnownRootSubtree(c)

            elif dst.root_ancestor:
                replace_root = True
                CopyOrRename.RootAncestorReplacesRootAncestor(c)

            elif dst.valid_root:
                # This has to be one of the most retarded things to do.
                #
                # Given:
                #   /foo/branches/1.0.x
                #   /foo/branches/2.0.x
                # Someone has done:
                #   svn mv ^/foo ^/trunk, or
                #   svn mv ^/foo ^/src/branches/2.0.x
                #
                # The precedent set by other parts of the code dealing
                # with dst.valid_root is to only create a new root if our
                # new path name is 'trunk'.  Another precedent we follow
                # is that the destination path's semantic value trumps the
                # source path's semantic value.  In this case, the source
                # path's semantic value (it is a container for multiple
                # roots) definitely outweighs the destination path's value
                # (it's a valid root path, but not a known root), so we'll
                # just rename all the roots.  Yes, even if that means we
                # ended up with the following known roots:
                #   /trunk/branches/1.0.x/
                #   /trunk/branches/2.0.x/
                #   /trunk/trunk/
                # (Retarded eh?)
                CopyOrRename.RootAncestorToValidRoot(c)

            elif dst.valid_root_subtree:
                # Similar level of retardation as above; let's just let
                # the multi-root rename go through.
                CopyOrRename.RootAncestorToValidRootSubtree(c)

            else:
                raise UnexpectedCodePath

        else:
            raise UnexpectedCodePath

    if c.is_file:
        assert none(
            new_root,
            remove_root,
            rename_root,
            create_root,
            replace_root,
        )
        return

    src._unlock()
    dst._unlock()


    if replace_root:
        pass

    if remove_root:
        self.rootmatcher.remove_root_path(dst_root)
    #if dst.known_root:
    #    assert c.is_dir
    #    # xxx todo: replace root

    #elif dst.valid_root:
    #    assert c.is_dir

    #elif dst.root_ancestor:
    #    assert c.is_dir
    #    # xxx todo: replace roots


    if clean_check:
        if not c.is_empty:
            c.error(e.UncleanRename)


    if new_root and copied_from_known_root:
        self.rootmatcher.add_root_path(c.path)

        if self.is_rev:
            d = Dict()
            d.created = c.changeset.rev
            d.creation_method = 'copied'
            d.copied_from = (c.copied_from_path, c.copied_from_rev)
            d.copies = {}
            if c.errors:
                d.errors = c.errors

            root = self.__get_copied_root_configdict(c)

            k = Dict()
            k.roots = self.roots
            k.change = c
            k.details = d
            k.src_path = src_path
            k.dst_path = dst_path
            if replace_root:
                pass

            self.__enqueue_root_action()

            self.roots[c.path] = d
            root = self.__get_copied_root_configdict(c)
            root._add_copy(c.copied_from_rev, c.path, c.changeset.rev)

    if self.is_rev:
        if renamed_from_known_root:
            # Need to mark the old root as removed and delete it from
            # our current roots.
            rev = c.renamed_from_rev
            rc = RepositoryRevisionConfig(fs=self.fs, rev=rev)
            crev = rc.roots[c.renamed_from_path]['created']
            rc = RepositoryRevisionConfig(fs=self.fs, rev=crev)
            root = rc.roots[c.renamed_from_path]
            root.removed = c.changeset.rev
            root.removal_method = 'renamed'
            root.renamed = (c.path, c.changeset.rev)

            self.rootmatcher.remove_root_path(c.renamed_from_path)
            del self.roots[c.renamed_from_path]

        if new_root:
            d = Dict()
            d.created = c.changeset.rev
            d.creation_method = 'renamed'
            d.renamed_from = (c.renamed_from_path, c.renamed_from_rev)
            d.copies = {}
            if c.errors:
                d.errors = c.errors

            self.roots[c.path] = d

    else:
        assert self.is_txn
        if renamed_from_known_root:
            self.rootmatcher.remove_root_path(c.renamed_from_path)

        if new_root:
            self.rootmatcher.add_root_path(c.path)

