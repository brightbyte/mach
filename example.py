from mach import *

mach(File("output.txt"), [File("mach.py")], "grep ^def $(<) > $(@)")
mach("all", ["output.txt"])
run()
