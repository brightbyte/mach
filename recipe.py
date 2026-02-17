import textwrap

from env import Environment, OutputMode
from wert import Context, expand_all

from typing import TypeAlias, Callable, Sequence, Any

Recipe: TypeAlias = Callable[[Context], None]
RecipeLike: TypeAlias = Recipe | str | Sequence['RecipeLike']
Options: TypeAlias = dict[str, Any]

DEFAULT_OPTIONS = {
    'echo': True,
    'check': True,
    'envars': {},
}

class Script:
    env: Environment
    cmd: str
    options: Options

    def __init__(self, env: Environment, cmd: str, options: Options|None):
        # NOTE: we have to use __dict__ in the constructor to bypass __setattr__!
        self.__dict__['env'] = env
        self.__dict__['cmd'] = textwrap.dedent(cmd.strip("\r\n"))

        options = options or {}
        self.__dict__['options'] = {
            **options,
            **DEFAULT_OPTIONS
        }

    def __getattr__(self, name):
        return self.options.get(name)

    def __setattr__(self, name, value):
        self.options[name] = value

    def __call__(self, ctx):
        expanded_cmd = expand_all(self.cmd, ctx)

        if self.echo:
            print(textwrap.indent(expanded_cmd, "> ").strip("\r\n"))

        kwargs = dict(self.options)
        envars = {
            **ctx.get_envars(),
            **kwargs['envars']
        }

        kwargs['envars'] = envars
        del kwargs['echo']
        del kwargs['check']

        code = self.env.execute(expanded_cmd, **kwargs)

        if self.check and code != 0:
            # TODO: kwargs['on_error']...
            raise Exception(f"Script returned error code {code}.")
