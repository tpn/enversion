#===============================================================================
# Imports
#===============================================================================
import os
import re
import sys
import optparse

import evn

from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from textwrap import (
    dedent,
)

from evn.config import (
    Config,
)

from evn.command import (
    CommandError,
)

from evn.util import (
    add_linesep_if_missing,
    prepend_error_if_missing,
    Dict,
    Options,
    Constant,
)

#===============================================================================
# CLI and CommandLine Classes
#===============================================================================

class CLI(object):
    __unknown_subcommand__ = "Unknown subcommand '%s'"
    __usage__ = "Type '%prog help' for usage."
    __help__ = """\
        Type '%prog help <subcommand>' for help on a specific subcommand.

        Available subcommands:"""

    def __init__(self, args):
        self.__args = args
        self.__help = self.__help__
        self.__commandlines_by_name = dict()
        self.__commandlines_by_shortname = dict()
        self.__load_commandlines()

        if not args:
            self.help()

        self.__process_commandline(args)

    @abstractproperty
    def program_name(self):
        raise NotImplementedError()

    @abstractmethod
    def commandline_subclasses(self):
        raise NotImplementedError()

    def __find_commandline_subclasses(self):
        l = list()
        for sc in self.commandline_subclasses:
            if sc.__name__[0] != '_':
                l.append((sc.__name__, sc))
            else:
                l += [ (ssc.__name__, ssc) for ssc in sc.__subclasses__() ]
        return l

    def __helpstr(self, name):
        return os.linesep + (' ' * 12) + name

    def __load_commandlines(self):
        subclasses = [
            sc[1] for sc in sorted(self.__find_commandline_subclasses())
        ]

        for subclass in subclasses:
            cl = subclass(self.program_name)
            assert cl.name not in self.__commandlines_by_name
            helpstr = self.__helpstr(cl.name)

            if cl.shortname:
                assert cl.shortname not in self.__commandlines_by_shortname
                self.__commandlines_by_shortname[cl.shortname] = cl
                helpstr += ' (%s)' % cl.shortname

            if cl.aliases:
                for alias in cl.aliases:
                    assert alias not in self.__commandlines_by_name
                    self.__commandlines_by_name[alias] = cl
                    self.__help += self.__helpstr(alias)

            self.__help += helpstr
            self.__commandlines_by_name[cl.name] = cl

        # Meh, this is a dodgy hack.  Add a fake version command so that it'll
        # appear in the list of available subcommands.  It doesn't matter if
        # it's None as we intercept 'version', '-v' and '--version' in the
        # __process_commandline method before doing the normal command lookup.
        self.__help += self.__helpstr('version')
        self.__commandlines_by_name['version'] = None

    def __find_commandline(self, cmdline):
        return self.__commandlines_by_name.get(cmdline,
               self.__commandlines_by_shortname.get(cmdline))

    def __process_commandline(self, args):
        cmdline = args.pop(0).lower()

        if cmdline and cmdline[0] != '_':
            if '-' not in cmdline and hasattr(self, cmdline):
                getattr(self, cmdline)(args)
                self._exit(0)
            elif cmdline in ('-v', '-V', '--version'):
                self.version()
            else:
                cl = self.__find_commandline(cmdline)
                if cl:
                    try:
                        cl.run(args)
                        self._exit(0)
                    except CommandError as err:
                        self.__commandline_error(cl, err.message)
                    except Exception as err:
                        if err.__class__.__name__ == 'SubversionException':
                            self.__commandline_error(cl, err.message)
                        else:
                            raise

        self._error(
            os.linesep.join((
                self.__unknown_subcommand__ % cmdline,
                self.__usage__,
            ))
        )

    @classmethod
    def _exit(self, code):
        sys.exit(code)

    def __commandline_error(self, cl, msg):
        args = (self.program_name, cl.name, msg)
        msg = '%s %s failed: %s' % args
        sys.stderr.write(prepend_error_if_missing(msg))
        self._exit(1)

    def _error(self, msg):
        sys.stderr.write(
            add_linesep_if_missing(
                dedent(msg).replace(
                    '%prog', self.program_name
                )
            )
        )
        self._exit(1)

    def usage(self, args=None):
        self._error(self.__usage__)

    def version(self, args=None):
        sys.stdout.write(add_linesep_if_missing(evn.__version__))
        self._exit(0)

    def help(self, args=None):
        if args:
            l = [ args.pop(0), '-h' ]
            if args:
                l += args
            self.__process_commandline(l)
        else:
            self._error(self.__help + os.linesep)

class _ArgumentType(Constant):
    Optional  = 1
    Mandatory = 2
ArgumentType = _ArgumentType()

class CommandHelpFormatter(optparse.IndentedHelpFormatter):
    def _default(self, txt):
        return txt + "\n" if txt else ""

    def format_description(self, description):
        return self._default(description)

    def format_epilog(self, epilog):
        return self._default(epilog)

class CommandLine:
    """
    The `CommandLine` class exposes `Command` classes via the `CLI` class.

    """
    __metaclass__ = ABCMeta

    _rev_ = None
    _conf_ = False
    _repo_ = False
    _hook_ = False
    _argc_ = 0
    _vargc_ = None
    _usage_ = None
    _quiet_ = None
    _epilog_ = None
    _verbose_ = None
    _command_ = None
    _aliases_ = None
    _rev_range_ = None
    _shortname_ = None
    _description_ = None

    @abstractproperty
    def commands_module(self):
        raise NotImplementedError()

    def __init__(self, program_name):
        self.__program_name = program_name
        pattern = re.compile('[A-Z][^A-Z]*')
        self.classname = self.__class__.__name__
        tokens = [ t for t in pattern.findall(self.classname) ]
        assert tokens[-2:] == [ 'Command', 'Line' ]
        if self._command_ is not None:
            self.command_class = self._command_
            self.command_classname = self._command_.__name__
        else:
            ccn = ''.join(tokens[:-1])
            ccl = getattr(self.commands_module, ccn)
            self.command_classname = ccn
            self.command_class = ccl

        self.command = self.command_class(sys.stdin, sys.stdout, sys.stderr)

        tokens = [ t.lower() for t in tokens[:-2] ]
        self.name = '-'.join(t for t in tokens)
        self.shortname = None
        if self._shortname_ is not None:
            self.shortname = self._shortname_
        elif len(tokens) > 1:
            self.shortname = ''.join(t[0] for t in tokens)

        self.aliases = None
        if self._aliases_:
            self.aliases = self._aliases_

        self.conf = Config()
        self.repo_path = None
        self.parser = None

    @property
    def program_name(self):
        return self.__program_name

    @property
    def _subcommand(self):
        return '%s %s' % (self.program_name, self.name)

    def _add_parser_options(self):
        pass

    def _pre_process_parser_results(self):
        pass

    def _process_parser_results(self):
        pass

    def _post_run(self):
        pass

    def usage_error(self, msg):
        self.parser.print_help()
        sys.stderr.write("\nerror: %s\n" % msg)
        self.parser.exit(status=1)

    def run(self, args):
        k = Dict()
        k.prog = self._subcommand
        if self._usage_:
            k.usage = self._usage_
        elif self._repo_:
            k.usage = '%prog [ options ] REPO_PATH'
        if self._description_:
            k.description = self._description_
        if self._epilog_:
            k.epilog = self._epilog_

        k.formatter = CommandHelpFormatter()
        self.parser = optparse.OptionParser(**k)

        if self._verbose_:
            assert self._quiet_ is None
            self.parser.add_option(
                '-v', '--verbose',
                dest='verbose',
                action='store_true',
                default=False,
                help="run in verbose mode [default: %default]"
            )

        if self._quiet_:
            assert self._verbose_ is None
            self.parser.add_option(
                '-q', '--quiet',
                dest='quiet',
                action='store_true',
                default=False,
                help="run in quiet mode [default: %default]"
            )


        if self._conf_:
            self.parser.add_option(
                '-c', '--conf',
                metavar='FILE',
                help="use alternate configuration file FILE"
            )

        if self._hook_:
            self.parser.add_option(
                '-k', '--hook',
                #type='string',
                dest='hook_name',
                metavar='NAME',
                action='store',
                choices=list(self.conf.hook_names),
                help="hook name (i.e. 'pre-commit')"
            )

        if self._rev_:
            assert self._rev_range_ is None
            self.parser.add_option(
                '-r',
                dest='revision',
                metavar='ARG',
                action='store',
                default=None,
                help="revision [default: evn:last_rev]"
            )

        if self._rev_range_:
            assert self._rev_ is None
            self.parser.add_option(
                '-r',
                dest='revision_range',
                metavar='ARG',
                action='store',
                default='0:HEAD',
                help="revision range [default: %default]"
            )

        self._add_parser_options()
        (opts, self.args) = self.parser.parse_args(args)

        # Ignore variable argument commands altogether.
        if self._vargc_ is not True:
            arglen = len(self.args)
            if arglen == 0 and self._argc_ != 0:
                self.parser.print_help()
                self.parser.exit(status=1)
            if len(self.args) != self._argc_ and self._argc_ != 0:
                self.usage_error("invalid number of arguments")

        self.options = Options(opts.__dict__)

        self._pre_process_parser_results()

        f = None
        if self._conf_:
            f = self.options.conf
            if f and not os.path.exists(f):
                self.usage_error("configuration file '%s' does not exist" % f)

        self.conf.load(filename=f)
        self.command.conf = self.conf

        if self._repo_:
            if len(self.args) < 1:
                self.usage_error("missing REPO_PATH argument")

            self.command.path = self.args.pop(0)

        if self._hook_:
            hn = self.options.hook_name
            if not hn:
                self.usage_error("missing option: -k/--hook")
            self.command.hook_name = hn

        if self._rev_:
            self.command.rev_str = self.options.revision

        if self._rev_range_:
            assert self.options.revision_range
            self.command.revision_range = self.options.revision_range

        self.command.args = self.args
        self.command.options = self.options
        self._process_parser_results()
        with self.command:
            self.command.run()

        self._post_run()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
