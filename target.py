from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import TypeAlias, override

from recipe import Recipe

class TargetMatch:
    target: Target

    def __init__(self, target: Target):
        self.target = target

    def cook_inputs(self, inputs: Inputs) -> Inputs:
        return [self.cook_input(inp) for inp in inputs]

    def cook_input(self, input: InputLike) -> InputLike:
        if isinstance(input, Rule):
            cooked = self.cook_rule( input )
        elif isinstance(input, Target):
            cooked = input.get_cooked( self.cook_name( input.name ) )
        else:
            cooked = self.cook_name( input )

        return cooked

    def cook_name(self, s: str) -> str:
        return s

    def get_cooked_target(self) -> Target:
        return self.target

    def cooked_target(self, target: Target) -> Target:
         return target.get_cooked( self.cook_name( target.name ) )

    def cook_rule(self, rule: Rule) -> Rule:
        return Rule(
            self.cooked_target( rule.target ),
            self.cook_inputs( rule.inputs ),
            rule.recipe,
            rule.help
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


class Rule:
    target: Target
    inputs: Inputs
    recipe: Recipe
    help:   str | None

    def __init__(
        self,
        target: TargetLike,
        inputs: Inputs,
        recipe: Recipe,
        help:   str|None = None
    ):
        self.target = to_target(target)
        self.inputs = inputs
        self.recipe = recipe
        self.help =   help

    @override
    def __str__(self):
        return self.target.name

    def matches(self, name: str) -> TargetMatch | None:
        return self.target.matches(name)

def is_file_name(name: str) -> bool:
    return "." in name or "/" in name

def to_target(target: TargetLike) -> Target:
    # TODO: pattern target (use % or regex or glob)
    # TODO: target group
    if isinstance(target, str):  # note that str is a Sequence
        if "%" in target:
            # if the name contains a percent, it's a pattern
            return Pattern(target)
        elif is_file_name(target):
            # if the name contains a dot or slash, it's a file
            return File(target)
        else:
            return Target(target)

    return target
