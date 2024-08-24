from dataclasses import dataclass
from models.context import Context

@dataclass
class Reload:
    def run(self, context :Context):
        context.__init__(context.root_path)