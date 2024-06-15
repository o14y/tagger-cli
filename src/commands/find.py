from typing import *
from dataclasses import dataclass
from simple_parsing import field
from models.context import Context

@dataclass
class Find:
    tag :str = field(help='Tag to search for')
    def run(self, context :Context):
        s = context.index.find(self.tag)
        for c in sorted(s):
            print(c)
