#!/usr/bin/env python3

import unittest
import wert

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

class WertTest(unittest.TestCase):
    context = {
        "%": "percent",
        "$": "$",
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
        "a": 1,
        "b": 2,
    }

    @staticmethod
    def expand_all_cases() -> list[tuple[str,str|type[Exception]]]:
        return [
            ( "", ""),
            ( "a b c", "a b c"),
            ( "#$%#", '#percent#' ),
            ( "#$(s)#", '#just a test#' ),
            ( "#$$variable#", '#$variable#' ),
            ( "#$%$$var#", '#percent$var#' ),
            ( "#$(undefined)#", NameError ),
            ( "#$(None)#", '##' ), # FIXME
            ( "$(named)", 'named value' ),
            ( "$(with_dollar)", 'tricky $(value)' ),
            ( "$(f)", 'from a function' ),
            ( "$(list) and $(tuple)", 'just a list and just a tuple' ),
            ( "$([s.upper() for s in list])", 'JUST A LIST' ),
            ( "$(quote(list)) and $(quote(tuple))", "'just' 'a' 'list' and 'just' 'a' 'tuple'" ),
            ( "$(quote(nested_list))", "'just' 'a' 'list'" ),
            ( "$(quote(trixy))", "'\\'back\\\\slash\\''" ),
            ( "$(True) or $(False)", 'True or False' ),
            ( "$(three) < $(pi)", '3 < 3.14' ),
            ( "$(a + b)", '3' ),
        ]

    @data_provider(expand_all_cases)
    def test_expand_all(self, cmd, expected):
        if isinstance(expected, str):
            self.assertEqual(expected, wert.expand_all(cmd, WertTest.context))
        else:
            self.assertRaises(expected, lambda: wert.expand_all(cmd, WertTest.context))

if __name__ == "__main__":
    unittest.main()
