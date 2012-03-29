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
Use the ``evnadmin create`` command to create a new Subversion repository
that's automatically enabled for Enversion::

    % evnadmin create foo
    % svn ls file://`pwd`/foo
    tags
    trunk
    branches
    % evnadmin show-roots foo
    Showing roots for repository 'foo' at r1:

    % svn mkdir -m "" file://`pwd`/foo/tags/test


.. tip:: If you don't want ``evnadmin`` to create the standard ``trunk``,
         ``tags`` and ``branches`` directories, you can specify the
         ``--empty`` option: ``evnadmin create --empty foo``.


Enabling Enversion against existing Subversion Repositories
-----------------------------------------------------------
I'll use a mirror of the trac repo as an example::

    % evnadmin enable trac
    Repository 'trac' has not been analyzed yet.
    Please run `evnadmin analyze trac` before enabling Enversion.

    % evnadmin analyze foo
    Analyzing repository 'foo'...
    1:0.029s,44,jonas,commit_root=/,action_root_count=8
    2:0.015s,20,jonas,commit_root=/trunk/
    3:0.015s,18,jonas,commit_root=/trunk/svntrac/
    4:0.005s,3,jonas,commit_root=/trunk/svntrac/
    5:0.011s,10,jonas,commit_root=/trunk/
    ...
    0929:0.017s,13,osimons,commit_root=/branches/0.12-stable/trac/
    10930:0.016s,12,osimons,mergeinfo,commit_root=/trunk/
    10931:0.008s,7,osimons,commit_root=/branches/0.12-stable/trac/ticket/tests/
    10932:0.013s,6,osimons,mergeinfo,commit_root=/trunk/

    % evnadmin enable trac
    Enversion has been enabled for repository 'trac'.

    % evnadmin show-roots trac
    Showing roots for repository 'trac' at r10932:
    {'/branches/0.10-stable/': {'created': 3802},
     '/branches/0.11-stable/': {'created': 6940},
     '/branches/0.12-stable/': {'created': 9938},
     ...
     '/tags/trac-0.10.1/': {'created': 4187},
     '/tags/trac-0.10.2/': {'created': 4267},
     '/tags/trac-0.10.3.1/': {'created': 4947},
     ...
     '/trunk/': {'created': 1}}

    % evnadmin root-info /trunk trac
    Looking up root '/trunk' in repository 'trac'...
    Found '/trunk' in r10932's roots; created in r1.
    Displaying root info for '/trunk' from r1:
    {'/trunk/': {
        'created': 1,
        'creation_method': 'created',
        'copies': {
            174: [('/tags/trac-0.5-rc1/', 175)],
            182: [('/tags/trac-0.5/', 183)],
            192: [('/tags/trac-0.5.1/', 193)],
            ...
            1086: [('/branches/0.8-stable/', 1087)],
            1185: [('/branches/cmlenz-dev/rearch/', 1186)],
            1351: [('/branches/cboos-dev/xref-branch/', 1352)],
            1370: [('/branches/cmlenz-dev/vclayer/', 1371)],
            ...
            9871: [('/tags/trac-0.12/', 9872)],
            9937: [('/branches/0.12-stable/', 9938)],
            10647: [('/sandbox/ticket-3584/', 10648)],
            10649: [('/sandbox/ticket-3580/', 10650)]
        },
    }}


.. vim:set ts=8 sw=4 sts=4 tw=78 et:
