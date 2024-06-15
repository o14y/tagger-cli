from typing import *
from dataclasses import dataclass
from simple_parsing import subparsers
from models.context import Context
from .tags import Tags
from .files import Files
from .files import SelectFiles
from .diff import Diff
from .save import Save
from .exit import Exit
from .list import List as ListCommand

@dataclass
class Cli:
    command :Any = subparsers(
        {'tags': Tags,
         'files': Files,
         'list': ListCommand,
         'select': SelectFiles,
         'diff': Diff,
         'save': Save,
         'exit': Exit,
         })
    def run(self, context :Context):
        self.command.run(context)
