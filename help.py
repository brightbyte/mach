import os, sys

from typing import Sequence
from macher import Macher, Rule

HELP = """
List all targets along with the help message associated with them.
"""

def can_use_ansi():
    # Respect NO_COLOR standard
    if os.environ.get('NO_COLOR'):
        return False

    # Avoid dumb terminals
    if os.environ.get('TERM') == 'dumb':
        return False

    # Must be a terminal
    if not sys.stdout.isatty():
        return False

    return True

if can_use_ansi():
    BOLD = "\033[1m"
    RESET = "\033[0m"
else:
    BOLD = RED = RESET = ""

def _bold(s):
    return BOLD + s + RESET

def _print(*s):
    print(*s)

def _normalize(msg):
    if not msg:
        return "(no help)"
    else:
        return msg.strip()

def _print_rule_help(rule: Rule):
    _print( _bold(f"{rule.target.name}:"), _normalize(rule.help) )

def _print_all_help(rules: Sequence[Rule]):
    for rule in rules:
        if rule.target.name.startswith('_'):
            # private helper target
            continue

        _print_rule_help(rule)

def recipe(macher: Macher):
    return lambda ctx: _print_all_help(macher.rules)
