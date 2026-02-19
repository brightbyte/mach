from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Mapping

from target import TargetLike, InputLike, Rule, File, is_file_name
from recipe import Recipe, RecipeLike, Script
from env import Environment
from wert import Context, VarValue

_VAR_NAME_PATTERN = re.compile( r'(\w\w+)' )
_FLAG_PATTERN = re.compile( _VAR_NAME_PATTERN.pattern + r'=(.*)' )
_OPTION_PATTERN = re.compile( r'--' + _VAR_NAME_PATTERN.pattern + r'(?:=(.*))?' )
_DEFAULT_OPTIONS = {}

class Macher:
    rules: list[Rule]
    context: Context
    flags: dict[str, str|bool]
    options: dict[str, str|bool]

    def __init__(self):
        self.rules = []
        self.context = Context()
        self.env = Environment()
        self.flags = {}
        self.options = dict(_DEFAULT_OPTIONS)

        # FIXME: this MUST not be overwritten! It implements $$ as an escape for $!
        self.context["$"] = "$"

    def _log(self, msg: str):
        print(msg)

    def add_rule(self, rule: Rule):
        #for r in self.rules:
        #    if rule.target.name == r.target.name:
        #        raise ValueError(f"There already is a rule for making {rule.target.name}")

        print("ADD RULE", rule)
        self.rules.append(rule)

    def make_rule(
        self,
        target: TargetLike,
        inputs: Sequence[InputLike] | None = None,
        recipe: RecipeLike | None = None,
        help:   str | None = None
    ):
        input_rules = [ self._input_rule(inp) for inp in inputs or [] ]
        input_names = [ inp_rule.target.name for inp_rule in input_rules ]
        return Rule(target, input_names, self._recipe(recipe), help)

    def find_rule(self, name: str) -> Rule | None:
        # TODO: best match (for patterns)
        # TODO: maybe: multi-match (merge recipes and inputs)
        for r in self.rules:
            match = r.matches(name)
            if match is not None:
                cooked = match.cook_rule( r )

                if cooked.target.name != r.target.name:
                    # remember the cooked rule, so we re-use it if we need it again.
                    self.add_rule( cooked )

                return cooked

        return None

    def require_rule(self, name: str) -> Rule:
        rule = self.find_rule(name)

        if rule is None:
            raise ValueError(f"No rule for making {name}")

        return rule

    def _input_rule(self, inp: InputLike) -> Rule:
        if isinstance(inp, Rule):
            return inp

        if isinstance(inp, str):
            rule = self.find_rule(inp)

            if rule:
                return rule

            if is_file_name(inp):
                # The name looks like a file name.
                # Usefule for files under user control
                inp = File(inp)
            else:
                raise ValueError(f"No rule for making {inp}")

        # The input is an inline target, define a trivial rule to wrap it.
        rule = self.make_rule(inp)
        self.add_rule( rule )
        return rule

    def execute(self, rule: Rule):
        first = rule.inputs[0] if len(rule.inputs) else None

        ctx = self.context.new_child({
            "<": first,
            "__first_input__": first,
            "^": rule.inputs,
            "__inputs__": rule.inputs,
            "@": rule.target,
            "__target__": rule.target,
        })

        (rule.recipe)(ctx)

        # Make each target only once
        rule.target.done = True

    def mach(self, rule: Rule):
        self._log(f"making {rule}...")
        outdated = rule.target.outdated()

        for inp in rule.inputs:
            inp_rule = self.require_rule(inp)
            self.mach(inp_rule)
            outdated = outdated or rule.target.outdated(inp_rule.target)

        if outdated:
            self.execute(rule)
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

    def script(self, cmd: str, **kwargs) -> Script:
        return Script(self.env, cmd, kwargs)

    def set_var(self, name: str, value: VarValue):
        self.context[name] = value

    def set_variables(self, values: Mapping[str, VarValue]):
        for name, value in values.items():
            self.set_var(name, value)

    def declare(self, name: str, default: VarValue, cli: str|bool = False):
        """
        Declares a variable and initializes it with a adefault value.
        If the cli parameter is truthy, the variable can be specified on the
        command line using foo=bar syntax. If the value of the cli parameter
        is a string, that string will serve as the help message for the
        variable.
        """

        if not _VAR_NAME_PATTERN.fullmatch(name):
            raise ValueError( f'Not a valid variable name: {name}' )

        self.flags[name] = cli
        self.context[name] = default

    def set_cli_flag(self, name: str, value: VarValue):
        if name not in self.flags:
            raise ValueError( f"Undeclared flag {name}" )

        if not self.flags[name]:
            raise ValueError( f"Flag {name} cannot be set on the command line" )

        self.set_var(name, value)

    def set_cli_option(self, name: str, value: str|bool):
        if name not in self.options:
            raise ValueError( f"Unknown option {name}" )

        if isinstance(self.options[name], bool) and not isinstance(value, bool):
            raise ValueError( f"Expected no value for option {bool}" )

        if not isinstance(self.options[name], bool) and isinstance(value, bool):
            raise ValueError( f"Expected value for option {bool}" )

        self.options[name] = value

    def process_argv(self, argv: Sequence[str]) -> Sequence[str]:
        """
        Process command line arguments and extract any flags and options.
        Returns a list of targets to make (at least one).
        """

        if not argv:
            argv = ("mach")

        targets = []

        for item in argv[1:]:
            match = _OPTION_PATTERN.fullmatch( item )
            if match:
                key = match.group(1)
                value = match.group(2) or True

                self.set_cli_option(key, value)
                continue

            match = _FLAG_PATTERN.fullmatch( item )
            if match:
                key = match.group(1)
                value = match.group(2)

                self.set_cli_flag(key, value)
                continue

            # Not an option or flag, must be the name of a target, then.
            targets.append(item)

        if not targets:
            targets = ("main",)

        return targets
