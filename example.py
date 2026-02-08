from mach import *

mach("all", [
    mach("output.txt", ["mach.py"], """
        echo "START"
        grep ^def $'<' > $'(__target__)'
        echo "END"
    """)
])
run()
