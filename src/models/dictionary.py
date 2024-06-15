from pathlib import Path
import pandas as pd
from pydantic import BaseModel, ConfigDict

class Dictionary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: pd.DataFrame = None
    @classmethod
    def load(cls, path:Path) -> 'Dictionary':
        d = cls()
        d.data = pd.read_csv(path, index_col=0)
        return d
    def __getitem__(self, key):
        k = key.strip()
        if not k in self.data.index:
            return None
        return self.data.loc[k, self.data.columns[0]]
