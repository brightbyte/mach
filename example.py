from mach import *
from env import OutputMode

mach("all", [
        mach("output.txt", ["mach.py"], """
            echo "START"
            grep ^def $'<' > $'(__target__)'
            echo "END"
        """),
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
