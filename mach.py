import os
import sys
from typing import Sequence

import help
from macher import Macher, TargetLike, RecipeLike, Script
from target import InputLike
from wert import VarValue, Context, expand_all, Function
from env import OutputMode
from recipe import Recipe

_disable_run = False

def run(*argv: str):
    if _disable_run:
        return

    if not argv:
        argv = tuple(sys.argv)

    targets = macher.process_argv(argv)
    for tgt in targets:
        rule = macher.require_rule(tgt)
        macher.mach(rule)

macher = Macher()
macher.set_variables( os.environ )

def declare(name: str, default: VarValue, cli: str|bool = False):
    """
    Declares a variable and initializes it with a adefault value.
    If the cli parameter is truthy, the variable can be specified on the
    command line using foo=bar syntax. If the value of the cli parameter
    is a string, that string will serve as the help message for the
    variable.
    """
    macher.declare(name, default, cli)

def mach(
    target: TargetLike, inputs: Sequence[InputLike] | None = None, recipe: RecipeLike | None = None, help: str | None = None
):
    # TODO: multi target
    rule = macher.make_rule(target, inputs, recipe, help)
    macher.add_rule(rule)
    return rule


def script(cmd: str, **kwargs) -> Script:
    return macher.script(cmd, **kwargs)

def blind(script: Script) -> Script:
    script.echo = False
    return script

def mute(script: Script) -> Script:
    script.output = OutputMode.MUTE
    return script

def lazy(s: str) -> Function:
    return lambda context, *args: expand_all(s, context)

def info(s: str) -> Recipe:
    return lambda context: print( expand_all(s, context) )

mach( "help", (), help.recipe(macher), help.HELP )

__all__ = [
    'declare', 'mach', 'run', 'script', 'lazy', 'info', 'mute', 'blind',
    'Context', 'OutputMode'
]

def main():
    argv = sys.argv
    machfile = 'Machfile.py'

    if not os.path.isfile(machfile):
        print( f"{machfile} not found" )
        exit(1)

    global _disable_run
    _disable_run = True
    with open(machfile, "rb") as src:
        code = compile(src.read(), machfile, "exec")

    # HACK: make sure the Machfile gets this module instance
    # when importing mach.
    module_name = os.path.splitext(os.path.basename(__file__))[0]
    if __package__:
            sys.modules[f'{__package__}.{module_name}'] = sys.modules['__main__']
    sys.modules[module_name] = sys.modules['__main__']

    globals = {}
    exec(code, globals, {})

    _disable_run = False
    run(*argv)

if __name__ == '__main__':
    main()
