
from dataclasses import dataclass
from typing import *
from simple_parsing import field, subparsers
from models.context import Context
from controllers.captions import Captions

@dataclass
class SelectFiles:
    exprs :List[str] = field(positional=True, hint='List of expressions to select files')
    all :bool = field(default=False, help='Select all files')
    def run(self, context :Context):
        c = Captions(context)
        if self.all:
            count = c.select_all_files()
        elif self.exprs:
            count = c.select_files(self.exprs)
        else:
            raise ValueError('Must provide expressions or use --all')
        print(f'{count} file{"s" if count>1 else ""} selected')

@dataclass
class ListFiles:
    absolute :bool = field(default=False, help='Show as absolute path')
    all :bool = field(default=False, help='Show only selected files')
    def run(self, context :Context):
        c = Captions(context)
        for i in c.list(selected=not self.all):
            p = i.path
            if not self.absolute:
                p = c.relative(context.root_path, p)
            print(f"* {p}: {', '.join(i.tags)}")

@dataclass
class AddFiles:
    def run(self, context :Context):
        pass

@dataclass
class Files(ListFiles):
    command: Any = subparsers(default=None,
                              positional=True,
                              subcommands={"list": ListFiles})
    def run(self, context :Context):
        if self.command:
            return self.command.run(context)
        return super().run(context)
