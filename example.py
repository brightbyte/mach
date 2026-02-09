from mach import mach, script, run
from wert import Context
from env import OutputMode

mach("%.txt", ["%.py"], """
    mkdir -p output
    grep ^def $'<' > output/$'(__target__)'
""")

def setup(ctx: Context):
    ctx.export("test", "hello")

mach("all", [
        mach("setup", [], setup),
        "mach.txt",
        mach("slow", [], script("""
            echo $(test)
            echo ONE
            sleep 1
            echo TWO
            sleep 2
            echo THREE
        """, output = OutputMode.DEFERRED, echo = False)),
        mach("calc", [], script("""
            2^3
        """, echo = False, shell = '/usr/bin/bc' )),
    ])

run()
