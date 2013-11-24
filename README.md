
### What is Enversion?

Enversion is a server-side tool that sits in front of your Subversion
repositories and validates incoming commits.  It can detect a wide variety
of problematic commits (over 80) and will block them at the pre-commit stage.

Enversion was designed specifically for enterprise Subversion deployments,
which have vastly different usage patterns than typical open source Subversion
repositories.

See the [wiki](/../../wiki/) for more information.

### Quick Start

Once [installed](http://github.com/tpn/enversion/wiki//Installation-Guide/):

```
evnadmin create foo
svn mkdir -m "Initializing repository." file://`pwd`/foo/trunk
svn mkdir -m "Initializing repository." file://`pwd`/foo/branches
svn mkdir -m "Initializing repository." file://`pwd`/foo/tags
svn cp -m "Branching trunk to 1.x." file://`pwd`/foo/trunk \
                                    file://`pwd`/foo/branches/1.x
svn cp -m "Branching trunk to 2.x." file://`pwd`/foo/trunk \
                                    file://`pwd`/foo/branches/2.x
svn cp -m "Tagging 1.0." file://`pwd`/foo/trunk \
                         file://`pwd`/foo/tags/1.0
```

Root tracking:
```
% evnadmin show-roots foo
Showing roots for repository 'foo' at r6:
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'copied_from': ('/trunk/', 5),
                'copies': {},
                'created': 6,
                'creation_method': 'copied',
                'errors': []},
 '/trunk/': {'created': 1}}
%
```

Individual root information:
```
% evnadmin root-info /branches/1.x/ foo
'/branches/1.x/': {
    'copies': { },
    'copied_from': ('/trunk/', 3),
    'creation_method': 'copied',
    'errors': [],
    'created': 4,
}
%
```

Forward-copy information:
```
% evnadmin root-info /trunk/ foo
'/trunk/': {
    'copies': {
        3: [('/branches/1.x/', 4)],
         4: [('/branches/2.x/', 5)],
         5: [('/tags/1.0/', 6)]
    },
    'creation_method': 'created',
    'created': 1,
}
```

Extensive protection [against over 80+ types of undesirable commits](https://github.com/tpn/enversion/blob/master/lib/evn/constants.py#L34):

```
% svn co file://`pwd`/foo foo.wc
% cd foo.wc
% svn mkdir branches/3.x
% svn ci -m "Manual directory creation."
Adding         branches/3.x
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/3.x/': ['branch directory created manually']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff:

% svn ci -m "Removing tag." tags/1.0
Deleting       tags/1.0
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/1.0/': ['tag removed']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff:
```
