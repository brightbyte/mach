from __future__ import annotations

import sys

import help
from macher import Macher, TargetLike, Inputs, RecipeLike, Script
from wert import VarValue, Context
from env import OutputMode

def run(*argv: str):
    if len(argv) == 0:
        argv = tuple(sys.argv)

    if len(argv) == 0:
        argv = ("mach", "all")

    if len(argv) == 1:
        argv = (argv[0], "all")

    for tgt in argv[1:]:
        rule = macher.require_rule(tgt)
        macher.mach(rule)

macher = Macher()

def define(key: str, value: VarValue):
    macher.context[key] = value

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
