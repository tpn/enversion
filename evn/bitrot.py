
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

