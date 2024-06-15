from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Dict, Iterable, List, Set

from tqdm import tqdm
from models.context import Context
from .transaction import Txn

def load_caption(path: Path) -> Iterable[str]:
    with open(path, 'r') as f:
        for tag in re.split(",|\n|\r", f.read()):
            t = tag.strip()
            if len(t) > 0:
                yield t

@dataclass
class FilesListItem:
    path: str
    tags: List[str]

@dataclass
class DiffResult:
    common: Set[str]
    dataset: Dict[str, List[str]]

class Captions:
    context: Context
    def __init__(self, context):
        self.context = context
    def select_all_files(self):
        return self.context.dataset._select_all_files()
    def select_files(self, expr:List[str]):
        paths: Set[str] = []
        conditions: List[re.Pattern] = []
        for e in expr:
            conditions.append(re.compile(e))
        with Txn.begin(self.context.conn) as cur:
            cur.execute("SELECT path FROM images")
            for row in cur:
                for c in conditions:
                    if c.match(row[0]):
                        paths.append(row[0])
                        break
            if len(paths) == 0:
                raise ValueError("No files selected")
            cur.execute("DELETE FROM selected")
            cur.executemany("INSERT INTO selected (path) VALUES (?)", [(x,) for x in paths])
        return len(paths)
    def save(self):
        with Txn.begin(self.context.conn) as cur:
            cur.execute("SELECT i.path, JSON_EXTRACT(i.tags, '$') FROM images as i, selected as s WHERE i.path = s.path")
            count = 0
            for path, tags in cur:
                with open(Path(path).with_suffix(".txt"), "w") as f:
                    f.write(", ".join(json.loads(tags)))
                count += 1
            return count
    def diff(self):
        with Txn.begin(self.context.conn) as cur:
            cur.execute("SELECT COUNT(*) FROM selected")
            if cur.fetchone()[0] < 2:
                raise ValueError("Select at least two files")
            cur.execute("SELECT i.path, JSON_EXTRACT(i.tags, '$') FROM images as i, selected as s WHERE i.path = s.path")
            dataset: Dict[str, List[str]] = {}
            path, tags = cur.fetchone()
            v = json.loads(tags)
            dataset[path] = v
            common :Set[str] = set(v)
            for path, tags in cur:
                v = json.loads(tags)
                dataset[path] = v
                common &= set(v)
            for k, v in dataset.items():
                tag: List[str]= []
                for t in v:
                    if not t in common:
                        tag.append(t)
                dataset[k] = tag
            return DiffResult(common, dataset)
    def list(self, selected:bool):
        with Txn.begin(self.context.conn) as cur:
            query = ''
            if selected:
                query = 'SELECT i.path, i.tags FROM images as i, selected as s ' \
                        'WHERE i.path = s.path '
            else:
                query = 'SELECT i.path, i.tags FROM images as i '
            query += 'ORDER BY i.path ASC'
            cur.execute(query)
            for path, tags in cur:
                yield FilesListItem(path, json.loads(tags))
    def relative(self, root_path: Path, absolute_path) -> str:
        p = root_path.as_posix() + '/'
        if absolute_path.startswith(p):
            absolute_path = absolute_path[len(p):]
        return absolute_path
    def update(self, path: Path, tags: List[str]):
        with Txn.begin(self.context.conn) as cur:
            cur.execute("UPDATE images SET tags = ? WHERE path = ?", (json.dumps(tags), path.as_posix()))