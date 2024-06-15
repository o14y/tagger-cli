from .dictionary import Dictionary
from pathlib import Path
import sqlite3
from models.dataset import Dataset
class Context():
    root_path: Path
    exiting: bool = False
    conn: sqlite3.Connection = sqlite3.connect(":memory:", autocommit=False)
    dictionary: Dictionary = Dictionary.load("assets/tags_ja-JP.csv")
    dataset :Dataset = None
    def __init__(self, path: Path):
        self.root_path = path
        self.dataset = Dataset(self.conn).load(path)
