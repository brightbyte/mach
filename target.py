from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import TypeAlias, override

from recipe import Recipe

class TargetMatch:
    raw_target: Target
    _cooked_target: Target | None

    def __init__(self, target: Target):
        self.raw_target = target
        self._cooked_target = None

    def cook_inputs(self, inputs: Sequence[str]) -> Sequence[str]:
        return [self.cook_name(inp) for inp in inputs]

    def cook_name(self, s: str) -> str:
        return s

    def get_cooked_target(self) -> Target:
        if self._cooked_target is None:
            name = self.cook_name(self.raw_target.name)

            if name != self.raw_target.name:
                self._cooked_target = self.raw_target.get_cooked(name)
            else:
                # Don't use a fresh Target if the name didn't change.
                # Targets are stateful!
                self._cooked_target = self.raw_target
        return self._cooked_target

    def cook_rule(self, rule: Rule) -> Rule:
        cooked_target = self.get_cooked_target()

        if cooked_target is rule.target:
            # cooking did nothing
            return rule

        return Rule(
            cooked_target,
            self.cook_inputs( rule.inputs ),
            rule.recipe,
            rule.help
        )


_percent_pattern = re.compile("%")


class PatternMatch(TargetMatch):
    match: re.Match

    def __init__(self, target: Target, match: re.Match):
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


class Target:
    name: str
    done: bool

    def __init__(self, name: str):
        self.name = name
        self.done = False

    def matches(self, name: str) -> TargetMatch | None:
        if name == self.name:
            return TargetMatch(self)
        else:
            return None

    def outdated(self, _other: Target | None = None) -> bool:
        return not self.done

    def get_cooked(self, name) -> Target:
        return Target(name)

    @override
    def __str__(self):
        return self.name


class File(Target):
    @override
    def outdated(self, other: Target | None = None) -> bool:
        if self.done:
            return False

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


class Rule:
    target: Target
    inputs: Sequence[InputLike]
    recipe: Recipe
    help:   str | None

    def __init__(
        self,
        target: TargetLike,
        inputs: Sequence[InputLike],
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

    def get_name(self):
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
