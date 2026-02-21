from mach import mach, script, run, declare, Context, makes

import random

mach("%.txt", ["%.py"], """
    mkdir -p output
    grep ^def $'<' > output/$'(__target__)'
""", """
    Make a txt file from a py file by greping for "def"
""")

@makes('something')
def something(ctx: Context):
    """just a function that does something"""
    print("SOMETHING")

def setup(ctx: Context):
    ctx.export("test", "hello")

declare("TEST", "JUST A TEST", "A test value")
declare("lazy", lambda ctx: "lazy var")
declare("random", random)
declare("dict", {"x": 1, "y": 2} )

mach("main", help="build mach.txt", inputs = [
        mach("_setup", [], setup),
        "mach.txt",
        mach("vartest", [], script("""
            echo $'(test)' $$TEST
            echo random: $'(random.random())'
            echo dict: $(dict)
        """), "testing variables"),
    ])

run()
