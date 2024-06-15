from dataclasses import dataclass
from models.context import Context

@dataclass
class Exit:
    def run(self, context :Context):
        context.exiting = True
