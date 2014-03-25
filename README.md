
### What is Enversion?

Enversion is a server-side tool that sits in front of your Subversion
repositories and validates incoming commits.  It can detect a wide variety
of problematic commits ([over 80](/lib/evn/constants.py#L34)) and will block
them at the pre-commit stage.

Enversion was designed specifically for enterprise Subversion deployments,
which have vastly different usage patterns than typical open source Subversion
repositories.

See the [wiki](/../../wiki/) for more information:
 -  [Tutorial 1 - Creating a new, Enversion-enabled Subversion Repository](/../../wiki/Tutorial-1-New-Repository)
 -  [Tutorial 2 - Enabling Enversion against an existing Subversion Repository](/../../wiki/Tutorial-2-Existing-Repository)

### Installation & Quick Start: Cheatsheet
Pre-requisites:
```
% wget http://repo.continuum.io/miniconda/Miniconda-3.3.0-Linux-x86_64.sh
% bash Miniconda-3.3.0-Linux-x86_64.sh
% source ~/.bashrc
% conda config --add channels enversion
```

To install:
```
% conda install enversion
```

To update to the latest version:
```
% conda update enversion
```

To create isolated environments with different versions:
```
% conda create -n evn-0.2.5 enversion=0.2.5
% source activate evn-0.2.5
```

```
% conda create -n evn-0.2.6 enversion=0.2.6
% source activate evn-0.2.6
```

To create a new Subversion repository automatically protected by Enversion:
```
% evnadmin create foo
```

To verify Enversion is installed and working:
```
% evnadmin show-repo-hook-status test
+-------------------------------------------------------------------------+
|                    Repository Hook Status for 'test'                    |
|                           (/home/evnadm/test)                           |
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

To enable Enversion against an existing repository, first, analyze it:
```
% evnadmin analyze myrepo
```

Then enable:
```
% evnadmin enable myrepo
```

Tutorials:
 -  [Tutorial 1 - Creating a new, Enversion-enabled Subversion Repository](/../../wiki/Tutorial-1-New-Repository)
 -  [Tutorial 2 - Enabling Enversion against an existing Subversion Repository](/../../wiki/Tutorial-2-Existing-Repository)

### Installation Guide - Detailed

The easiest (and recommended) way to install Enversion is via ``conda``, the
cross-platform (Windows, Linux and OS X) binary package manager from [Continuum
Analytics](http://continuum.io).

> Already have ``conda`` installed?  Enversion installation is simple:
> ```
> % conda config --add channels enversion
> % conda install enversion
> ```

You can get ``conda`` in one of two ways:

  -   Install [Anaconda](https://store.continuum.io/cshop/anaconda/) (245MB
      to 483MB depending on platform).

  -   Install [Miniconda](http://conda.pydata.org/miniconda.html#miniconda)
      (18MB to 30MB depending on platform).

[Anaconda](https://store.continuum.io/cshop/anaconda/) is a fully-fledged,
completely free, enterprise-ready Python distribution for large-scale data
processing, predictive analytics, and scientific computing.  [It ships with
over 125 of the most popular Python packages for science, math, engineering and
data analysis](http://docs.continuum.io/anaconda/pkgs.html).

[Miniconda](http://conda.pydata.org/miniconda.html#miniconda) is a bare-bones
version of Anaconda that only includes the small subset of Python packages
required by ``conda``.

> Pro-tip: installed Miniconda, but want to try out Anaconda?  Simply run:
> ```
> % conda install anaconda
> ```

#### Miniconda Installation (Linux)

Miniconda installation is trivial:

```
[evnadm@centos5x64 ~]$ wget http://repo.continuum.io/miniconda/Miniconda-3.3.0-Linux-x86_64.sh
--2014-03-25 08:12:37--  http://repo.continuum.io/miniconda/Miniconda-3.3.0-Linux-x86_64.sh
Resolving repo.continuum.io... 72.21.195.181
Connecting to repo.continuum.io|72.21.195.181|:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 19998995 (19M) [application/x-sh]
Saving to: `Miniconda-3.3.0-Linux-x86_64.sh'

100%[=========================================>] 19,998,995  1.81M/s   in 9.2s

2014-03-25 08:12:50 (2.07 MB/s) - `Miniconda-3.3.0-Linux-x86_64.sh' saved [19998995/19998995]

[evnadm@centos5x64 ~]$
```

Once downloaded, simply execute the file via bash to install:

```
[evnadm@centos5x64 ~]$ bash Miniconda-3.3.0-Linux-x86_64.sh

Welcome to Miniconda 3.3.0 (by Continuum Analytics, Inc.)

In order to continue the installation process, please review the license
agreement.
Please, press ENTER to continue
>>>
===================================
Anaconda END USER LICENSE AGREEMENT
===================================
<snip>

1. You include a copy of this EULA in all copies of the derived software.
2. In advertising and labeling material for products built with Anaconda

Do you approve the license terms? [yes|no]
[no] >>> yes

Miniconda will now be installed into this location:
/home/evnadm/miniconda

  - Press ENTER to confirm the location
  - Press CTRL-C to abort the installation
  - Or specify an different location below

[/home/evnadm/miniconda] >>>
PREFIX=/home/evnadm/miniconda
installing: python-2.7.6-1 ...
installing: openssl-1.0.1c-0 ...
installing: pycosat-0.6.0-py27_0 ...
installing: pyyaml-3.10-py27_0 ...
installing: readline-6.2-2 ...
installing: sqlite-3.8.4.1-0 ...
installing: system-5.8-1 ...
installing: tk-8.5.13-0 ...
installing: yaml-0.1.4-0 ...
installing: zlib-1.2.7-0 ...
installing: conda-3.3.0-py27_0 ...
Python 2.7.6 :: Continuum Analytics, Inc.
creating default environment...
installation finished.
Do you wish the installer to prepend the Miniconda install location
to PATH in your /home/evnadm/.bashrc ? [yes|no]
[no] >>> yes

Prepending PATH=/home/evnadm/miniconda/bin to PATH in /home/evnadm/.bashrc
A backup will be made to: /home/evnadm/.bashrc-miniconda.bak


For this change to become active, you have to open a new terminal.

Thank you for installing Miniconda!
```

Then simply source .bashrc again (or open a new terminal) and you should have
access to conda:

```
[evnadm@centos5x64 ~]$ source .bashrc
[evnadm@centos5x64 ~]$ which conda
~/miniconda/bin/conda
```

Then simply run the following to install Enversion:
```
[evnadm@centos5x64 ~]$ conda config --add channels enversion
[evnadm@centos5x64 ~]$ conda install enversion
Fetching package metadata: ...
Solving package specifications: .
Package plan for installation in environment /home/evnadm/miniconda:

The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    enversion-0.2.5            |           py27_1         151 KB
    expat-2.1.0                |                0         307 KB
    httpd-2.2.26               |                0         4.3 MB
    pcre-8.31                  |                0         535 KB
    serf-1.2.1                 |                0         307 KB
    sqlite-3.7.13              |                0         1.9 MB
    subversion-1.8.8           |           py27_0        11.8 MB
    swig-2.0.12                |           py27_0         1.8 MB
    ------------------------------------------------------------
                                           Total:        21.0 MB

The following packages will be UN-linked:

    package                    |            build
    ---------------------------|-----------------
    conda-3.3.0                |           py27_0
    sqlite-3.8.4.1             |                0

The following packages will be linked:

    package                    |            build
    ---------------------------|-----------------
    apr-1.5.0                  |                0   hard-link
    apr-iconv-1.2.1            |                0   hard-link
    apr-util-1.5.3             |                0   hard-link
    conda-3.3.2                |           py27_0   hard-link
    enversion-0.2.5            |           py27_1   hard-link
    expat-2.1.0                |                0   hard-link
    httpd-2.2.26               |                0   hard-link
    pcre-8.31                  |                0   hard-link
    serf-1.2.1                 |                0   hard-link
    sqlite-3.7.13              |                0   hard-link
    subversion-1.8.8           |           py27_0   hard-link
    swig-2.0.12                |           py27_0   hard-link

Proceed ([y]/n)? y

Fetching packages ...
enversion-0.2.5-py27_1.tar.bz2 100% |################| Time: 0:00:00   1.48 MB/s
expat-2.1.0-0.tar.bz2 100% |#########################| Time: 0:00:00   1.51 MB/s
httpd-2.2.26-0.tar.bz2 100% |########################| Time: 0:00:02   2.12 MB/s
pcre-8.31-0.tar.bz2 100% |###########################| Time: 0:00:00   1.86 MB/s
serf-1.2.1-0.tar.bz2 100% |##########################| Time: 0:00:00   1.39 MB/s
sqlite-3.7.13-0.tar.bz2 100% |#######################| Time: 0:00:01   1.89 MB/s
subversion-1.8.8-py27_0.tar.bz2 100% |###############| Time: 0:00:06   2.06 MB/s
swig-2.0.12-py27_0.tar.bz2 100% |####################| Time: 0:00:00   1.97 MB/s
Extracting packages ...
[      COMPLETE      ] |##################################################| 100%
Unlinking packages ...
[      COMPLETE      ] |##################################################| 100%
Linking packages ...
[      COMPLETE      ] |##################################################| 100%
[evnadm@centos5x64 ~]$
```

This will install Enversion, which is administered via the command line program
``evnadmin``, and all required dependencies.  Note that the entire installation
is contained within the Miniconda installation, ensuring that there aren't any
conflicts with other versions of Subversion/HTTPD that may be installed on your
system.

Additionally, because the Enversion conda package manages all dependencies, no
root access is required, nor are there any base-system RPM dependencies.  This
is one of the reasons conda is the recommended installation technique.

```
[evnadm@centos5x64 ~]$ which svn
~/miniconda/bin/svn
[evnadm@centos5x64 ~]$ which evnadmin
~/miniconda/bin/evnadmin
[evnadm@centos5x64 ~]$ evnadmin create test
[evnadm@centos5x64 ~]$ evnadmin show-repo-hook-status test
+-------------------------------------------------------------------------+
|                    Repository Hook Status for 'test'                    |
|                           (/home/evnadm/test)                           |
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

#### Upgrading

Upgrading to the latest version of Enversion is trivial:

```
[evnadm@centos5x64 ~]$ conda update enversion
Fetching package metadata: ...
Solving package specifications: .
Package plan for installation in environment /home/evnadm/miniconda:

The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    enversion-0.2.6            |           py27_0         151 KB

The following packages will be UN-linked:

    package                    |            build
    ---------------------------|-----------------
    enversion-0.2.5            |           py27_1

The following packages will be linked:

    package                    |            build
    ---------------------------|-----------------
    enversion-0.2.6            |           py27_0   hard-link

Proceed ([y]/n)? y

Fetching packages ...
enversion-0.2.6-py27_0.tar.bz2 100% |################| Time: 0:00:00 421.03 kB/s
Extracting packages ...
[      COMPLETE      ] |##################################################| 100%
Unlinking packages ...
[      COMPLETE      ] |##################################################| 100%
Linking packages ...
[      COMPLETE      ] |##################################################| 100%
[evnadm@centos5x64 ~]$ evnadmin version
0.2.6
```

If there are no new versions available:

```
[evnadm@centos5x64 ~]$ conda update enversion
Fetching package metadata: ...
# All requested packages already installed.
# packages in environment at /home/evnadm/miniconda:
#
enversion                 0.2.6                    py27_0
```

#### Custom Environments

You can leverage ``conda``'s support for isolated environments to install
different versions of Enversion.  The following example creates two completely
isolated enversion environments, named ``enversion-0.2.5`` and
``enversion-0.2.6`` (for v0.2.5 and v0.2.6 respectively):

```
[evnadm@centos5x64 ~]$ conda create -n enversion-0.2.5 enversion=0.2.5
Fetching package metadata: ...
Solving package specifications: .
Package plan for installation in environment /home/evnadm/miniconda/envs/enversion-0.2.5:

The following packages will be linked:

    package                    |            build
    ---------------------------|-----------------
    apr-1.5.0                  |                0   hard-link
    apr-iconv-1.2.1            |                0   hard-link
    apr-util-1.5.3             |                0   hard-link
    enversion-0.2.5            |           py27_1   hard-link
    expat-2.1.0                |                0   hard-link
    httpd-2.2.26               |                0   hard-link
    openssl-1.0.1c             |                0   hard-link
    pcre-8.31                  |                0   hard-link
    python-2.7.6               |                1   hard-link
    readline-6.2               |                2   hard-link
    serf-1.2.1                 |                0   hard-link
    sqlite-3.7.13              |                0   hard-link
    subversion-1.8.8           |           py27_0   hard-link
    swig-2.0.12                |           py27_0   hard-link
    system-5.8                 |                1   hard-link
    tk-8.5.13                  |                0   hard-link
    zlib-1.2.7                 |                0   hard-link

Proceed ([y]/n)? y

Linking packages ...
[      COMPLETE      ] |##################################################| 100%
#
# To activate this environment, use:
# $ source activate enversion-0.2.5
#
# To deactivate this environment, use:
# $ source deactivate
#
[evnadm@centos5x64 ~]$ source activate enversion-0.2.5
discarding /home/evnadm/miniconda/bin from PATH
prepending /home/evnadm/miniconda/envs/enversion-0.2.5/bin to PATH
(enversion-0.2.5)[evnadm@centos5x64 ~]$ which evnadmin
~/miniconda/envs/enversion-0.2.5/bin/evnadmin
(enversion-0.2.5)[evnadm@centos5x64 ~]$ evnadmin version
0.2.5
(enversion-0.2.5)[evnadm@centos5x64 ~]$ source deactivate
discarding /home/evnadm/miniconda/envs/enversion-0.2.5/bin from PATH
[evnadm@centos5x64 ~]$ conda create -n enversion-0.2.6 enversion=0.2.6
Fetching package metadata: ...
Solving package specifications: .
Package plan for installation in environment /home/evnadm/miniconda/envs/enversion-0.2.6:

The following packages will be linked:

    package                    |            build
    ---------------------------|-----------------
    apr-1.5.0                  |                0   hard-link
    apr-iconv-1.2.1            |                0   hard-link
    apr-util-1.5.3             |                0   hard-link
    enversion-0.2.6            |           py27_0   hard-link
    expat-2.1.0                |                0   hard-link
    httpd-2.2.26               |                0   hard-link
    openssl-1.0.1c             |                0   hard-link
    pcre-8.31                  |                0   hard-link
    python-2.7.6               |                1   hard-link
    readline-6.2               |                2   hard-link
    serf-1.2.1                 |                0   hard-link
    sqlite-3.7.13              |                0   hard-link
    subversion-1.8.8           |           py27_0   hard-link
    swig-2.0.12                |           py27_0   hard-link
    system-5.8                 |                1   hard-link
    tk-8.5.13                  |                0   hard-link
    zlib-1.2.7                 |                0   hard-link

Proceed ([y]/n)? y

Linking packages ...
[      COMPLETE      ] |##################################################| 100%
#
# To activate this environment, use:
# $ source activate enversion-0.2.6
#
# To deactivate this environment, use:
# $ source deactivate
#
[evnadm@centos5x64 ~]$ source activate enversion-0.2.6
discarding /home/evnadm/miniconda/bin from PATH
prepending /home/evnadm/miniconda/envs/enversion-0.2.6/bin to PATH
(enversion-0.2.6)[evnadm@centos5x64 ~]$ which evnadmin
~/miniconda/envs/enversion-0.2.6/bin/evnadmin
(enversion-0.2.6)[evnadm@centos5x64 ~]$ evnadmin version
0.2.6
(enversion-0.2.6)[evnadm@centos5x64 ~]$
```

### Quick Start

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

Extensive protection [against over 80+ types of undesirable commits](/lib/evn/constants.py#L34):

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
