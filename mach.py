from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import TypeAlias, override


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


class Target:
    name: str

    def __init__(self, name: str):
        self.name = name

    def matches(self, name: str):
        return name == self.name

    def outdated(self, _other: Target | None = None) -> bool:
        return True

    @override
    def __str__(self):
        return self.name


class File(Target):
    @override
    def outdated(self, other: Target | None = None) -> bool:
        try:
            mtime = os.path.getmtime(self.name)
            if other is None:
                return False
            elif isinstance(other, File):
                other_mtime = os.path.getmtime(other.name)
                return mtime < other_mtime

        except IOError:
            pass

        return True


Inputs: TypeAlias = list[str] | tuple[str]
Recipe: TypeAlias = Callable[[Target, Inputs], None]


class Rule:
    target: Target
    inputs: Inputs
    recipe: Recipe | None

    def __init__(
        self,
        target: Target | str,
        inputs: Inputs | None = None,
        recipe: Recipe | None = None,
    ):
        if not isinstance(target, Target):
            target = Target(target)

        self.target = target
        self.inputs = inputs or []
        self.recipe = recipe

    @override
    def __str__(self):
        return self.target.name

    def execute(self):
        if self.recipe:
            (self.recipe)(self.target, self.inputs)


class Macher:
    rules: list[Rule]

    def __init__(self):
        self.rules = []

    def _log(self, msg: str):
        print(msg)

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def find_rule(self, name: str) -> Rule | None:
        for r in self.rules:
            if r.target.matches(name):
                return r

        return None

    def require_rule(self, name: str) -> Rule:
        rule = self.find_rule(name)

        if rule is None:
            raise Exception(f"No rule matching {name}")

        return rule

    def mach(self, rule: Rule):
        self._log(f"making {rule}...")
        outdated = rule.target.outdated()
        for inp in rule.inputs:
            inp_rule = self.require_rule(inp)

            self.mach(inp_rule)
            outdated = rule.target.outdated(inp_rule.target)

        if outdated:
            rule.execute()
            self._log(f"...done {rule}")
        else:
            self._log(f"...skipped {rule}")


macher = Macher()


def mach(
    target: Target | str, inputs: Inputs | None = None, recipe: Recipe | None = None
):
    macher.add_rule(Rule(target, inputs, recipe))


def shell(cmd: str) -> Recipe:
    def f(target: Target, inputs: Inputs):
        first = inputs[0] if len(inputs) > 0 else ""
        effective_cmd = cmd.replace("${@}", str(target)).replace("${<}", first)

        print("\t", effective_cmd)
        _ = os.system(effective_cmd)

    return f
