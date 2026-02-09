from mach import *
from env import OutputMode

mach("%.txt", ["%.py"], """
    grep ^def $'<' > $'(__target__)'
"""),

mach("all", [
        "mach.txt",
        mach("slow", [], script("""
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
