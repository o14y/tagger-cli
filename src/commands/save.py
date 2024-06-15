from models.context import Context
from dataclasses import dataclass
from controllers.captions import Captions

@dataclass
class Save:
    def run(self, context :Context):
        c = Captions(context)
        count = c.save()
        print(f"{count} file{'s' if count>1 else ''} saved")
