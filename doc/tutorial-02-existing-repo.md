This tutorial assumes you have completed the previous tutorial, [Tutorial 1 - New Repository](/tpn/enversion/wiki/Tutorial-1-New-Repository/), which focused on using `evnadmin create <repo>` to create a new Enversion-enabled Subversion repository from scratch.

This tutorial will look at how to enable Enversion against existing Subversion repositories.

Before we start, let's mimic the simple repository environment we used in the last tutorial, but instead of using `evnadmin create foo`, we'll just create a normal Subversion repository via `svnadmin create foo`.

```
svnadmin create foo
svn mkdir -m "Initializing repository." file://`pwd`/foo/trunk
svn co file://`pwd`/foo foo.wc
cd foo.wc
svn mkdir branches tags
svn ci -m "Initializing repository."
cd trunk
date > date.txt
svn add date.txt
svn ci -m "Adding date.txt."
cd ..
svn up
cd branches
svn cp ../trunk 1.x
svn ci -m "Branching trunk to 1.x."
cd ../..
svn cp -m "Branching trunk to 2.x." file://`pwd`/foo/trunk \
                                    file://`pwd`/foo/branches/2.x
svn cp -m "Tagging 1.0." file://`pwd`/foo/branches/1.x \
                         file://`pwd`/foo/tags/1.0
svn up foo.wc
cd foo.wc/trunk
date > new-date.txt
svn add new-date.txt
svn ci -m "Adding new-date.txt to trunk."
cd ../branches/1.x
svn merge ^/trunk .
svn ci -m "Syncing with trunk."
cd ../2.x
svn cp ../../trunk/new-date.txt .
svn ci -m "Copying a file when I should be merging..."
cd ../..
svn up
cd tags
svn mkdir 1.0-dodgy
svn ci -m "Creating a tag directory manually."
svn up ..
svn cp ../trunk 1.1
svn ci -m "Creating a valid tag." 1.1
svn up
date > 1.1/modifying-tag-is-bad.txt
svn add 1.1/modifying-tag-is-bad.txt
svn ci -m "Modifying a tag is bad." 1.1
svn up
svn rm 1.1
svn ci -m "Deleting one is even worse." 1.1
cd ..
svn up
```

Remember from the previous tutorial that Enversion relied on the `evn:roots` revision property to be present on the previous revision's revision property when processing a new commit at the pre-commit phase.  This reliance is based on the fact that Enversion requires an accurate list of the exact roots present in the repository in order to validate the incoming action.

Thus, you can't just enable Enversion against an existing Subversion repository and expect it to start blocking dodgy commits.  You need to let Enversion analyze the repository first, a process by which it reviews each commit ever made to the repository and incrementally builds up the `evn:roots` revision property, just as it does during the post-commit phase when already enabled.

Kicking off analysis is simple: `evnadmin analyze <repo>`.  A status message line is printed for each revision processed.  If there were any notes, errors or warnings associated with the commit, they are also printed.

In the list of commands above, we purposefully did a number of actions that Enversion would have blocked if it were enabled -- things like creating invalid roots, deleting valid roots, etc.  This will allow us to see how Enversion deals with undesirable commits in an existing repository.

Let's do the analysis:

```
% evnadmin analyze foo
1:0.001s,1,Trent,commit_root=/trunk/,action_root=/trunk/,action_type=Create
2:0.001s,2,Trent,commit_root=/,action_root_count=2
3:0.001s,2,Trent,commit_root=/trunk/
4:0.001s,2,Trent,commit_root=/branches/1.x/,action_root=/branches/1.x/,action_type=Copy,notes={'/branches/1.x/': ['known root path copied to valid root path']}
5:0.001s,2,Trent,commit_root=/branches/2.x/,action_root=/branches/2.x/,action_type=Copy,notes={'/branches/2.x/': ['known root path copied to valid root path']}
6:0.001s,2,Trent,commit_root=/tags/1.0/,action_root=/tags/1.0/,action_type=Copy,notes={'/tags/1.0/': ['known root path copied to valid root path']}
7:0.001s,2,Trent,commit_root=/trunk/
8:0.002s,3,Trent,mergeinfo,commit_root=/branches/1.x/,notes={'/branches/1.x/': ['merge']}
9:0.002s,3,Trent,commit_root=/branches/2.x/,errors={'/branches/2.x/new-date.txt': ['path copied from outside root during non-merge']}
10:0.001s,2,Trent,commit_root=/tags/1.0-dodgy/,action_root=/tags/1.0-dodgy/,action_type=Create,errors={'/tags/1.0-dodgy/': ['tag directory created manually']}
11:0.001s,2,Trent,commit_root=/tags/1.1/,action_root=/tags/1.1/,action_type=Copy,notes={'/tags/1.1/': ['known root path copied to valid root path']}
12:0.002s,3,Trent,commit_root=/tags/1.1/,errors={'/tags/1.1/modifying-tag-is-bad.txt': ['tag modified']}
13:0.001s,2,Trent,commit_root=/tags/1.1/,notes={'/tags/1.1/': ['root removed']},errors={'/tags/1.1/': ['tag removed']}
Finished analyzing repository 'foo'.
% 
```

Let's take a look at the resulting roots for the repository at r13:

```
% evnadmin show-roots foo
Showing roots for repository 'foo' at r13:
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'created': 6},
 '/trunk/': {'created': 1}}
% 
```

Two things to note: first, no root entry was added for `/tags/1.0-dodgy/` -- this directory was created via a `svn mkdir`, not by copying an existing root.  So even though it lives under the tags directory, it's not considered an existing root.

Also note that there is no root entry for `/tags/1.1/`, because we deleted it in r13.  But what about in r12?

```
% evnadmin root-info -r12 /tags/1.1/ foo
'/tags/1.1/': {
    'copies': { },
    'errors': [],
    'created': 11,
    'copied_from': ('/trunk/', 10),
    'creation_method': 'copied',
    'removed': 13,
    'removal_method': 'removed',
}
```

This is an example of where `evnadmin root-info` is more useful than `svn propget evn:roots --revprop -r<rev>`:

```
% svn propget evn:roots --revprop -r12 file://`pwd`/foo
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'created': 6},
 '/tags/1.1/': {'created': 11},
 '/trunk/': {'created': 1}}
%
```

Also note the addition of the `removed` and `removal_method` keys, which are automatically added to the tag's root information in the revision property of the revision it was created, r11:

```
% svn propget evn:roots --revprop -r11 file://`pwd`/foo
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'created': 6},
 '/tags/1.1/': {'copied_from': ('/trunk/', 10),
                'copies': {},
                'created': 11,
                'creation_method': 'copied',
                'errors': [],
                'removal_method': 'removed',
                'removed': 13},
 '/trunk/': {'created': 1}}
%
```

Before enabling a repository for Enversion usage, there's no harm in re-running analysis.  Enversion will work out, based on the value of `evn:last_rev` in the r0's rev-prop, how much analysis has already been done, and if it needs to do more:

```
% evnadmin analyze foo
Repository 'foo' is up to date (r13).
% svn cp -m "Branching 3.x" file://`pwd`/foo/trunk file://`pwd`/foo/branches/3.x                                                   

Committed revision 14.
% evnadmin analyze foo                                                          Resuming analysis for repository 'foo' from revision 13...
13:0.002s,2,Trent,commit_root=/tags/1.1/,notes={'/tags/1.1/': ['root removed']},errors={'/tags/1.1/': ['tag removed']}
14:0.001s,2,Trent,commit_root=/branches/3.x/,action_root=/branches/3.x/,action_type=Copy,notes={'/branches/3.x/': ['known root path copied to valid root path']}
Finished analyzing repository 'foo'.
%
% evnadmin show-roots foo
Showing roots for repository 'foo' at r14:
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/branches/3.x/': {'copied_from': ('/trunk/', 13),
                    'copies': {},
                    'created': 14,
                    'creation_method': 'copied',
                    'errors': []},
 '/tags/1.0/': {'created': 6},
 '/trunk/': {'created': 1}}
% 
```

If you've forgotten whether or not you've enabled Enversion, `show-repo-hook-status` always comes in handy:

```
% evnadmin show-repo-hook-status foo
+-------------------------------------------------------------------------+
|                     Repository Hook Status for 'foo'                    |
|   (/Users/Trent/src/enversion/test/wiki-tutorial-2-existing-repo/foo)   |
+-------------------------------------------------------------------------+
|         Name        | Exists? | Valid? | Exe? | Cnfgrd? | Enbld? | Rdb? |
+---------------------|---------|--------|------|---------|--------|------+
|  post-revprop-change|    N    |   -    |  -   |    -    |   -    |  -   |
|         start-commit|    N    |   -    |  -   |    -    |   -    |  -   |
|            post-lock|    N    |   -    |  -   |    -    |   -    |  -   |
|             pre-lock|    N    |   -    |  -   |    -    |   -    |  -   |
|          post-unlock|    N    |   -    |  -   |    -    |   -    |  -   |
|           pre-unlock|    N    |   -    |  -   |    -    |   -    |  -   |
|           pre-commit|    N    |   -    |  -   |    -    |   -    |  -   |
|          post-commit|    N    |   -    |  -   |    -    |   -    |  -   |
|   pre-revprop-change|    N    |   -    |  -   |    -    |   -    |  -   |
|=====================|=========|========|======|=========|========|======|
|               evn.sh|    N    |   -    |  -   |   0/9   |  0/9   |  -   |
+-------------------------------------------------------------------------+
% 
```

Let's re-run the analysis just to make sure, then enable Enversion via the `enable` command:

```
% evnadmin analyze foo              
Repository 'foo' is up to date (r14).
% evnadmin enable foo
Fixing repository hook 'post-revprop-change'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'start-commit'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'pre-lock'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'post-unlock'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'pre-unlock'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'pre-revprop-change'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'pre-commit'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'post-commit'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing repository hook 'post-lock'...
    Creating new file.
    Setting correct file permissions.
Done!
Fixing hook 'evn.sh' for repository '/Users/Trent/src/enversion/test/wiki-tutorial-2-existing-repo/foo'...
    Creating new file.
Done!
%
```

We can confirm that it's active:
```
% evnadmin show-repo-hook-status foo
+-------------------------------------------------------------------------+
|                     Repository Hook Status for 'foo'                    |
|   (/Users/Trent/src/enversion/test/wiki-tutorial-2-existing-repo/foo)   |
+-------------------------------------------------------------------------+
|         Name        | Exists? | Valid? | Exe? | Cnfgrd? | Enbld? | Rdb? |
+---------------------|---------|--------|------|---------|--------|------+
|  post-revprop-change|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|         start-commit|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|            post-lock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|             pre-lock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|          post-unlock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|           pre-unlock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|           pre-commit|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|          post-commit|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|   pre-revprop-change|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|=====================|=========|========|======|=========|========|======|
|               evn.sh|    Y    |   Y    |  Y   |   9/9   |  9/9   |  -   |
+-------------------------------------------------------------------------+
%
```

Let's confirm it's working:
```
% svn mkdir -m "" file://`pwd`/foo/tags/foobar
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/foobar/': ['tag directory created manually']}                                                                                                           Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent                                                                                                                       %
```


