import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Set
from controllers.transaction import Txn

SUPPORTED_FORMATS = set(['.jpg', '.jpeg', '.png', '.webp'])

class Dataset:
    conn :sqlite3.Connection = None
    def __init__(self, connection):
        self.conn = connection
    '''
    Select all files in the dataset.
    Create a table named 'selected' if not there and set default values.
    '''
    def _select_all_files(self):
        with Txn.begin(self.conn) as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS selected (path TEXT PRIMARY KEY)")
            cur.execute("DELETE FROM selected")
            cur.execute("INSERT INTO selected (path) SELECT path FROM images")
            return cur.rowcount
    '''
    Load images as dataset from the given path.
    Create a table named 'images' if not there and set default values.
    '''
    def load(self, path: Path):
        with Txn.begin(self.conn) as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS images (path TEXT PRIMARY KEY, tags JSON)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_images_tags ON images (JSON_EXTRACT(tags, '$'))")
            cur.execute("DELETE FROM images")
            for base, _, filenames in os.walk(path):
                for n in filenames:
                    image_filepath = Path(base)/n
                    if not image_filepath.suffix.lower() in SUPPORTED_FORMATS:
                        # Ignore unsupported formats
                        continue
                    caption_filepath = image_filepath.with_suffix('.txt')
                    tags = []
                    if caption_filepath.exists():
                        # Read tags from the caption file if exists
                        with open(caption_filepath, 'rt') as f:
                            tags = [s.strip() for s in re.split(r',|\n|\r', f.read())]
                    cur.execute("INSERT INTO images (path, tags) VALUES (?, ?)", (str(image_filepath), json.dumps(tags)))
            self._select_all_files()
        return self
