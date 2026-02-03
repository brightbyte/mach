from mach import *

mach(File("mach.py"))
mach(File("output.txt"), ["mach.py"], shell("grep ^def ${<} > ${@}"))
mach("all", ["output.txt"])
run()
