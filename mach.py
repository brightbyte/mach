from __future__ import annotations

import os
import sys
from collections.abc import Callable, Sequence
from typing import Protocol, TypeAlias, override

class Stringable(Protocol):
    @override
    def __str__(self) -> str:
        ...

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
Recipe: TypeAlias = Callable[[Target, Inputs], None]
RecipeLike: TypeAlias = Recipe | str | Sequence[str]


class Rule:
    target: Target
    inputs: Inputs
    recipe: Recipe

    def __init__(
        self,
        target: TargetLike,
        inputs: Inputs | None = None,
        recipe: RecipeLike | None = None
    ):
        target = _target(target)

        self.target = target
        self.inputs = inputs or []
        self.recipe = _recipe(recipe)

    @override
    def __str__(self):
        return self.target.name

    def execute(self):
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
            rule.execute()
            self._log(f"...made {rule}.")
        else:
            self._log(f"...got {rule}.")


macher = Macher()


def mach(
    target: TargetLike, inputs: Inputs | None = None, recipe: RecipeLike | None = None
):
    rule = Rule(target, inputs, recipe)
    macher.add_rule(rule)
    return rule

def _is_file_name(name: str) -> bool:
    return '.' in name or '/' in name

def _target(target: TargetLike) -> Target:
    if isinstance(target, str): # note that str is a Sequence
        if _is_file_name(target):
            # if the name contains a dot or slash, it's a file
            return File(target)
        else:
            return Target(target)

    return target

def _recipe(recipe: RecipeLike | None) -> Recipe:
    if recipe is None:
        def null(_target: Target, _inputs: Inputs):
            pass
        return null
    elif isinstance(recipe, str): # note that str is a Sequence
        return _shell(recipe)
    elif isinstance(recipe, Sequence):
        rr = [ _recipe(r) for r in recipe ]

        def sq(target: Target, inputs: Inputs):
            for r in rr:
                r(target, inputs)
        return sq

    assert( isinstance(recipe, Callable) )
    return recipe

Quotable: TypeAlias = Stringable|Sequence['Quotable']

def _quote( x: Quotable ) -> str:
    if isinstance(x, Sequence) and not isinstance(x, str): # note that str is a Sequence
        ss = [ _quote(s) for s in x ]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        return " ".join(ss)
    else:

        # TODO: proper escaping!
        return '"' + str(x) + '"'

def _shell(cmd: str) -> Recipe:
    def f(target: Target, inputs: Inputs):
        first = inputs[0] if len(inputs) > 0 else ""

        # TODO: resolve variables from context
        # TODO: support $@ as well as $(@), but fail on $foo
        # TODO: support function calls
        # TODO: support lisp-style nested calls
        # TODO: resolve $$ and $($) to $
        effective_cmd = cmd.replace("$(@)", _quote(target)).replace("$(<)", _quote(first))

        print("\t", effective_cmd)

        # TODO: optionally suppress output
        # TODO: pipe into stdin to support multi-command recipes
        _ = os.system(effective_cmd)

    return f
