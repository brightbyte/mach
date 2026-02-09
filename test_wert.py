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
                except Exception as ex:
                    print(f"Exception caught with data set {case}")
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
        "f": lambda *p: "from a function",
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
            ( "#$'%'#", '#\'percent\'#' ),
            ( "#$(s)#", '#just a test#' ),
            ( "#$(s", Exception ),
            ( "#$(x y z)", SyntaxError ), # bad python
            ( "#$$variable#", '#$variable#' ),
            ( "#$%$$var#", '#percent$var#' ),
            ( "#$(undefined)#", NameError ),
            ( "#$(None)#", '##' ),
            ( "$(named)", 'named value' ),
            ( "ambiguous $named", Exception ),
            ( "shell $$named", 'shell $named' ),
            ( "$(with_dollar)", 'tricky $(value)' ),
            ( "$(f) as lazy variable", 'from a function as lazy variable' ),
            ( "$(f()) via call", 'from a function via call' ),
            ( "$(list) and $(tuple)", 'just a list and just a tuple' ),
            ( "$([s.upper() for s in list])", 'JUST A LIST' ),
            ( "$(quote(list)) and $(quote(tuple))", "'just' 'a' 'list' and 'just' 'a' 'tuple'" ),
            ( "$'(list)' and $'(tuple)'", "'just' 'a' 'list' and 'just' 'a' 'tuple'" ),
            ( "$(quote(nested_list))", "'just' 'a' 'list'" ),
            ( "$(quote(trixy))", "'\\'back\\\\slash\\''" ),
            ( "$'(trixy) thing", Exception ), # missing closing '
            ( "$(True) or $(False)", 'True or False' ),
            ( "$(three) < $(pi)", '3 < 3.14' ),
            ( "$(a + b)", '3' ),
        ]

    @data_provider(expand_all_cases)
    def test_expand_all(self, cmd, expected):
        ctx = wert.Context(WertTest.context)

        if isinstance(expected, str):
            self.assertEqual(expected, wert.expand_all(cmd, ctx))
        else:
            self.assertRaises(expected, lambda: wert.expand_all(cmd, ctx))

if __name__ == "__main__":
    unittest.main()
