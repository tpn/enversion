Once you've [installed Enversion](/tpn/enversion/wiki/Installation-Guide/), you should be able to run the ``evnadmin`` command:

```
% evnadmin
Type 'evnadmin <subcommand> help' for help on a specific subcommand.

Available subcommands:
    analyze
    create
    disable-remote-debug (drd)
    doctest
    dump-config (dc)
    dump-default-config (ddc)
    dump-hook-code (dhc)
    enable
    enable-remote-debug (erd)
    find-merges (fm)
    fix-hooks (fh)
    purge-evn-props (pep)
    root-info (ri)
    run-hook (rh)
    selftest
    show-config-file-load-order (scflo)
    show-repo-hook-status (srhs)
    show-repo-remote-debug-sessions (srrds)
    show-roots (sr)
    toggle-remote-debug (trd)
    version

```

For commands that have a short alias in parenthesis, you can type that instead of typing the full command name; i.e. ``evnadmin scflo`` instead of ``evnadmin show-config-file-load-order``.  However, for this guide, I'll use the full versions for all command names so it's more obvious what's being done.

Let's change into a temporary directory and create a new, Enversion-enabled Subversion repository:

```
% cd ~/tmp
% ls
% evnadmin create foo
% ls
foo
% svn info file://`pwd`/foo
Path: foo
URL: file:///Users/Trent/tmp/foo
Relative URL: ^/
Repository Root: file:///Users/Trent/tmp/foo
Repository UUID: 7f0997a5-8924-49e4-bb99-55b9bed51a34
Revision: 0
Node Kind: directory
Last Changed Rev: 0
Last Changed Date: 2013-11-22 21:00:03 -0500 (Fri, 22 Nov 2013)
```

The command ``evnadmin create foo`` is intended to be analogous to the svn equivalent: ``svnadmin create foo``.  It creates a Subversion repository, then enables Enversion functionality against it.  By that, I specifically mean that it has inserted itself into all the Subversion hooks for that repository.

You can view this via the ``evnadmin show-repo-hook-status`` command.

```
% evnadmin show-repo-hook-status foo
+-------------------------------------------------------------------------+
|                     Repository Hook Status for 'foo'                    |
|                          (/Users/Trent/tmp/foo)                         |
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
```

A lot of work has been done to ease the administrative burden associated with managing hooks.  This has two parts: detecting when a hook is invalid or has some other issue (like not having executable permissions set), and then providing a simple way to fix all issues that would possibly prevent hooks from working properly.

The first step, showing the status of repository hooks, is handled by the ``evnadmin show-repo-hook-status`` command, depicted above.  The second step, automatically fixing any issues, is handled by ``evnadmin fix-hooks <repo>``.

Let's purposefully butcher the state of all the hooks, and watch how Enversion deals with it.  (I remove all the *.tmpl hooks just to make the output of ``ls -la`` a little cleaner.)

```
% cd foo/hooks
% rm *.tmpl
% ls -la
total 80
drwxr-xr-x  21 Trent  staff  714 Nov 23 17:12 .
drwxr-xr-x  10 Trent  staff  340 Nov 23 12:29 ..
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-post-commit
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-post-lock
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-post-revprop-change
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-post-unlock
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-pre-commit
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-pre-lock
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-pre-revprop-change
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-pre-unlock
-rw-r--r--   1 Trent  staff    0 Nov 23 12:29 evn-start-commit
-rwxr-xr-x   1 Trent  staff  923 Nov 23 12:29 evn.sh
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 post-commit
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 post-lock
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 post-revprop-change
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 post-unlock
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 pre-commit
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 pre-lock
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 pre-revprop-change
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 pre-unlock
-rwxr-xr-x   1 Trent  staff  127 Nov 23 12:29 start-commit
```

Let's remove `evn-post-commit` and `evn-pre-revprop-change`:

```
% rm evn-post-commit
% rm evn-pre-revprop-change
%
```
This has the effect of instantly disabling Enversion during the *post-commit* and *pre-revprop-change* hook phases.  This is referred to as *enabled*; a hook is considered enabled if a file exists in the `hooks` directory with the name `evn-<hook-phase>`, i.e. `evn-pre-commit`, `evn-post-commit`, etc.

This allows you to quickly disable (``rm foo/hooks/evn-pre-commit``) and enable (``touch foo/hooks/evn-pre-commit``) individual hooks on a live repository without having to enable/disable Enversion altogether.

Whether or not a hook is considered to be *enabled* is depicted by the `Enbld?` column (Y = enabled, N = disabled) of the `show-repo-hook-status` command.

Next, we'll take out the special `evn.sh` launch string from the `pre-commit` hook:
```
% cat pre-commit
#!/bin/sh

$(dirname "$0")/evn.sh $(basename "$0") $* || exit 1

exit 0

$(dirname "$0")/evn.sh $(basename "$0") $* || exit 1

%
```

(If you're wondering why `$(dirname "$0")/evn.sh $(basename "$0") $* || exit 1` occurs twice, I was thinking the same thing!  That's a bug, I've raised [issue9](/tpn/enversion/issue/9/).)

So, let's take out the evn.sh launcher line:
```
% cat post-commit | grep -v evn.sh > pre-commit
% cat pre-commit
#!/bin/sh


exit 0


%
```

And finally, let's mess up some permissions:

```
% chmod 600 post-commit
% chmod 644 evn.sh
```

Now, let's see what ``show-repo-hook-status`` has to say now, after we've butchered everything:

```
% pwd
/Users/Trent/tmp/foo/hooks
% cd ../../
+-------------------------------------------------------------------------+
|                     Repository Hook Status for 'foo'                    |
|                          (/Users/Trent/tmp/foo)                         |
+-------------------------------------------------------------------------+
|         Name        | Exists? | Valid? | Exe? | Cnfgrd? | Enbld? | Rdb? |
+---------------------|---------|--------|------|---------|--------|------+
|  post-revprop-change|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|         start-commit|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|            post-lock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|             pre-lock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|          post-unlock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|           pre-unlock|    Y    |   -    |  Y   |    Y    |   Y    |  N   |
|           pre-commit|    Y    |   -    |  Y   |    N    |   N    |  N   |
|          post-commit|    Y    |   -    |  N   |    Y    |   N    |  N   |
|   pre-revprop-change|    Y    |   -    |  Y   |    Y    |   N    |  N   |
|=====================|=========|========|======|=========|========|======|
|               evn.sh|    Y    |   Y    |  N   |   8/9   |  6/9   |  -   |
+-------------------------------------------------------------------------+
%
```

Compare the Ns against the previous Ys.  It detected all of the things we purposefully broke.  Luckily, it's easy enough to fix:

```
% evnadmin fix-hooks foo
Fixing repository hook 'pre-commit'...
    Configuring for use with Enversion.
Done!
Fixing repository hook 'post-commit'...
    Setting correct file permissions.
Done!
Fixing hook 'evn.sh' for repository '/Users/Trent/tmp/foo'...
    Setting correct file permissions.
Done!
```

That was easy!  Let's see what `show-repo-hook-status` says now:

```
% evnadmin show-repo-hook-status foo
+-------------------------------------------------------------------------+
|                     Repository Hook Status for 'foo'                    |
|                          (/Users/Trent/tmp/foo)                         |
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
|          post-commit|    Y    |   -    |  Y   |    Y    |   N    |  N   |
|   pre-revprop-change|    Y    |   -    |  Y   |    Y    |   N    |  N   |
|=====================|=========|========|======|=========|========|======|
|               evn.sh|    Y    |   Y    |  Y   |   9/9   |  7/9   |  -   |
+-------------------------------------------------------------------------+
%
```

That looks better.  But what about the two that are showing as not enabled?  `post-commit` and `pre-revprop-change`?  As mentioned previously, we can toggle a hook on and off simply by the presence of a file name `evn-<hook-name>` in the hooks directory.

In our example, we removed `evn-post-commit` and `evn-pre-prevprop-change`, which is why they both show as disabled in the hook status table.

We can enable them again by simply `touch`ing each file:
```
% touch foo/hooks/evn-post-commit
% touch foo/hooks/evn-pre-revprop-change
% evnadmin show-repo-hook-status foo
+-------------------------------------------------------------------------+
|                     Repository Hook Status for 'foo'                    |
|                          (/Users/Trent/tmp/foo)                         |
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

When would you enable/disable an individual hook?  Under normal circumstances, you wouldn't.  The functionality is really provided when dealing with unexpected issues -- if a problem occurs with Enversion and Subversion commits are getting rejected at the pre-commit stage, you can quickly disable the pre-commit hook (`rm foo/hooks/evn-pre-commit`) to allow commits to go through once again, whilst investigating things in the background.

```
% svn mkdir -m "Initializing repository." file://`pwd`/foo/trunk

Committed revision 1.

% evnadmin show-roots foo
Showing roots for repository 'foo' at r3:
{'/trunk/': {'created': 1}}

% evnadmin root-info /trunk/ foo
'/trunk/': {
    'copies': { },
    'creation_method': 'created',
    'created': 1,
}
```

Let's set up some initial structure:
```
% svn co file://`pwd`/foo foo.wc
Checked out revision 0.

% svn co file://`pwd`/foo foo.wc
A    foo.wc/trunk
Checked out revision 1.
% cd foo.wc
% svn mkdir branches tags
A         branches
A         tags
% svn ci -m "Initializing repository."
Adding         branches
Adding         tags

Committed revision 2.
%

% cd trunk
% date > date.txt
% cat date.txt
Fri Nov 22 21:33:48 EST 2013
% svn add date.txt
A         date.txt
% svn ci -m "Adding date.txt."
Adding         date.txt
Transmitting file data .
Committed revision 3.
```

### Blocking Commits

The main purpose of Enversion is to block undesirable commits.  An undesirable commit is something that Subversion will happily let through in the out-of-the-box configuration, but really shouldn't.

An undesirable commit can fall into one of two categories:
* Policy: standard SCM best-practices.  Preventing tag modification is the best example of this.
* Preventative: these are the sort of commits that result from inexperienced users or basic tool re-use.  This is a much larger category.

Let's take a look at some of the commits that Enversion will block that fall into the preventative category.  First up, manually creating a branch by `svn mkdir` instead of `svn cp`'ing the source.

```
% cd ../branches
% svn mkdir 1.x
A         1.x
% svn ci -m "Branching trunk."
Adding         1.x
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/1.x/': ['branch directory created manually']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff:

%
```

Creating a branch directory manually instead of `svn cp` is an instant red flag.  Let's revert this copy attempt:
```
% svn revert 1.x
Reverted '1.x'
% rm -rf 1.x
% svn st
%
```

Another common problem, often caused by incorrect TortoiseSVN usage, is when users create branches from out-of-date working copies:

```
% pwd
/Users/Trent/tmp/foo.wc/branches
% svn cp ../trunk 1.x
A         1.x
% svn ci -m "Branching trunk to 1.x."
Adding         1.x
Adding         1.x/date.txt
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/1.x/': ['unclean copy'],
 '/branches/1.x/date.txt': ['path copied from outside root during non-merge']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent
```

We can see that our 1.x branch has been copied from an out-of-date trunk:
```
% svn info 1.x
Path: 1.x
Working Copy Root Path: /Users/Trent/tmp/foo.wc
URL: file:///Users/Trent/tmp/foo/branches/1.x
Relative URL: ^/branches/1.x
Repository Root: file:///Users/Trent/tmp/foo
Repository UUID: dc2a6be0-9580-4901-8197-46e6afbe7aa6
Revision: 1
Node Kind: directory
Schedule: add
Copied From URL: file:///Users/Trent/tmp/foo/trunk
Copied From Rev: 1
Last Changed Author: Trent
Last Changed Rev: 1
Last Changed Date: 2013-11-22 21:09:15 -0500 (Fri, 22 Nov 2013)
%
```

Let's clean up that example:
```
% svn revert --depth infinity 1.x
Reverted '1.x'
Reverted '1.x/date.txt'
%
```

And let's bring trunk up to date so that a subsequent clean copy would work:
```
% svn up ../trunk
Updating '/Users/Trent/tmp/foo.wc/trunk':
At revision 3.
%
```

Before we take a clean copy, though, let's look at another issue: unclean copies.  That is, you take a copy of an existing root, but modify it before you commit.  This can result in complications down the track if you need to merge between the two trees.  Let's see this in effect:

```
% pwd
/Users/Trent/tmp/foo.wc/branches
% svn cp ../trunk 1.x
A         1.x
% svn st
A  +    1.x
A  +    1.x/date.txt
```

Now let's modify `date.txt` before we commit:
```
% date > 1.x/date.txt
% svn ci -m "Branching trunk to 1.x."
Adding         1.x
Sending        1.x/date.txt
Transmitting file data .svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/1.x/': ['unclean copy']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

So, how do you create branches?  You should create them from an existing root.  The only way of creating a new root is by naming it trunk.  You can then copy trunk into branches:

```
% pwd
/Users/Trent/tmp/foo.wc/branches
% svn revert --depth infinity 1.x
Reverted '1.x'
Reverted '1.x/date.txt'
% ls
% svn up ..
Updating '/Users/Trent/tmp/foo.wc':
At revision 3.
% svn cp ../trunk 1.x
A         1.x
%
% svn ci -m "Branching trunk to 1.x."
Adding         1.x

Committed revision 4.
%
```

As you can see, there are a lot of issues you need to be aware of when creating branches from local working copies.  That's why the best practice is to create branches server-side:

```
% pwd
/Users/Trent/tmp/foo.wc/branches
% cd ../../
% svn cp -m "Branching trunk to 2.x." file://`pwd`/foo/trunk \
                                     file://`pwd`/foo/branches/2.x

Committed revision 5.
%
% svn up foo.wc
Updating 'foo.wc':
A    foo.wc/branches/2.x
A    foo.wc/branches/2.x/date.txt
Updated to revision 5.
%
```

The same sort of protection applies to tags as well:
```
% pwd
/Users/Trent/tmp
% cd foo.wc/tags
% svn mkdir 1.0
A         1.0
% svn ci -m "Tagging 1.0"
Adding         1.0
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/1.0/': ['tag directory created manually']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

In fact, once created, tags are immutable.  Let's create a proper tag first:
```
% pwd
/Users/Trent/tmp/foo.wc/tags
% svn revert --depth infinity 1.0
Reverted '1.0'
% rm -rf 1.0
% svn st
% svn cp ../branches/1.x  1.0
A         1.0
% svn ci -m "Tagging 1.0"
Adding         1.0

Committed revision 6.
%
```

You can't delete a tag:
```
% pwd
/Users/Trent/tmp/foo.wc/tags
% cd ../..
% svn rm -m "Removing tag 1.0" file://`pwd`/foo/tags/1.0
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/1.0/': ['tag removed']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

You can't copy a tag:
```
% svn cp -m "Branching from tag 1.0" file://`pwd`/foo/tags/1.0 \
                                     file://`pwd`/foo/branches/1.0.x
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/1.0.x/': ['tag copied']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

And you definitely can't modify the contents of a tag after it's been created:
```
% pwd
/Users/Trent/tmp
% cd foo.wc
% svn up
Updating '.':
At revision 6.
% cd tags/1.0
% date > date.txt
% svn st
M       date.txt
% svn ci -m "Modifying tag."
Sending        date.txt
Transmitting file data .svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/1.0/date.txt': ['tag modified']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

That also includes adding new files:
```
% svn revert date.txt
Reverted 'date.txt'
% svn st
% date > new-date.txt
% svn add new-date.txt
A         new-date.txt
% svn ci -m "Adding new file to tag."
Adding         new-date.txt
Transmitting file data .svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/1.0/new-date.txt': ['tag modified']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

% svn revert new-date.txt
% rm new-date.txt
% svn st
%
```

And removing existing files:
```
% svn rm date.txt
D         date.txt
% svn ci -m "Removing file from tag."
Deleting       date.txt
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/tags/1.0/date.txt': ['file removed from tag']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

Let's take a look at a few more non-trivial commits that we block.  Multi-root commits are generally not a good idea -- a commit should only contain the specific changes related to a given bug/issue/feature.  This allows the change to be backed out (reverted) easily.  If a commit contains three features, it becomes much harder to rollback just one of those features.

Enversion can detect multi-root commits and will block them accordingly:

```
% pwd
/Users/Trent/tmp/foo.wc/tags/1.0
% cd ../../branches
% svn up
Updating '.':
At revision 6.
% date > branches/1.x/date.txt
% date > branches/2.x/date.txt
% svn st
M       branches/1.x/date.txt
M       branches/2.x/date.txt
```

Watch what happens when we try and commit this at the branches level:
```
% svn ci -m "Commits across multiple known-roots are not permitted."
Sending        branches/1.x/date.txt
Sending        branches/2.x/date.txt
Transmitting file data ..svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/': ['mixed root names in multi-root commit']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

Let's clean up:
```
% svn st
M       branches/1.x/date.txt
M       branches/2.x/date.txt
% svn st | awk '{ print $2 }' | xargs svn revert
Reverted 'branches/1.x/date.txt'
Reverted 'branches/2.x/date.txt'
% svn st | awk '{ print $2 }' | xargs rm
% svn st
%
```

Another non-trivial thing we block is when users incorrectly copy things from outside their root.  This can be best demonstrated by an example:

```
% pwd
/Users/Trent/tmp/foo.wc/branches/1.x
% cd ../../trunk
% date > trunk-date.txt
% svn add trunk-date.txt
A         trunk-date.txt
% svn ci -m "Adding trunk-date.txt."
Adding         trunk-date.txt
Transmitting file data .
Committed revision 7.
% cd ../branches/1.x
% svn cp ../../trunk/trunk-date.txt .
A         trunk-date.txt
% svn ci -m "Copying a file when I should be merging..."
Adding         trunk-date.txt
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/1.x/trunk-date.txt': ['path copied from outside root during non-merge']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

The reason this commit is blocked is because it is rarely what the user actually wants to do -- but very frequently *what* they end up doing due to unfamiliarity with Subversion's command line, TortoiseSVN, or the Subversion plugin being used by their IDE.

```
% svn revert new-date.txt && rm new-date.txt
Reverted 'new-date.txt'
%
```

The correct way to bring in changes from outside your tree is to either copy them manually (i.e. without doing an `svn cp`), or do things properly via a merge:

```
% svn merge ^/trunk .
--- Merging r4 through r7 into '.':
A    new-date.txt
--- Recording mergeinfo for merge of r4 through r7 into '.':
 U   .
% svn ci -m "Sync'ing with trunk."
Sending        .
Adding         new-date.txt

Committed revision 8.
%
```

Another example of something we block: users committing entire Subversion repositories into Subversion.  I have seen this time and time again at various enterprise clients, and it's usually due to an unfamiliarity with TortoiseSVN.
```
% pwd
/Users/Trent/tmp/foo.wc/branches/1.x
% svnadmin create repo
% svn add –q repo
% svn ci -qm "Oops, I accidentally committed a repository."
svn: E165001: Commit failed (details follow):
svn: E165001: Commit blocked by pre-commit hook (exit code 1) with output:
error: errors:
{'/branches/1.x/repo/': ['subversion repository checked in']}

Commits with errors or warnings can be forced through by the following repository admins: <none>, or support staff: trent

%
```

The current list of all the errors that are blocked by Enversion can be found in [constants.py](https://github.com/tpn/enversion/blob/master/lib/evn/constants.py#L34).

```python
class _Errors(Constant):
    TagRenamed = 'tag renamed'
    TagModified = 'tag modified'
    RootReplaced = 'root replaced'
    RootAncestorRemoved = 'root ancestor removed'
    RootAncestorReplaced = 'root ancestor replaced'
    MultipleUnknownAndKnownRootsModified = 'multiple known and unknown roots modified in the same commit'
    MixedRootNamesInMultiRootCommit = 'mixed root names in multi-root commit'
    MixedRootTypesInMultiRootCommit = 'mixed root types in multi-root commit'
    SubversionRepositoryCheckedIn = 'subversion repository checked in'
    MergeinfoAddedToRepositoryRoot = "svn:mergeinfo added to repository root '/'"
    MergeinfoModifiedOnRepositoryRoot = "svn:mergeinfo modified on repository root '/'"
    SubtreeMergeinfoAdded = 'svn:mergeinfo added to subtree'
    RootMergeinfoRemoved = 'svn:mergeinfo removed from root'
    DirectoryReplacedDuringMerge = 'directory replaced during merge'
    EmptyMergeinfoCreated = 'empty svn:mergeinfo property set on path'
    TagDirectoryCreatedManually = 'tag directory created manually'
    BranchDirectoryCreatedManually = 'branch directory created manually'
    BranchRenamedToTrunk = 'branch renamed to trunk'
    TrunkRenamedToBranch = 'trunk renamed to branch'
    TrunkRenamedToTag = 'trunk renamed to tag'
    TrunkRenamedToUnknownPath = 'trunk renamed to unknown path'
    BranchRenamedToTag = 'branch renamed to tag'
    BranchRenamedToUnknown = 'branch renamed to unknown'
    BranchRenamedOutsideRootBaseDir = 'branch renamed to location outside root base dir'
    TagSubtreePathRemoved = 'tag subtree path removed'
    TagSubtreeCopied = 'tag subtree copied'
    TagSubtreeRenamed = 'tag subtree renamed'
    RenameAffectsMultipleRoots = 'rename affects multiple roots'
    UncleanRenameAffectsMultipleRoots = 'unclean rename affects multiple roots'
    MultipleRootsCopied = 'multiple roots copied'
    TagCopied = 'tag copied'
    UncleanCopy = 'unclean copy'
    FileRemovedFromTag = 'file removed from tag'
    CopyKnownRootSubtreeToValidAbsoluteRootPath = 'copy known root subtree to valid absolute root path'
    MixedRootsNotClarifiedByExternals = 'multiple known and unknown roots in commit could not be clarified by svn:externals'
    CopyKnownRootToIncorrectlyNamedRootPath = 'known root copied to an incorrectly-named new root path'
    CopyKnownRootSubtreeToIncorrectlyNamedRootPath = 'known root subtree copied to incorrectly-named new root path'
    UnknownPathRenamedToIncorrectlyNamedNewRootPath = 'unknown path renamed incorrectly to new root path name'
    RenamedKnownRootToIncorrectlyNamedRootPath = 'renamed known root to incorrectly named root path'
    MixedChangeTypesInMultiRootCommit = 'mixed change types in multi-root commit'
    CopyKnownRootToKnownRootSubtree = 'copy known root to known root subtree'
    UnknownPathCopiedToIncorrectlyNamedNewRootPath = 'unknown path copied to incorrectly named new root path'
    RenamedKnownRootToKnownRootSubtree = 'renamed root to known root subtree'
    FileUnchangedAndNoParentCopyOrRename = 'file has no text or property changes, and no parent copy or rename actions can be found'
    DirUnchangedAndNoParentCopyOrRename = 'directory has not changed, and no parent copy or rename actions can be found'
    EmptyChangeSet = 'empty change set'
    RenameRelocatedPathOutsideKnownRootDuringNonMerge = 'rename relocated path outside known root during non-merge'
    RenameRelocatedPathBetweenKnownRootsDuringMerge = 'rename relocated path between known roots during merge'
    TagRemoved = 'tag removed'
    CopyKnownRootToUnknownPath = 'known root copied to unknown path'
    CopyKnownRootSubtreeToInvalidRootPath = 'known root copied to invalid root path'
    NewRootCreatedByRenamingUnknownPath = 'new root created by renaming unknown path'
    UnknownPathCopiedToKnownRootSubtree = 'unknown path copied to known root subtree'
    NewRootCreatedByCopyingUnknownPath = 'new root created by copying unknown path'
    RenamedKnownRootToUnknownPath = 'known root renamed to unknown path'
    RenamedKnownRootSubtreeToUnknownPath = 'known root subtree renamed to unknown path'
    RenamedKnownRootSubtreeToValidRootPath = 'known root subtree renamed to valid root path'
    RenamedKnownRootSubtreeToIncorrectlyNamedRootPath = 'known root subtree renamed to incorrectly-named root path'
    UncleanRename = 'unclean rename'
    RootAncestorRenamedToKnownRootSubtree = "root ancestor renamed to known-root subtree"
    PathCopiedFromOutsideRootDuringNonMerge = 'path copied from outside root during non-merge'
    PathCopiedFromUnrelatedKnownRootDuringMerge = 'path copied from unrelated known root during merge'
    PathCopiedFromUnrelatedRevisionDuringMerge = 'path copied from unrelated revision root during merge'
    UnknownDirReplacedViaCopyDuringNonMerge = 'unknown directory replaced via copy during non-merge'
    DirReplacedViaCopyDuringNonMerge = 'directory replaced via copy during non-merge'
    DirectoryReplacedDuringNonMerge = 'directory replaced during non-merge'
    PreviousPathNotMatchedToPathsInMergeinfo = 'previous path not matched to paths in mergeinfo'
    PreviousRevDiffersFromParentCopiedFromRev = 'previous rev differs from parent copied-from rev'
    PreviousPathDiffersFromParentCopiedFromPath = 'previous path differs from parent copied-from path'
    PreviousRevDiffersFromParentRenamedFromRev = 'previous rev differs from parent renamed-from rev'
    PreviousPathDiffersFromParentRenamedFromPath = 'previous path differs from parent renamed-from path'
    KnownRootPathReplacedViaCopy = 'known root path replaced via copy'
    BranchesDirShouldBeCreatedManuallyNotCopied = "'branches' directory should be created manually not copied"
    TagsDirShouldBeCreatedManuallyNotCopied = "'tags' directory should be created manually not copied"
    CopiedFromPathNotMatchedToPathsInMergeinfo = 'copied-from path not matched to paths in mergeinfo'
    InvariantViolatedModifyContainsMismatchedPreviousPath = 'invariant violated: modify contains mismatched previous path'
    InvariantViolatedModifyContainsMismatchedPreviousRev = 'invariant violated: modify contains mismatched previous path'
    InvariantViolatedCopyNewPathInRootsButNotReplace = "invariant violated: the new path name created (via copy) is already a known root, but the change isn't marked as a replace."
    MultipleRootsAffectedByRemove = 'multiple roots affected by remove'
    InvariantViolatedDieCalledWithoutErrorInfo = "invariant violated: Repository.die() method called without any error information being set"
    VersionMismatch = "version mismatch: we are at version %d, but the 'evn:version' revision property found on revision 0 reports the repository is at version %d"
    MissingOrEmptyRevPropOnRev0 = "missing or empty 'evn:%s' revision property on revision 0"
    InvalidIntegerRevPropOnRev0 = "invalid value for 'evn:%s' revision property on revision 0; expected an integer greater than or equal to %d, got: %s"
    PropertyValueConversionFailed = "failed to convert property %s's value: %s"
    PropertyValueLiteralEvalFailed = "invalid value for property '%s': %s"
    LastRevTooHigh = "the value for the revision property 'evn:last_rev' on revision 0 of the repository is too high; it indicates the last processed revision was %d, however, the highest revision in the repository is only %d"
    RepositoryOutOfSyncTxn = "the repository is out of sync and can not be committed to at this time (base revision for this transaction: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    LastRevNotSetToBaseRevDuringPostCommit = "the repository is out of sync (last_rev is not set to base_rev during post-commit), preventing post-commit processing of this revision; is the pre-commit hook enabled? (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    OutOfOrderRevisionProcessingAttempt = "unable to process repository revision %d until the base revision %d has been processed; however, the last processed revision reported by the repository is %d (current repository revision: %d)"
    RootsMissingFromBaseRevTxn = "missing or empty 'evn:roots' revision property on base revision (this transaction: %s, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    RootsMissingFromBaseRevDuringPostCommit = "missing or empty 'evn:roots' revision property on base revision, preventing post-commit processing of this revision; is the pre-commit hook enabled? (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    ChangeSetOnlyApplicableForRev1AndHigher = "changeset only applicable to revisions 1 and higher"
    InvalidRootsForRev = "invalid value for 'evn:roots' revision property on revision (this revision: %d, base revision: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    StaleTxnProbablyDueToHighLoad = "please re-try your commit -- the repository is under load and your transaction became out-of-date while it was being queued for processing (base revision for this transaction: %d, repository last synchronised at revision: %d, current repository revision: %d)"
    AbsoluteRootOfRepositoryCopied = "absolute root of repository copied"
    PropertyChangedButOldAndNewValuesAreSame = "the property '%s' is recorded as having changed, but the old value and new value are identical ('%s')"
    FileExceedsMaxSize = "file size (%0.2fMB) exceeds limit (%dMB)"
```

Let's switch back to roots and examine things in a bit more detail.  A list of the steps performed so far is below -- you can copy these straight into your shell in order to replicate the environment.

```
evnadmin create foo
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
```

Let's take a look at the roots that have been created:
```
% pwd
/Users/Trent/tmp
% evnadmin show-roots foo
Showing roots for repository 'foo' at r6:
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'copied_from': ('/branches/1.x/', 5),
                'copies': {},
                'created': 6,
                'creation_method': 'copied',
                'errors': []},
 '/trunk/': {'created': 1}}
%
```

Notice that `/tags/1.0/` has a lot more information than the other entries.  Let's make a trivial change to bump the repository along to r7:

```
% date > foo.wc/trunk/foobar.txt
% svn add foo.wc/trunk/foobar.txt
A         foo.wc/trunk/foobar.txt
% svn ci -m "Adding foobar.txt." foo.wc
Adding         foo.wc/trunk/foobar.txt
Transmitting file data .
Committed revision 7.
%
```

Now let's do another `show-roots`, and watch what happens to all the information to `/tags/1.0/` information that was present in the r6 version of the repository:
```
% evnadmin show-roots foo
Showing roots for repository 'foo' at r7:
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'created': 6},
 '/trunk/': {'created': 1}}
%
```

As can be seen, that information doesn't come up directly anymore when the repository is at r7.  But it's not lost:

```
% evnadmin root-info /tags/1.0/ foo
'/tags/1.0/': {
    'copies': { },
    'copied_from': ('/branches/1.x/', 5),
    'creation_method': 'copied',
    'errors': [],
    'created': 6,
}
%
```

Let's dig a little deeper.  Where is Enversion storing this root information?

```
% svn proplist --revprop -r7 file://`pwd`/foo
Unversioned properties on revision 7:
  evn:roots
  svn:author
  svn:date
  svn:log
%
```

Hmmm... let's take a look at `evn:roots`:

```
% svn propget evn:roots --revprop -r7 file://`pwd`/foo
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'created': 6},
 '/trunk/': {'created': 1}}
%
```

Ah!  That looks like the output we saw from `show-roots`.  Let's look at r6:

```
% svn propget evn:roots --revprop -r6 file://`pwd`/foo
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'created': 5},
 '/tags/1.0/': {'copied_from': ('/branches/1.x/', 5),
                'copies': {},
                'created': 6,
                'creation_method': 'copied',
                'errors': []},
 '/trunk/': {'created': 1}}
%
```

There are three other roots in that information, `/branches/1.x/` which was created in r4:

```
% evnadmin root-info /branches/1.x/ foo
'/branches/1.x/': {
    'copies': {
        5: [('/tags/1.0/', 6)]
    },
    'copied_from': ('/trunk/', 3),
    'creation_method': 'copied',
    'errors': [],
    'created': 4,
}
% svn propget evn:roots --revprop -r4 file://`pwd`/foo
{'/branches/1.x/': {'copied_from': ('/trunk/', 3),
                    'copies': {5: [('/tags/1.0/', 6)]},
                    'created': 4,
                    'creation_method': 'copied',
                    'errors': []},
 '/trunk/': {'created': 1}}
%
```

`/branches/2.x/`, which was created in r5:
```
% evnadmin root-info /branches/2.x/ foo
'/branches/2.x/': {
    'copies': { },
    'copied_from': ('/trunk/', 4),
    'creation_method': 'copied',
    'errors': [],
    'created': 5,
}
% svn propget evn:roots --revprop -r5 file://`pwd`/foo
{'/branches/1.x/': {'created': 4},
 '/branches/2.x/': {'copied_from': ('/trunk/', 4),
                    'copies': {},
                    'created': 5,
                    'creation_method': 'copied',
                    'errors': []},
 '/trunk/': {'created': 1}}
%
```

And `/trunk/`, which we created in r1:
```
% evnadmin root-info /trunk/ foo
'/trunk/': {
    'copies': {
        3: [('/branches/1.x/', 4)], 4: [('/branches/2.x/', 5)]
    },
    'creation_method': 'created',
    'created': 1,
}
% svn propget evn:roots --revprop -r1 file://`pwd`/foo
{'/trunk/': {'copies': {3: [('/branches/1.x/', 4)],
                        4: [('/branches/2.x/', 5)]},
             'created': 1,
             'creation_method': 'created'}}
%
```

As you can see, Enversion uses revision properties to track root information.  As part of post-commit processing of a revision, it clones the previous revision's `evn:roots` revision property in a simplified format, where the existing root's name and the revision it was created in is kept, but everything else is dropped.  Additionally, any root modifications that occurred in that commit are merged into the property, and the final version is saved in that revision's revision property.

Enversion uses this information in the pre-commit phase of the next incoming commit to determine what roots are being affected by the commit, if any.  That allows us to do sophisticated checks against incoming commits depending on the type of root modifications that are discerned.

Also note that we didn't have to tell Enversion what was a root -- it figured it out automatically.  This is handled by one very simple rule: *in the beginning, there was trunk*.  That is, creating a directory named `trunk` is the only way you can create a brand new root.

Once `/trunk/` is created, it becomes a formal root, recognized by Enversion.  That means any subsequent copy operations of that root, in turn, create new roots.  We saw that when we copied `/trunk/` to `/branches/1.x/`, which then turned `/branches/1.x/` into a root.  That allowed us to copy it again to a tag, `/tags/1.0/`, which also created a new root.  Tags are handled specially within Enversion as we previously saw -- they are immutable once created.

Another unique feature of Enversion's root detection capabilities is that we can record forward-copies of roots, something that Subversion doesn't have the capability to do out of the box.  This can be seen when we take a look at the `root-info` for `/trunk/`, which we copied twice (to `/branches/1.x/` and `/branches/2.x/`):

```
% evnadmin root-info /trunk/ foo
'/trunk/': {
    'copies': {
        3: [('/branches/1.x/', 4)], 4: [('/branches/2.x/', 5)]
    },
    'creation_method': 'created',
    'created': 1,
}
%
```

That tells us r3 of `/trunk/` was copied in r4 to `/branches/1.x/`, and r4 of `/trunk/` was copied to `/branches/2.x/` in r5.  If we wanted to know more information about `/branches/1.x/`, we know that it will be stored in the evn:roots revision property at r4:

```
% svn propget evn:roots --revprop -r4 file://`pwd`/foo
{'/branches/1.x/': {'copied_from': ('/trunk/', 3),
                    'copies': {5: [('/tags/1.0/', 6)]},
                    'created': 4,
                    'creation_method': 'copied',
                    'errors': []},
 '/trunk/': {'created': 1}}
%
```

The `evnadmin root-info /branches/1.x/ foo` is simply a nicer wrapper around this functionality:

```
% evnadmin root-info /branches/1.x/ foo
'/branches/1.x/': {
    'copies': {
        5: [('/tags/1.0/', 6)]
    },
    'copied_from': ('/trunk/', 3),
    'creation_method': 'copied',
    'errors': [],
    'created': 4,
}
%
```

Enversion also stores a little bit of information in the revision properties of revision 0:

```
% svn proplist --revprop -r0 file://`pwd`/foo
Unversioned properties on revision 0:
  evn:last_rev
  evn:version
  svn:date
% svn propget evn:last_rev --revprop -r0 file://`pwd`/foo
7
% svn propget evn:version --revprop -r0 file://`pwd`/foo
1
%
```

The `evn:last_rev` property is a way for Enversion to track the revision it has most recently processed.  The role of that property becomes apparent when you start dealing with enabling Enversion against existing repositories, which is a topic that will be covered in detail in the next tutorial.

:vim set ts=8 sw=4 sts=4 tw=78 expandtab:
