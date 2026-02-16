from mach import mach, script, run, declare, Context
from wert import flatten

mach("%.txt", ["%.py"], """
    mkdir -p output
    grep ^def $'<' > output/$'(__target__)'
""", """
    Make a txt file from a py file by greping for "def"
""")

def setup(ctx: Context):
    ctx.export("test", "hello")

declare("TEST", "JUST A TEST", "A test value")
declare("lazy", lambda ctx: "lazy var")

mach("main", help="build mach.txt", inputs = [
        mach("_setup", [], setup),
        "mach.txt",
        mach("vartest", [], script("""
            echo $'(test)' $$TEST
        """), "testing variables"),
    ])

run()
