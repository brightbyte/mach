import subprocess
import threading
import sys

from typing import TypeAlias, Callable, IO, Protocol
from enum import Enum

StdOutHandler: TypeAlias = Callable[[str], str]

EOF = None

class OutputHandler(Protocol):
    def handle(self, line: str | None): ...

class MuteHandler:
    def handle(self, line: str | None):
        pass

class LineHandler:
    def handle(self, line: str | None):
        if line is not None:
            sys.stdout.write(line)

class DeferredHandler:
    buffer: list[str]
    def __init__(self):
        self.buffer = []

    def handle(self, line: str | None):

        if line is None:
            sys.stdout.write( "".join(self.buffer) )
            self.buffer = []
        else:
            self.buffer.append(line)

class OutputMode(Enum):
    MUTE = MuteHandler
    LINES = LineHandler
    DEFERRED = DeferredHandler

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)  # pyright: ignore[reportAbstractUsage]

def _shovel( pipe: IO[str], handler: OutputHandler, encoding: str = 'utf-8' ):
    for line in iter(pipe.readline, ''):
        handler.handle(line)

    handler.handle(EOF)

def _start_shoveling(pipe: IO[str], handler: OutputHandler, **kwargs) -> threading.Thread:
    thread = threading.Thread(target=_shovel, args = [pipe, handler], kwargs = kwargs)
    thread.start()
    return thread

class Environment:
    shell: str
    encoding: str

    def __init__(self):
        self.shell = "/bin/sh"
        self.encoding = 'utf-8'

    def execute(self, script: str, output: OutputMode = OutputMode.LINES, shell: str | None = None, encoding: str | None = None ) -> int:
        encoding = str(encoding or self.encoding)

        p = subprocess.Popen(
            shell or self.shell,
            shell = False,
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            encoding = encoding)

        assert(p.stdin)
        assert(p.stdout)
        assert(p.stderr)

        _start_shoveling(p.stdout, output(), encoding = encoding)
        _start_shoveling(p.stderr, output(), encoding = encoding)

        p.stdin.write(script)
        p.stdin.close()

        p.wait()

        return p.returncode

    def print(self, s):
        print(s)
