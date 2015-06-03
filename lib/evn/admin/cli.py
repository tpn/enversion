#===============================================================================
# Imports
#===============================================================================
import os
import sys

from itertools import (
    count,
    chain,
    repeat,
)

import textwrap

import evn.admin.commands

from evn.util import (
    render_text_table,
    Dict,
)

from evn.command import (
    CommandError,
)

from evn.cli import (
    CLI,
    CommandLine,
)

#===============================================================================
# Classes
#===============================================================================
class AdminCommandLine(CommandLine):
    @property
    def commands_module(self):
        return evn.admin.commands

class AdminCLI(CLI):

    @property
    def program_name(self):
        return 'evnadmin'

    @property
    def commandline_subclasses(self):
        return AdminCommandLine.__subclasses__()

class DoctestCommandLine(AdminCommandLine):
    _quiet_ = True
    _description_ = textwrap.dedent("""\
        Run all Enversion doctests.

        Doctests are a convenient way to embed tests for simple/standalone
        pieces of logic without needing the huge overhead of having to write
        a formal unit test module.  This command will automatically find all
        doctests within the Enversion source code and run them.
    """)

class UnittestCommandLine(AdminCommandLine):
    _quiet_ = True
    _usage_ = '%prog [options] [unit-test-classname|test-file-name]'
    _description_ = textwrap.dedent("""\
        Helper command for running all or individual unit tests.

        To run the entire unit test suite:
            `evnadmin unittest`

        To run all test case classes within the unit test file (note that file
        is assumed to live in the evn/test directory):
            `evnadmin unittest test_root_hints.py`

        To run tests within a single test case class:
            `evnadmin unittest TestManualBranchCreationRootHint`

        To list available unit test case class names for use with that last
        command, run `evnadmin list-unit-test-classnames`.  Note that this
        will print the class names in fully qualified form but you only need
        to specify the class name itself to this command, i.e. use this:

            `evnadmin unittest TestManualBranchCreationRootHint`

        Instead of:

            `evnadmin unittest evn.test.test_root_hints.TestManualBranchCreationRootHint`
    """)


class SelftestCommandLine(AdminCommandLine):
    _quiet_ = True
    _usage_ = '%prog [options]'
    _description_ = textwrap.dedent("""\
        Run all Enversion test commands.

        This is a convenience command that runs `evnadmin doctest` and then
        `evnadmin unittest`.
    """)

class ListUnitTestClassnamesCommandLine(AdminCommandLine):
    _description_ = textwrap.dedent("""\
        List Enversion unit test class names.

        See also: `evnadmin unittest --help`
    """)

class DumpDefaultConfigCommandLine(AdminCommandLine):
    pass

class DumpConfigCommandLine(AdminCommandLine):
    _conf_ = True

class DumpRepoConfigCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class DumpModifiedRepoConfigCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class ShowPossibleConfigFileLoadOrderCommandLine(AdminCommandLine):
    _conf_ = True

class ShowPossibleRepoConfigFileLoadOrderCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class ShowActualConfigFileLoadOrderCommandLine(AdminCommandLine):
    _conf_ = True

class ShowActualRepoConfigFileLoadOrderCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class ShowWritableRepoOverrideConfigFilenameCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class DumpHookCodeCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class ShowRepoHookStatusCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _aliases_ = ('status',)

    def _post_run(self):
        r = self.command.result

        rows = [(
            'Name',
            'Exists?',
            'Valid?',
            'Exe?',
            'Cnfgrd?',
            'Enbld?',
            'Rdb?',
        )]

        def _b(b): return 'Y' if bool(b) is True else 'N'

        enabled = 0
        configured = 0
        for h in r.hook_files:
            row = [ h.name, _b(h.exists), '-' ]
            if not h.exists:
                row += [ '-', '-', '-', '-' ]
            else:
                row += [
                    _b(h.executable),
                    _b(h.configured),
                    _b(h.enabled),
                    _b(h.remote_debug),
                ]

            if h.configured:
                configured += 1

            if h.enabled:
                enabled += 1

            rows.append(row)

        rows += [ ('=',) * len(rows[0]) ]
        total = len(r.hook_files)
        eh = r.evn_hook_file
        row = [ eh.name, _b(h.exists) ]
        if not eh.exists:
            row += [ '-', '-' ]
        else:
            row += [ _b(eh.valid), _b(eh.executable) ]
        row += [
            '%d/%d' % (configured, total),
            '%d/%d' % (enabled, total),
            '-',
        ]
        rows.append(row)

        k = Dict()
        k.banner = (
            "Repository Hook Status for '%s'" % r.name,
            "(%s)" % r.path,
        )
        if False:
            k.footer = (
                "type 'evn help hook-status' for info on columns",
                "type 'evn help fix-hooks' for info on fixing errors",
            )
        k.formats = lambda: chain((str.rjust,), repeat(str.center))
        k.output = sys.stdout
        k.special = '='
        render_text_table(rows, **k)

class _ShowDebugSessionsCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _command_ = evn.admin.commands.ShowRepoHookStatusCommand

    _debug_ = False

    def _post_run(self):
        r = self.command.result

        i = count()
        rows = list()
        listening = list()
        for h in r.hook_files:
            sessions = h.remote_debug_sessions
            if not sessions:
                continue

            for s in sessions:
                state = s.state
                is_listening = False
                if state == 'listening':
                    is_listening = True
                    if not self._debug_:
                        state = state + '*'

                row = [ i.next(), s.hook_name, s.pid, s.host, s.port, state ]

                if s.state == 'connected':
                    row.append('%s:%d' % (s.dst_host, s.dst_port))
                else:
                    row.append('-')

                rows.append(row)

                if is_listening:
                    listening.append(row)

        if not rows:
            m = "No remote debug sessions found for repository '%s'.\n"
            sys.stdout.write(m % r.name)
            return

        header = ('ID', 'Hook', 'PID', 'Host', 'Port', 'State', 'Connected')
        rows.insert(0, header)

        k = Dict()
        k.banner = (
            "Remote Debug Sessions for Repository '%s'" % r.name,
            "(%s)" % r.path,
        )
        if not self._debug_:
            if len(listening) == 1:
                k.footer = (
                    "(*) type 'evnadmin debug %s' "
                    "to debug this session" % self.command.name
                )
            elif len(listening) > 1:
                # Ugh, this is highly unlikely and I can't think of a good way
                # to handle it at the moment.
                k.footer = '(*) multiple listeners?!'

        k.formats = lambda: chain((str.rjust,), repeat(str.center))
        k.output = sys.stdout
        #k.special = '='
        render_text_table(rows, **k)

        if not self._debug_:
            return

        if len(listening) != 1:
            return

        from telnetlib import Telnet
        listen = listening[0]
        host = listen[3]
        port = listen[4]
        t = Telnet(host, port)
        t.interact()

class ShowDebugSessionsCommandLine(_ShowDebugSessionsCommandLine):
    pass

class DebugCommandLine(_ShowDebugSessionsCommandLine):
    _debug_ = True

class FixHooksCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True

class EnableCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True

class DisableCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True

class CreateCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True
    _command_   = evn.admin.commands.CreateRepoCommand
    _verbose_   = True

    _description_ = (
"""
Create a new Enversion-enabled Subversion repository.

Enversion can enforce two styles of repository layouts: single-component and
multi-component.

Single-component repository layout (default):
    /trunk
    /tags
    /branches

Multi-component repository:
    /foo/trunk
    /foo/tags
    /foo/branches
    /bar/trunk
    /bar/tags
    /bar/branches

Single-component Repositories
=============================
By default, repositories are created in single-component mode.  This implies a
component-depth of 0.  These commands are equivalent:

    evnadmin create team1
    evnadmin create -s team1
    evnadmin create --single team1
    evnadmin create -d 0 team1
    evnadmin create --component-depth=0 team1

And will create the following directory structure:
    /trunk
    /tags
    /branches

If you would like to disable the automatic directory creation, specify the
-n/--no-svnmucc option, e.g.:

    evnadmin create --no-svnmucc team1

Multi-component Repositories
============================
A repository can be created in multi-component mode via the following commands:
    evnadmin create -m team2
    evnadmin create --multi team2
    evnadmin create --component-depth=1 team2

Enversion will then ensure top-level directories conform to the multi-component
layout; that is, the first directory name in the path can be anything other
than trunk, tags or branches, but the second directory name *must* be one of
these.

These are all valid paths in a multi-component repository:
    /foo/trunk
    /foo/branches
    /bar/trunk
    /bar/branches
    /bar/tags

However, Enversion would block you from creating the following directories:
    /trunk
    /tags
    /branches
    /foo/xyz
    /cat/dog

Single to Multi Conversion
==========================
Disable the Enversion hooks:
    % evnadmin disable <reponame>

Move /trunk, /tags and /branches into the desired new directory.  Make sure to
use `svn mkdir` and `svn mv` instead of normal file system operations,
otherwise Enversion won't be able to track the changed paths when it is
re-enabled.
    % cd <repo.workingcopy>
    % svn mkdir foo
    % svn mv tags foo
    % svn mv trunk foo
    % svn mv branches foo
    % svn ci -m "Converting repository from single to multi."

Mark the repository as multi-component:
    % evnadmin set-repo-component-depth --multi <reponame>
(This sets the r0 revprop evn:component_depth to 1.)

Re-enable Enversion:
    % evnadmin enable <reponame>

Verify the roots were updated:
    % evnadmin show-roots <reponame>

Verify component depth (should return '1 (multi)'):
    % evnadmin get-repo-component-depth <reponame>
"""
    )

    def _add_parser_options(self):
        self.parser.add_option(
            '-p', '--passthrough',
            dest='passthrough',
            metavar='SVNADMIN_CREATE_FLAGS',
            type='string',
            default=self.conf.svnadmin_create_flags,
            help=(
                'call `svnadmin create` with these flags when creating '
                'the underlying subversion repository -- note that all '
                'flags will need to be quoted as a single string, e.g. '
                '`evnadmin create --passthrough "--compatible-version 1.7 '
                '--config-dir /some/other/dir" <repo_name>` [default: '
                '"%default" (note: the default can be altered by the '
                '\'svnadmin-create-flags\' configuration variable)]'
            )
        )

        self.parser.add_option(
            '-d', '--component-depth',
            dest='component_depth',
            type='int',
            default=0,
            metavar='COMPONENT_DEPTH',
            help=(
                'specify a value of either 0 or 1 to enforce single or '
                'multi-component repository layout, or -1 to disable '
                'all component-depth functionality [default: %default]'
            )
        )

        self.parser.add_option(
            '-s', '--single',
            dest='single',
            action='store_true',
            help=(
                'create a single-component repository (shortcut for '
                '--component-depth=0)'
            )
        )

        self.parser.add_option(
            '-m', '--multi',
            dest='multi',
            action='store_true',
            help=(
                'create a multi-component repository (shortcut for '
                '--component-depth=1)'
            )
        )

        self.parser.add_option(
            '-n', '--no-svnmucc',
            dest='no_svnmucc',
            action='store_true',
            help=(
                'don\'t attempt to automatically create the standard '
                'layout directories via `svnmucc` after creating the '
                'repository (note: the standard layout directories are '
                'controlled by the config variable \'standard-layout\', '
                'which defaults to "branches,tags,trunk"; additionally, '
                'the config variable \'no-svnmucc-after-evnadmin-create\' '
                'can be set to a non-null value to always disable this '
                'functionality); ignored when --component-depth=1 specified'
            )
        )

    def _process_parser_results(self):
        opts = self.options

        cd = None

        if opts.multi:
            cd = 1
        elif opts.single:
            cd = 0
        else:
            cd = opts.component_depth

        if cd not in (-1, 0, 1):
            raise CommandError("invalid component depth: %r" % cd)

        self.command.component_depth = cd

class SetRepoComponentDepthCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

    def _add_parser_options(self):
        self.parser.add_option(
            '-d', '--component-depth',
            dest='component_depth',
            type='int',
            metavar='COMPONENT_DEPTH',
            help='0 = single, 1 = multi, -1 disable',
        )

        self.parser.add_option(
            '-s', '--single',
            dest='single',
            action='store_true',
            help='single-component (shortcut for --component-depth=0)'
        )

        self.parser.add_option(
            '-m', '--multi',
            dest='multi',
            action='store_true',
            help='multi-component (shortcut for --component-depth=1)'
        )

    def _process_parser_results(self):
        opts = self.options

        cd = None

        if opts.multi:
            cd = 1
        elif opts.single:
            cd = 0
        else:
            cd = opts.component_depth

        if cd not in (-1, 0, 1):
            raise CommandError("invalid component depth: %r" % cd)

        self.command.component_depth = cd

class GetRepoComponentDepthCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class SetRepoCustomHookClassCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

    def _add_parser_options(self):
        self.parser.add_option(
            '-k', '--custom-hook-classname',
            dest='custom_hook_classname',
            type='string',
            help=(
                'fully qualified classname (i.e. inc. module name) '
                'of custom hook class to use (the module must be '
                'importable and the class must derive from '
                '`evn.custom_hook.CustomHook`)'
            )
        )

class GetRepoCustomHookClassCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class VerifyPathMatchesBlockedFileExtensionsRegexCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

    def _add_parser_options(self):
        self.parser.add_option(
            '-p', '--path',
            dest='path',
            type='string',
            help="path to test (e.g. '/trunk/foo.txt')",
        )

class VerifyPathMatchesFileSizeExclusionRegexCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

    def _add_parser_options(self):
        self.parser.add_option(
            '-p', '--path',
            dest='path',
            type='string',
            help="path to test (e.g. '/trunk/foo.txt')",
        )

class RunHookCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _vargc_ = True
    _usage_ = '%prog [ OPTIONS ] REPO_PATH HOOK_NAME [HOOK_ARGS ...]'
    _description_ = 'This command should be invoked by hooks only.'

    def _pre_process_parser_results(self):
        self.command.hook_name = self.args.pop(0)

    def _process_parser_results(self):
        self.command.hook_args = self.args

class _SetRepoHookRemoteDebugCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _hook_ = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _command_ = evn.admin.commands.SetRepoHookRemoteDebugCommand

    def _add_parser_options(self):
        if self._action_ == 'disable':
            return

        self.parser.add_option(
            '-H', '--host',
            dest='remote_debug_host',
            metavar='HOST',
            type='string',
            default=self.conf.remote_debug_host,
            help='hostname to listen on [default: %default]',
        )

        self.parser.add_option(
            '-P', '--port',
            dest='remote_debug_port',
            metavar='PORT',
            type='int',
            default=self.conf.remote_debug_port,
            help='port to listen on [default: %default]',
        )

    def _process_parser_results(self):
        self.command.action = self._action_

class EnableRemoteDebugCommandLine(_SetRepoHookRemoteDebugCommandLine):
    _action_ = 'enable'

class DisableRemoteDebugCommandLine(_SetRepoHookRemoteDebugCommandLine):
    _action_ = 'disable'

class ToggleRemoteDebugCommandLine(_SetRepoHookRemoteDebugCommandLine):
    _action_ = 'toggle'

class AnalyzeCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _quiet_ = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Analyzes a Subversion repository in preparation for having Enversion
        enabled.

        Analysis involves reviewing each commit and constructing evn:roots
        entries for each revision.  Before Enversion can be enabled, an
        evn:roots entry must be present on every revision property.

        Enversion tracks the last revision analyzed in the revision 0 revprop
        named evn:last_rev.  It will query this property when analyzing a repo
        in order to pick up from the last analyzed revision.
    """)

class ShowRootsCommandLine(AdminCommandLine):
    _rev_       = True
    _repo_      = True
    _conf_      = True
    _quiet_     = True
    _usage_     = '%prog [ options ] REPO_PATH'

class ShowRevPropsCommandLine(AdminCommandLine):
    _rev_       = True
    _repo_      = True
    _conf_      = True
    _quiet_     = True
    _usage_     = '%prog [ options ] REPO_PATH'

class ShowBaseRevPropsCommandLine(AdminCommandLine):
    _repo_      = True
    _conf_      = True
    _quiet_     = True
    _usage_     = '%prog [ options ] REPO_PATH'

class RootInfoCommandLine(AdminCommandLine):
    _rev_       = True
    _repo_      = True
    _conf_      = True
    _argc_      = 2
    _usage_     = '%prog [ options ] ROOT REPO_PATH'
    _verbose_   = True

    def _add_parser_options(self):
        self.parser.add_option(
            '--json',
            dest='json',
            action='store_true',
            default=False,
            help='print roots in json format [default: %default]',
        )

    def _pre_process_parser_results(self):
        self.command.root_path = self.args.pop(0)

class FindMergesCommandLine(AdminCommandLine):
    _rev_   = True
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'

class PurgeEvnPropsCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _quiet_ = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _rev_range_ = True

class IsRepoReadonlyCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'

class SetRepoReadonlyCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'

    def _add_parser_options(self):
        self.parser.add_option(
            '-m', '--message',
            dest='message',
            metavar='MESSAGE',
            type='string',
            default=self.conf.readonly_error_message,
            help=(
                'Message to include in error message when a user attempts '
                'to commit to the repository after it has been set readonly.'
                "[default: '%default']"
            )
        )


class UnsetRepoReadonlyCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'

class AddRootHintCommandLine(AdminCommandLine):
    _rev_   = True
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog -p PATH -t TYPE REPO_PATH'
    _description_ = textwrap.dedent("""
        Add a root hint for a path of a given root type ('trunk', 'tag' or
        'branch').  The path must have been created in the given revision,
        either via mkdir or a copy of an existing path.

        This command is used to provide hints to Enversion for when its
        default root detection logic doesn't pick up that a new root is being
        created.  This could be because the branch wasn't being created
        properly (e.g. a directory called /branches/1.x was created manually
        via mkdir, but it is still desirable for it to be a root), or because
        the path represents a new 'trunk', but isn't named as such (e.g. the
        FreeBSD project uses /head/ as their main 'trunk', so they would use
        `evnadmin add-root-hint -p /head/ -r1 -t trunk freebsd` in order for
        an evn:roots entry to be added whilst analyzing the repository).

        The naming of this command as 'add root hint' versus simply 'add root'
        is intentional -- it does not create evn:roots entries directly.  What
        it does is provide Enversion with additional information about a path
        when a repository is being analyzed that will result in a new root
        being added as long as all other root invariants are met.  Thus, a
        root hint is only that, a hint.  That being said, if, after analysis,
        Enversion did not create an evn:roots entry, it means that there is
        some condition preventing that root from existing as specified, such
        as it being a sub-path of an existing root.  E.g. a root hint of
        /trunk/foo/ would be ignored if a root already exists for /trunk/ at
        the given revision.

        Examples:

            % evnadmin create foo
            % evnadmin add-root-hint -p /head/ -t trunk foo
            % evnadmin add-root-hint -p /release/1.0.24/ -t tag foo
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-p', '--path',
            dest='path',
            type='string',
            help="path of directory to add root hint for (e.g. /head/)"
        )

        self.parser.add_option(
            '-t', '--root-type',
            dest='root_type',
            metavar='ROOT_TYPE',
            type='string',
            default='trunk',
            help=(
                "type of root: 'trunk', 'tag', or 'branch' "
                "[default: %default]"
            ),
        )

    def _process_parser_results(self):
        opts = self.options

        if opts.root_type not in ('trunk', 'tag', 'branch'):
            msg = (
                "invalid root type %s, expected one of 'trunk', "
                "'tag', or 'branch'" % opts.root_type
            )
            raise CommandError(msg)

        self.command.root_type = opts.root_type
        self.command.root_path = opts.path

class RemoveRootHintCommandLine(AdminCommandLine):
    _rev_   = True
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Remove a previously added root hint from a repository.

        Note: this only removes the root hint from the evn:root_hints revision
        property on revision 0 of the repository.  It does not remove anly
        evn:roots that may have been created on account of this root hint, nor
        will it do any re-analysis of the repository.

        You can infer if roots were created because of this root hint via
        `evnadmin srp -r <rev> <repo>`.  If you need to remove these roots as
        well, after you've removed the root hint, you'll need to re-start
        analysis from the affected revision.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-p', '--path',
            dest='path',
            type='string',
            help="path of root hint to remove"
        )

    def _process_parser_results(self):
        self.command.root_path = self.options.path

class AddRootExclusionCommandLine(AdminCommandLine):
    _rev_   = True
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Add a root exclusion to the repository.  A root exclusion tells
        Enversion not to treat this path as a root when it otherwise would
        have.  It is essentially the inverse of a root hint.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-e', '--root-exclusion',
            dest='root_exclusion',
            type='string',
            help="root to exclude"
        )

    def _process_parser_results(self):
        self.command.root_exclusion = self.options.root_exclusion

class RemoveRootExclusionCommandLine(AdminCommandLine):
    _rev_   = True
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Remove an existing root exclusion from the repository.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-e', '--root-exclusion',
            dest='root_exclusion',
            type='string',
            help="existing root exclusion"
        )

    def _process_parser_results(self):
        self.command.root_exclusion = self.options.root_exclusion

class AddBranchesBasedirCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Add a branches base directory hint to the repository.

        This instructs Enversion to treat paths rooted in this directory as if
        they were rooted in a /branches/ directory.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-b', '--basedir',
            dest='basedir',
            type='string',
            help=(
                "path representing the branches base directory "
                "(e.g.  /stable/)"
            )
        )

    def _process_parser_results(self):
        self.command.branches_basedir = self.options.basedir

class RemoveBranchesBasedirCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Remove a previously added branches base directory from the repository.

        This will not affect existing roots nor will it re-analyze the
        repository.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-b', '--basedir',
            dest='basedir',
            type='string',
            help=(
                "path representing the branches base directory "
                "(e.g.  /stable/)"
            )
        )

    def _process_parser_results(self):
        self.command.branches_basedir = self.options.basedir

class AddTagsBasedirCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Add a tags base directory hint to the repository.

        This instructs Enversion to treat paths rooted in this directory as if
        they were rooted in a /tags/ directory.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-b', '--basedir',
            dest='basedir',
            type='string',
            help="path representing the tags base directory (e.g. /releng/)"
        )

    def _process_parser_results(self):
        self.command.tags_basedir = self.options.basedir

class RemoveTagsBasedirCommandLine(AdminCommandLine):
    _repo_  = True
    _conf_  = True
    _usage_ = '%prog [ options ] REPO_PATH'
    _description_ = textwrap.dedent("""
        Remove a previously added tags base directory from the repository.

        This will not affect existing roots nor will it re-analyze the
        repository.
    """)

    def _add_parser_options(self):
        self.parser.add_option(
            '-b', '--basedir',
            dest='basedir',
            type='string',
            help="path representing the tags base directory (e.g. /releng/)"
        )

    def _process_parser_results(self):
        self.command.tags_basedir = self.options.basedir

#=============================================================================#
# Main                                                                        #
#=============================================================================#
def main():
    AdminCLI(sys.argv[1:])

if __name__ == '__main__':
    main()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
