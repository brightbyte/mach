from __future__ import annotations

import os
import sys

import help
from macher import Macher, TargetLike, Inputs, RecipeLike, Script
from wert import VarValue, Context
from env import OutputMode

def run(*argv: str):
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
    target: TargetLike, inputs: Inputs | None = None, recipe: RecipeLike | None = None, help: str | None = None
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

mach( "help", (), help.recipe(macher), help.HELP )

__all__ = [
    'define', 'mach', 'run', 'script',
    'Context', 'OutputMode'
]
