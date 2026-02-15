from mach import mach, script, run, define, Context

mach("%.txt", ["%.py"], """
    mkdir -p output
    grep ^def $'<' > output/$'(__target__)'
""", """
    Make a txt file from a py file by greping for "def"
""")

def setup(ctx: Context):
    ctx.export("test", "hello")

define("DONE", "done.")

mach("all", help="build mach.txt", inputs = [
        mach("_setup", [], setup),
        "mach.txt",
        mach("slow", [], script("""
            echo $(test)
            echo ONE
            sleep 1
            echo TWO
            sleep 1
            echo THREE
            echo $$DONE
        """), "a slow script that does nothing useful"),
    ])

run()
