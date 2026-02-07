from __future__ import annotations

import os
import sys
import re
from collections.abc import Callable, Sequence
from typing import TypeAlias, override

from wert import Context, flatten

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


TargetLike: TypeAlias = "Target | str"
InputLike: TypeAlias = "Target | Rule | str"
Inputs: TypeAlias = Sequence[InputLike]
Recipe: TypeAlias = Callable[[Context], None]
RecipeLike: TypeAlias = Recipe | str | Sequence[str]


class Rule:
    target: Target
    inputs: Inputs
    recipe: Recipe

    def __init__(
        self,
        target: TargetLike,
        inputs: Inputs | None = None,
        recipe: RecipeLike | None = None,
    ):
        target = _target(target)

        self.target = target
        self.inputs = inputs or []
        self.recipe = _recipe(recipe)

    @override
    def __str__(self):
        return self.target.name

    def execute(self, ctx: Context):
        first = self.inputs[0] if len(self.inputs) else None

        ctx = {
            **ctx,
            "<": first,
            "__first_input__": first,
            "^": self.inputs,
            "__inputs__": self.inputs,
            "@": self.target,
            "__target__": self.target,
        }
        (self.recipe)(ctx)


class Macher:
    rules: list[Rule]
    context: Context

    def __init__(self):
        self.rules = []
        self.context = {}

    def _log(self, msg: str):
        print(msg)

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def find_rule(self, name: str) -> Rule | None:
        # TODO: best match (for patterns)
        # TODO: maybe: multi-match (merge recipes and inputs)
        for r in self.rules:
            if r.target.matches(name):
                # TODO: "cook" the rule after a pattern match or group match
                return r

        return None

    def require_rule(self, name: str) -> Rule:
        rule = self.find_rule(name)

        if rule is None:
            raise Exception(f"No rule for making {name}")

        return rule

    def _input_rule(self, inp: InputLike) -> Rule:
        if isinstance(inp, Rule):
            return inp

        if isinstance(inp, str):
            rule = self.find_rule(inp)

            if rule:
                return rule

            if _is_file_name(inp):
                # The name looks like a file name.
                # Usefule for files under user control
                inp = File(inp)
            else:
                raise Exception(f"No rule for making {inp}")

        # The input is an inline target, define a trivial rule to wrap it.
        return Rule(inp)

    def mach(self, rule: Rule):
        self._log(f"making {rule}...")
        outdated = rule.target.outdated()

        for inp in rule.inputs:
            inp_rule = self._input_rule(inp)
            self.mach(inp_rule)
            outdated = rule.target.outdated(inp_rule.target)

        if outdated:
            rule.execute(self.context)
            self._log(f"...made {rule}.")
        else:
            self._log(f"...got {rule}.")


macher = Macher()


def mach(
    target: TargetLike, inputs: Inputs | None = None, recipe: RecipeLike | None = None
):
    # TODO: multi target
    rule = Rule(target, inputs, recipe)
    macher.add_rule(rule)
    return rule


def _is_file_name(name: str) -> bool:
    return "." in name or "/" in name


def _target(target: TargetLike) -> Target:
    # TODO: pattern target (use % or regex or glob)
    # TODO: target group
    if isinstance(target, str):  # note that str is a Sequence
        if _is_file_name(target):
            # if the name contains a dot or slash, it's a file
            return File(target)
        else:
            return Target(target)

    return target


def _recipe(recipe: RecipeLike | None) -> Recipe:
    if recipe is None:

        def null(_ctx: Context):
            pass

        return null
    elif isinstance(recipe, str):  # note that str is a Sequence
        return _shell(recipe)
    elif isinstance(recipe, Sequence):
        rr = [_recipe(r) for r in recipe]

        def sq(ctx: Context):
            for r in rr:
                r(ctx)

        return sq

    assert isinstance(recipe, Callable)
    return recipe


expand_pattern = re.compile(r"\$\(([^()'\r\n]+)\)|\$'([^()'\r\n]+)'|\$([^()'\s\w])|\$(\w+)")

def _expand_command(cmd: str, ctx: Context) -> str:
    def sub(match: re.Match[str]):
        quote = False
        if match.group(4) is not None:
            raise Exception(f"Found ambiguous variable expression {match.group(0)}. " +
                f"For the shell variable, use $${match.group(3)}. " +
                f"For the mach variable, use $({match.group(3)})."
            )
        elif match.group(3) is not None:
            k = match.group(3)
        elif match.group(2) is not None:
            # TODO: implement quoting as a function as well, for complex cases
            k = match.group(2)
            quote = True
        elif match.group(1) is not None:
            k = match.group(1)
        else:
            assert(False) # unreachable

        # $($) always means $
        if k == "$":
            return "$"

        # TODO: warn/fail on missing variables
        v = ctx.get(k)

        # TODO: resolve callables in nested lists
        if callable(v):
            v = v(ctx)

        return flatten(v, quote)

    # TODO: support function calls
    # TODO: support lisp-style nested calls
    return expand_pattern.sub(sub, cmd)

def _shell(cmd: str) -> Recipe:
    def f(ctx: Context):
        expanded_cmd = _expand_command(cmd, ctx)
        print("\t", expanded_cmd)

        # TODO: optionally suppress output
        # TODO: pipe into stdin to support multi-command recipes
        _ = _system(expanded_cmd)

    return f

def _system(cmd: str) -> int:
    return os.system(cmd)
