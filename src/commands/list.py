from typing import Any
from simple_parsing import subparsers
from models.context import Context
from dataclasses import dataclass
from .files import ListFiles
from .tags import ListTags

@dataclass
class List:
    command: Any = subparsers(positional=True,
                              subcommands={"files": ListFiles,
                                           "tags": ListTags})
    def run(self, context :Context):
        return self.command.run(context)
