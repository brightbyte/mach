from mach import mach, script, run, declare, Context

def setup(ctx: Context):
    ctx.export("test", "hello")

declare("TEST", "JUST A TEST", "A test value")
declare("lazy", lambda ctx: "lazy var")

mach("main", help="build mach.txt", inputs = [
        mach("_setup", [], setup),
        mach("vartest", ["_setup"], script("""
            echo $'(test)' $$TEST
        """), """testing variables,
        bla bla bla, yadda yadda, lorem ipsum dolor sit amet,
        the quick brown fox makes jack a dull boy."""),
    ])

run()
