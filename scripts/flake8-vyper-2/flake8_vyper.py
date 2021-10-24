"""Command-line implementation of flake8 with some tinkering for vyper."""
import sys
from typing import List, Optional

from flake8.main import application, options
from flake8.processor import PyCF_ONLY_AST, FileProcessor
from flake8.options import manager

from vyper.builtin_functions.functions import BUILTIN_FUNCTIONS
from vyper.semantics.namespace import RESERVED_KEYWORDS
from vyper.utils import (
    BASE_TYPES,
    FUNCTION_WHITELIST, 
    VALID_LLL_MACROS
)
from vyper.ast.folding import BUILTIN_CONSTANTS
from vyper.ast.pre_parser import pre_parse
from vyper.old_codegen.expr import ENVIRONMENT_VARIABLES

# Below is orginal author
# This code forked by @0xBeeDao (DevBruce)
# for Yearn, because linting is important.
__author__ = 'Mike Shultz'
__email__ = 'mike@mikeshultz.com'
__version__ = '0.1.10'

VYPER_BUILTINS = set(BUILTIN_FUNCTIONS)
VYPER_BUILTINS.update(BASE_TYPES)
VYPER_BUILTINS.update(BUILTIN_CONSTANTS.keys())
VYPER_BUILTINS.update(ENVIRONMENT_VARIABLES)
VYPER_BUILTINS.update(RESERVED_KEYWORDS)
VYPER_BUILTINS.update(FUNCTION_WHITELIST)
VYPER_BUILTINS.update(VALID_LLL_MACROS)
# Missing from vyper internals?
# https://github.com/ethereum/vyper/issues/1364
VYPER_BUILTINS.update({'self', 'String', 'HashMap', 'view', 'Bytes', 'pure'})

def find(val, it):
    """ Find the index of a value in an iterator """
    for i in range(0, len(it)):
        if val == it[i]:
            return i
    return -1


def patch_processor(processor):
    """ Patch FileProcessor to use the Vyper AST pre-processor """

    def build_ast(self):
        """Build an abstract syntax tree from the list of lines."""
        source_code = "".join(self.lines)
        _, reformatted_code = pre_parse(source_code)
        return compile(reformatted_code, "", "exec", PyCF_ONLY_AST)

    processor.build_ast = build_ast


def patch_app_option_manager(app):
    """ Patch Application an option_manager with a different name (and config) """
    app.option_manager = manager.OptionManager(
        prog="flake8-vyper",
        version=__version__,
    )
    options.register_default_options(app.option_manager)
    add_option = app.option_manager.add_option
    add_option(
        "--output-file",
        default="flake8.log",
        help="The output filename (Default: %(default)s)",
    )
    add_option(
        "--verbose",
        default=False,
        action="store_true",
        help="Verbose",
    )


def add_vyper_builtins_to_argv(argv):
    """ Inject --builtins with the vyper builtins into argv """
    argv = (argv if argv is not None else sys.argv)[:]
    if '--builtins' in argv:
        idx = find('--builtins', argv)
        if idx > -1 and '=' in argv[idx]:
            parts = argv[idx].split('=')
            values = parts[1].split(',')
            argv = '{}={}'.format(parts[0], ','.join(list(values + VYPER_BUILTINS)))
    else:
        argv.append('--builtins=' + ','.join(VYPER_BUILTINS))
    return argv


def or_sys_argv(argv):
    return (argv if argv is not None else sys.argv[1:])


def main(argv=None):
    # type: (Optional[List[str]]) -> None
    """Execute the main bit of the application.

    This handles the creation of an instance of :class:`Application`, runs it,
    and then exits the application.

    :param list argv:
        The arguments to be passed to the application for parsing.
    """
    patch_processor(FileProcessor)
    app = application.Application()
    patch_app_option_manager(app)
    app.run(add_vyper_builtins_to_argv(or_sys_argv(argv)))
    app.exit()

if __name__ == "__main__":
    main(sys.argv[1:])