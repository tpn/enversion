#=============================================================================
# Imports
#=============================================================================
import os
import re
import sys
import optparse

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
    Dict,
    Options,
)

#=============================================================================
# CLI and CommandLine Classes
#=============================================================================

class CLI(object):
    __unknown_subcommand__ = "Unknown subcommand '%s'"
    __usage__ = "Type '%prog help' for usage."
    __help__ = """\
        Type '%prog <subcommand> help' for help on a specific subcommand.

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

    def __load_commandlines(self):
        subclasses = [
            sc[1] for sc in sorted(self.__find_commandline_subclasses())
        ]

        for subclass in subclasses:
            cl = subclass(self.program_name)
            assert cl.name not in self.__commandlines_by_name
            helpstr = os.linesep + (' ' * 12) + cl.name

            if cl.shortname:
                assert cl.shortname not in self.__commandlines_by_shortname
                self.__commandlines_by_shortname[cl.shortname] = cl
                helpstr += ' (%s)' % cl.shortname

            self.__help += helpstr
            self.__commandlines_by_name[cl.name] = cl

    def __find_commandline(self, cmdline):
        return self.__commandlines_by_name.get(cmdline,
               self.__commandlines_by_shortname.get(cmdline))

    def __process_commandline(self, args):
        cmdline = args.pop(0).lower()

        if cmdline and cmdline[0] != '_':
            if '-' not in cmdline and hasattr(self, cmdline):
                getattr(self, cmdline)(args)
                self._exit(0)
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
        msg = 'error: %s %s failed: %s' % args
        sys.stderr.write(add_linesep_if_missing(msg))
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

    def help(self, args=None):
        if args:
            l = [ args.pop(0), '-h' ]
            if args:
                l += args
            self.__process_commandline(l)
        else:
            self._error(self.__help + os.linesep)

class CommandLine:
    """
    The `CommandLine` class exposes `Command` classes via the `CLI` class.

    """
    __metaclass__ = ABCMeta

    _conf_ = False
    _repo_ = False
    _hook_ = False
    _argc_ = 0
    _usage_ = None
    _verbose_ = False
    _command_ = None
    _revision_ = None
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

        self.command = self.command_class(sys.stdout, sys.stderr)

        tokens = [ t.lower() for t in tokens[:-2] ]
        self.name = '-'.join(t for t in tokens)
        self.shortname = None
        if self._shortname_ is not None:
            self.shortname = self._shortname_
        elif len(tokens) > 1:
            self.shortname = ''.join(t[0] for t in tokens)

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

    def run(self, args):
        k = Dict()
        k.prog = self._subcommand
        if self._usage_:
            k.usage = self._usage_
        elif self._repo_:
            k.usage = '%prog [options] REPO_PATH'
        if self._description_:
            k.description = self._description_

        self.parser = optparse.OptionParser(**k)

        if self._verbose_:
            self.parser.add_option(
                '-v', '--verbose',
                dest='verbose',
                action='store_true',
                default=False,
                help="run in verbose mode [default: %default]"
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

        if self._revision_:
            self.parser.add_option(
                '-r',
                dest='revision',
                metavar='ARG',
                action='store',
                default='0:HEAD',
                help="revision range [default: %default]"
            )

        self._add_parser_options()
        (opts, self.args) = self.parser.parse_args(args)
        self.options = Options(opts.__dict__)

        if self._conf_:
            f = self.options.conf
            if f and not os.path.exists(f):
                self.parser.error("configuration file '%s' does not exist" % f)
            self.conf.load(f)
            self.command.conf = self.conf

        self._pre_process_parser_results()
        if self._repo_:
            if len(self.args) < 1:
                self.parser.error("missing REPO_PATH argument")

            self.command.path = self.args.pop(0)

        if self._argc_ is not False:
            if len(self.args) > self._argc_:
                self.parser.error("invalid number of arguments: %s" % args)

        if self._hook_:
            hn = self.options.hook_name
            if not hn:
                self.parser.error("missing option: -k/--hook")
            self.command.hook_name = hn

        if self._revision_:
            if not self.options.revision:
                self.parser.error("missing option: -r")

            self.command.revision = self.options.revision

        self.command.args = self.args
        self.command.options = self.options
        self._process_parser_results()
        with self.command:
            self.command.run()

        self._post_run()

# vim:set ts=8 sw=4 sts=4 tw=78 et:
