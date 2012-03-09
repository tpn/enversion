.. _quick-start_toplevel:

===========
Quick Start
===========

.. _quick-start:

Getting Started with Enversion in 5 Minutes
-------------------------------------------

Download Enversion.

Creating a new, Enversion-enabled Repository
--------------------------------------------
Use the `evnadmin create` command to create a new Subversion repository that's
automatically enabled for Enversion:


    % evnadmin create foo
    % svn ls file://`pwd`/foo
    tags
    trunk
    branches
    % svn mkdir -m "" file://`pwd`/foo/tags/test

If you don't want to create 


Enabling Enversion against existing Subversion Repositories
-----------------------------------------------------------

    % evnadmin enable foo
    Repository 'foo' has not been analyzed yet.
    Please run `evnadmin analyze foo` before enabling Enversion.

    % evnadmin analyze foo
    Analyzing repository 'foo'...


    Would you like to analyze it now? [Y/n]
    Analyzing repository 'foo', this may take some time...
    ...


Alternatively, you can explicitly analyze a repository before enabling
Enversion.
    % evnadmin analyze foo

    % 
    % 

    % evnadmin create --empty foo
    % svn ls file://`pwd`/foo
    %


    trunk
    branches
    tags
    %
    % svn ls 
    % svn 

    % easy_install enversion
    % svnadmin  wizard





