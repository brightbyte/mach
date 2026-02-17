from mach import mach, script, run, declare, Context, lazy, info

def setup(ctx: Context):
    ctx.export("test", "hello")

declare("TEST", "JUST A TEST", "A test value")
declare("lazy", lazy("lazy $(test)"))

mach("main", help="build mach.txt", inputs = [
        mach("_setup", [], setup),
        mach("vartest", ["_setup"],
           [ info("PWD: $(PWD)"), script("""
            echo $'(test)' $$TEST
            echo $'(lazy)'
        """) ], """testing variables,
        bla bla bla, yadda yadda, lorem ipsum dolor sit amet,
        the quick brown fox makes jack a dull boy."""),
    ])
