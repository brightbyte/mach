#!/usr/bin/env python3

import unittest
import mach

def data_provider(fn_data_provider):
    """Data provider decorator, allows another callable to provide the data for the test
    Copied from https://pypi.org/project/unittest-data-provider/ by jpic (MIT license).
    """
    def test_decorator(fn):
        def repl(self, *args):
            for case in fn_data_provider():
                try:
                    fn(self, *case)
                except AssertionError as ex:
                    print(f"Assertion error caught with data set {case}")
                    raise ex
        return repl
    return test_decorator

class MachTest(unittest.TestCase):
    context = {
        "%": "percent",
        "s": "just a test",
        "named": "named value",
        "with_dollar": "tricky $(value)",
        "f": lambda _: "from a function",
        "list": [ "just", "a", "list" ],
        "nested_list": [ "just", [ "a", ( "list", ) ] ],
        "tuple": ( "just", "a", "tuple" ),
        "trixy": "'back\\slash'",
        "False": False,
        "True": True,
        "None": None,
        "three": 3,
        "pi": 3.14,
    }

    @staticmethod
    def expand_command_cases() -> list[tuple[str,str]]:
        return [
            ( "", ""),
            ( "a b c", "a b c"),
            ( "#$%#", '#percent#' ),
            ( "#$(s)#", '#just a test#' ),
            ( "#$$variable#", '#$variable#' ),
            ( "#$%$$var#", '#percent$var#' ),
            ( "#$($)#", '#$#' ),
            ( "#$(undefined)#", '##' ),
            ( "#$(None)#", '##' ), # FIXME
            ( "$(named)", 'named value' ),
            ( "$(with_dollar)", 'tricky $(value)' ),
            ( "$(f)", 'from a function' ),
            ( "$(list) and $(tuple)", 'just a list and just a tuple' ),
            ( "$'list' and $'tuple'", "'just' 'a' 'list' and 'just' 'a' 'tuple'" ),
            ( "$'nested_list'", "'just' 'a' 'list'" ),
            ( "$'trixy'", "'\\'back\\\\slash\\''" ),
            ( "$(True) or $(False)", 'True or False' ),
            ( "$(three) < $(pi)", '3 < 3.14' ),
        ]

    @data_provider(expand_command_cases)
    def test_expand_command(self, cmd, expected):
        self.assertEqual(expected, mach._expand_command(cmd, MachTest.context))

if __name__ == "__main__":
    unittest.main()
