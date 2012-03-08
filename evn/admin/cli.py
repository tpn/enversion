#=============================================================================
# Imports
#=============================================================================
import os
import sys

from itertools import (
    chain,
    repeat,
)

import evn.admin.commands

from evn.util import (
    render_text_table,
    Dict,
)

from evn.cli import (
    CLI,
    CommandLine,
)

#=============================================================================
# Classes
#=============================================================================
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
    _verbose_ = True

class DumpDefaultConfigCommandLine(AdminCommandLine):
    pass

class DumpConfigCommandLine(AdminCommandLine):
    _conf_ = True

class ShowConfigFileLoadOrderCommandLine(AdminCommandLine):
    _conf_ = True

class DumpHookCodeCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

class ShowRepoHookStatusCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True

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

class ShowRepoRemoteDebugSessionsCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _command_ = evn.admin.commands.ShowRepoHookStatusCommand

    def _post_run(self):
        r = self.command.result

        rows = list()
        found_at_least_one_listening_session = False
        for h in r.hook_files:
            sessions = h.remote_debug_sessions
            if not sessions:
                continue

            for s in sessions:
                state = s.state
                if state == 'listening':
                    found_at_least_one_listening_session = True
                    state = state + '*'

                row = [ s.hook_name, s.pid, s.host, s.port, state ]

                if s.state == 'connected':
                    row.append('%s:%d' % (s.dst_host, s.dst_port))
                else:
                    row.append('-')

                rows.append(row)

        if not rows:
            m = "No remote debug sessions found for repository '%s'.\n"
            sys.stdout.write(m % r.name)
            return

        header = ('Hook', 'PID', 'Host', 'Port', 'State', 'Connected')
        rows.insert(0, header)

        k = Dict()
        k.banner = (
            "Remote Debug Sessions for Repository '%s'" % r.name,
            "(%s)" % r.path,
        )
        if found_at_least_one_listening_session:
            k.footer = "(*) type 'telnet <host> <port>' to connect to session"

        k.formats = lambda: chain((str.rjust,), repeat(str.center))
        k.output = sys.stdout
        #k.special = '='
        render_text_table(rows, **k)

class FixHooksCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True
    _verbose_   = True

class EnableCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True
    _verbose_   = True

class CreateCommandLine(AdminCommandLine):
    _conf_      = True
    _repo_      = True
    _verbose_   = True
    _command_   = evn.admin.commands.CreateRepoCommand

class RunHookCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _argc_ = False
    _usage_ = '%prog [ OPTIONS ] REPO_PATH HOOK_NAME [HOOK_ARGS ...]'
    _description_ = 'This command should be invoked by hooks only.'

    def _pre_process_parser_results(self):
        self.command.hook_name = self.args.pop(0)

    def _process_parser_results(self):
        self.command.hook_args = self.args

class _SetRepoHookRemoteDebugCommandLine(AdminCommandLine):
    _conf_ = True
    _repo_ = True
    _argc_ = 3
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

class AnalyzeRepoCommandLine(AdminCommandLine):
    _repo_ = True
    _conf_ = True
    _verbose_ = True
    _usage_ = '%prog [ options ] REPO_PATH'

class FindMergesCommandLine(AdminCommandLine):
    _repo_ = True
    _conf_ = True
    _verbose_ = True
    _revision_ = True
    _usage_ = '%prog [ options ] REPO_PATH'

#=============================================================================#
# Main                                                                        #
#=============================================================================#
if __name__ == '__main__':
    AdminCLI(sys.argv[1:])

# vim:set ts=8 sw=4 sts=4 tw=78 et:
