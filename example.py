from mach import *

mach("all", [
    mach("output.txt", ["mach.py"], "grep ^def $(<) $(xyz) > $(@)")
])
run()
