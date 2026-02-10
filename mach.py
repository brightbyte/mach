from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Sequence
from typing import TypeAlias, override

from env import Environment
from wert import Context, VarValue, expand_all


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


class TargetMatch:
    target: Target

    def __init__(self, target: Target):
        self.target = target

    def cook_inputs(self, inputs: Inputs) -> Inputs:
        return [self.cook_input(inp) for inp in inputs]

    def cook_input(self, input: InputLike) -> InputLike:
        if isinstance(input, Rule):
            return self.cook_rule( input )
        elif isinstance(input, Target):
            return input.get_cooked( self.cook_name( input.name ) )
        else:
            return self.cook_name( input )

    def cook_name(self, s: str) -> str:
        return s

    def get_cooked_target(self) -> Target:
        return self.target

    def cook_rule(self, rule: Rule) -> Rule:
        return Rule(
            self.get_cooked_target(),
            self.cook_inputs( rule.inputs ),
            rule.recipe
        )


_percent_pattern = re.compile("%")


class PatternMatch(TargetMatch):
    match: re.Match

    def __init__(self, target: "Target", match: re.Match):
        super().__init__(target)
        self.match = match

    @override
    def cook_name(self, s: str) -> str:
        idx = [1]  # holder

        def f(_: re.Match):
            v = self.match.group(idx[0])
            idx[0] += 1
            return v

        return _percent_pattern.sub(f, s)

    @override
    def get_cooked_target(self) -> "Target":
        name = self.cook_name(self.target.name)
        return File(name)  # TODO: use a factory/class object


class Target:
    name: str

    def __init__(self, name: str):
        self.name = name

    def matches(self, name: str) -> TargetMatch | None:
        if name == self.name:
            return TargetMatch(self)
        else:
            return None

    def outdated(self, _other: Target | None = None) -> bool:
        return True

    def get_cooked(self, name):
        return Target(name)

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

    @override
    def get_cooked(self, name):
         return File(name)


class Pattern(Target):
    name: str
    pattern: re.Pattern

    def __init__(self, name: str):
        super().__init__(name)

        p = name.replace("%", "(.*?)")
        self.pattern = re.compile(p)

    @override
    def matches(self, name: str) -> TargetMatch | None:
        match = self.pattern.fullmatch(name)
        if match is None:
            return None
        else:
            return PatternMatch(self, match)

    @override
    def get_cooked(self, name):
        # XXX: always File?
        return File(name)


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
        inputs: Inputs,
        recipe: Recipe,
    ):
        target = _target(target)

        self.target = target
        self.inputs = inputs
        self.recipe = recipe

    @override
    def __str__(self):
        return self.target.name

    def execute(self, ctx: Context):
        first = self.inputs[0] if len(self.inputs) else None

        ctx = ctx.new_child({
            "<": first,
            "__first_input__": first,
            "^": self.inputs,
            "__inputs__": self.inputs,
            "@": self.target,
            "__target__": self.target,
        })

        (self.recipe)(ctx)

    def matches(self, name: str) -> TargetMatch | None:
        return self.target.matches(name)


class Macher:
    rules: list[Rule]
    context: Context

    def __init__(self):
        self.rules = []
        self.context = Context()
        self.env = Environment()

        # FIXME: this MUST not be overwritten! It implements $$ as an escape for $!
        self.context["$"] = "$"

    def _log(self, msg: str):
        print(msg)

    def add_rule(self, rule: Rule):
        self.rules.append(rule)

    def make_rule(
        self,
        target: TargetLike,
        inputs: Inputs | None = None,
        recipe: RecipeLike | None = None,
    ):
        return Rule(target, inputs or [], self._recipe(recipe))

    def find_rule(self, name: str) -> Rule | None:
        # TODO: best match (for patterns)
        # TODO: maybe: multi-match (merge recipes and inputs)
        for r in self.rules:
            match = r.matches(name)
            if match is not None:
                return match.cook_rule( r )

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
        return self.make_rule(inp)

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

    def _recipe(self, recipe: RecipeLike | None) -> Recipe:
        if recipe is None:

            def null(_ctx: Context):
                pass

            return null
        elif isinstance(recipe, str):  # note that str is a Sequence
            return self.script(recipe)
        elif isinstance(recipe, Sequence):
            rr = [self._recipe(r) for r in recipe]

            def sq(ctx: Context):
                for r in rr:
                    r(ctx)

            return sq

        assert isinstance(recipe, Callable)
        return recipe

    def script(self, cmd: str, echo=True,  **kwargs) -> Recipe:
        def f(ctx: Context):
            expanded_cmd = expand_all(cmd, ctx)

            if echo:
                print("\t", expanded_cmd)

            envars = ctx.get_envars()

            if 'envars' in kwargs:
                envars = {
                    **envars,
                    **kwargs['envars']
                }

            kwargs['envars'] = envars

            # TODO: Fail on non-zero return code!
            # TODO: optionally suppress output
            code = self.env.execute(expanded_cmd, **kwargs)

            if code != 0:
                # TODO: kwargs['on_error']...
                raise Exception(f"Script returned error code {code}.")

        return f


macher = Macher()

def define(key: str, value: VarValue):
    macher.context[key] = value

def mach(
    target: TargetLike, inputs: Inputs | None = None, recipe: RecipeLike | None = None
):
    # TODO: multi target
    rule = macher.make_rule(target, inputs, recipe)
    macher.add_rule(rule)
    return rule


def script(cmd: str, **kwargs):
    return macher.script(cmd, **kwargs)


def _is_file_name(name: str) -> bool:
    return "." in name or "/" in name


def _target(target: TargetLike) -> Target:
    # TODO: pattern target (use % or regex or glob)
    # TODO: target group
    if isinstance(target, str):  # note that str is a Sequence
        if "%" in target:
            # if the name contains a percent, it's a pattern
            return Pattern(target)
        elif _is_file_name(target):
            # if the name contains a dot or slash, it's a file
            return File(target)
        else:
            return Target(target)

    return target
