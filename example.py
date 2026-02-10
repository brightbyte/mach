from mach import mach, script, run, define
from wert import Context
from env import OutputMode

mach("%.txt", ["%.py"], """
    mkdir -p output
    grep ^def $'<' > output/$'(__target__)'
""")

def setup(ctx: Context):
    ctx.export("test", "hello")

define("DONE", "done.")

mach("all", [
        mach("setup", [], setup),
        "mach.txt",
        mach("slow", [], script("""
            echo $(test)
            echo ONE
            sleep 1
            echo TWO
            sleep 1
            echo THREE
            echo $$DONE
        """)),
    ])

run()
