from typing import Any
from dataclasses import dataclass
from simple_parsing import subparsers
from models.context import Context
from commands.tags import Tags
from commands.files import Files, SelectFiles
from commands.exit import Exit
from commands.route import Add, Remove, List, Diff, Save
from commands.reload import Reload

@dataclass
class Cli:
    command :Any = subparsers(
        {'tags': Tags,
         'files': Files,
         'add': Add,
         'remove': Remove,
         'list': List,
         'select': SelectFiles,
         'diff': Diff,
         'save': Save,
         'reload': Reload,
         'exit': Exit,
         })
    def run(self, context :Context):
        self.command.run(context)
