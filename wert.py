import re

from typing import TypeAlias, Protocol, override
from collections import ChainMap
from collections.abc import Sequence

class Stringable(Protocol):
    @override
    def __str__(self) -> str: ...

class Function(Protocol):
    def __call__(self, context: "Context", *args: str) -> "VarValue": ...


VarValue: TypeAlias = (
    str | int | float | bool | Stringable | Function | Sequence["VarValue"] | None
)

_envar_pattern = re.compile(r'[A-Z_]+')

class Context(ChainMap[str, VarValue]):
    def export(self, key: str, value: VarValue):
        # update key in base map
        self.maps[-1][key] = value

    @override
    def new_child(self, m=None, **kwargs) -> 'Context':
        # A bit hacky...
        child = super().new_child(m, **kwargs)
        return Context( *child.maps )

    @property
    def parents(self) -> 'Context':
        # A bit hacky...
        parents = super().parents
        return Context( *parents.maps )

    def get_envars(self) -> dict[str, str]:
        envars = { key: flatten(value) for (key, value) in self.items() if _envar_pattern.fullmatch(key) }

        return envars


Quotable: TypeAlias = Stringable | None | Sequence["Quotable"]

def quote(x: Quotable):
    return flatten(x, True)

def flatten(x: Quotable, quote = False) -> str:
    if x is None:
        x = ""

    if isinstance(x, Sequence) and not isinstance(
        x, str
    ):  # note that str is a Sequence
        ss = [flatten(s, quote) for s in x]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        return " ".join(ss)
    elif quote:
        s = str(x).replace('\\', '\\\\').replace('\'', '\\\'')
        return "'" + s + "'"
    else:
        return str(x)

_var_pattern = re.compile(r'\$\'?(.)')
_name_pattern = re.compile(r'\w+')

def _expand_next(s: str, ctx: Context) -> tuple[str, str]:

    match = _var_pattern.search(s)

    if match is None:
        return ( s, "" )

    quoted = match.group(0).startswith("$'")
    key = match.group(1)
    prefix = s[:match.start()]

    if _name_pattern.fullmatch(key):
        raise Exception("Ambiguous variable "  + key)
    elif key == "(":
        exp = s[match.end():]

        # python expression in parentacies. Try to parse up to the first syntax error,
        # then expect the closing parantecie at that location.
        # No syntax error means missing closing parantecie.
        try:
            ast = compile(exp, '<mach>', 'eval')
            raise Exception("Expression started with $( was never closed'")
        except SyntaxError as err:
            if err.offset is None:
                raise err

            # Trim to location of first syntax error, which should be ")".
            # The result should be a valid expression.
            exp = exp[:err.offset-1]

        if len(exp.strip()) == 0:
            raise Exception("Expression is empty")

        end = match.end()+len(exp)
        closing = ")'" if quoted else ")"

        if s[ end : end+len(closing) ] != closing:
            raise Exception("Expected closing " + closing)

        remainder = s[end+len(closing):]

        ast = compile(exp, '<mach>', 'eval')
        v = eval(ast, globals(), ctx) # FIXME: strip private stuff from global scope

    else:
        end = match.end()

        if quoted:
            if s[ end ] != "'":
                raise Exception("Expected closing single quote")
            end += 1

        # TODO: warn/fail on missing variables
        v = ctx.get(key)
        remainder = s[end:]

    # TODO: resolve callables in nested lists
    while callable(v):
        v = v(ctx)

    result = flatten(v, quoted)
    return ( prefix + result, remainder )

_line_pattern = re.compile(r'(.*?)([\r\n]+|$)')

def expand_all(s: str, ctx: Context) -> str:
    result = ""

    for (remainder, eol) in _line_pattern.findall(s):
        while len(remainder)>0:
            (chunk, remainder) = _expand_next(remainder, ctx)
            result += chunk
        result += eol

    return result
