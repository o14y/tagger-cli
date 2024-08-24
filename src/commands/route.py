from typing import Any, TypeVar, Generic
from dataclasses import dataclass
from simple_parsing import subparsers
from models.context import Context
from commands.tags import AddTags, ListTags, RemoveTags
from commands.files import DiffFiles, ListFiles, SaveFiles

T = TypeVar('T')

@dataclass
class Route:
    command: Any = None
    def run(self, context :Context):
        if self.command:
            self.command.run(context)
        else:
            super().run(context)

@dataclass
class List(Route, ListTags):
    command: Any = subparsers(positional=True,
                              default=None,
                              subcommands={"files": ListFiles,
                                           "tags": ListTags})

@dataclass
class Add(Route):
    command: Any = subparsers(positional=True, 
                              subcommands={'tags': AddTags})

@dataclass
class Remove(Route):
    command: Any = subparsers(positional=True,
                              subcommands={'tags': RemoveTags})

@dataclass
class Diff(Route, DiffFiles):
    command: Any = subparsers(positinal=True,
                              default=None,
                              subcommands={'files': DiffFiles})

@dataclass
class Save(Route, SaveFiles):
    command: Any = subparsers(positional=True,
                              default=None,
                              subcommands={'files': SaveFiles})
