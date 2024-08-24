
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any
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
    tag :str = field(default=None, help='Filter by tag')
    sort :bool = field(default=False, help='Sort tags')
    def run(self, context :Context):
        c = Captions(context)
        soreted_list = []
        for i in c.list(selected=not self.all, filter=self.tag):
            p = i.path
            if not self.absolute:
                p = c.relative(context.root_path, p)
            if self.sort:
                soreted_list.append((p, ', '.join(sorted(i.tags))))
            else:
                print(f"* {p}: {', '.join(i.tags)}")
        if self.sort:
            soreted_list = sorted(soreted_list, key=lambda x: x[1])
            for p, tags in soreted_list:
                print(f"* {p}: {tags}")

@dataclass
class DiffFiles:
    absolute :bool = field(default=False, help='Show as absolute path')
    def run(self, context :Context):
        c = Captions(context)
        r = c.diff()
        print(f'* [ALL]: {', '.join(r.common)}')
        for path in sorted(r.dataset):
            tags = sorted(r.dataset[path])
            if not self.absolute:
                path = c.relative(context.root_path, Path(path))
            print(f"* {path}: {', '.join(tags)}")

@dataclass
class SaveFiles:
    def run(self, context :Context):
        c = Captions(context)
        count = c.save()
        print(f"{count} file{'s' if count>1 else ''} saved")

@dataclass
class Files(ListFiles):
    command: Any = subparsers(default=None,
                              positional=True,
                              subcommands={"list": ListFiles,
                                           "select": SelectFiles,
                                           "diff": DiffFiles})
    def run(self, context :Context):
        if self.command:
            return self.command.run(context)
        return super().run(context)
