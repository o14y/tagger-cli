from typing import *
from dataclasses import dataclass
from simple_parsing import field
from models.context import Context
from controllers.captions import Captions

@dataclass
class Diff:
    absolute :bool = field(default=False, help='Show as absolute path')
    def run(self, context :Context):
        c = Captions(context)
        r = c.diff()
        print(f'* [ALL]: {', '.join(r.common)}')
        for path in sorted(r.dataset):
            tags = sorted(r.dataset[path])
            if not self.absolute:
                path = c.relative(context.root_path, path)
            print(f"* {path}: {', '.join(tags)}")
