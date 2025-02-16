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
    path: Path
    tags: List[str]

@dataclass
class DiffResult:
    common: Set[str]
    dataset: Dict[str, List[str]]

class Captions:
    context: Context
    def __init__(self, context) -> None:
        self.context = context
    def select_all_files(self) -> int:
        return self.context.dataset._select_all_files()
    def select_files(self, expr:List[str]) -> int:
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
    def save(self) -> int:
        with Txn.begin(self.context.conn) as cur:
            cur.execute("SELECT i.path, JSON_EXTRACT(i.tags, '$') FROM images as i, selected as s WHERE i.path = s.path")
            count = 0
            for path, tags in cur:
                with open(Path(path).with_suffix(".txt"), "w") as f:
                    f.write(", ".join(json.loads(tags)))
                count += 1
            return count
    def diff(self) -> DiffResult:
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
    def list(self, selected:bool, filter:str=None) -> Iterable[FilesListItem]:
        with Txn.begin(self.context.conn) as cur:
            query = ""
            if selected:
                query = "(" \
                        "SELECT DISTINCT i.path as p FROM images as i, selected as s "
                query += ", JSON_EACH(i.tags) as e " if filter is not None else " "
                query += "WHERE i.path = s.path "
                query += "AND e.VALUE LIKE ? " if filter is not None else " "
                query += ") "
            else:
                query = "(" \
                        "SELECT DISTINCT i.path as p FROM images as i "
                query += ", JSON_EACH(i.tags) as e WHERE e.VALUE LIKE ? " if filter is not None else " "
                query += ") "
            query = "SELECT p, i.tags FROM " + query + " as v, images as i WHERE v.p = i.path " \
                    "ORDER BY p ASC "
            if filter:
                cur.execute(query, ("%" if filter is None else "%"+filter+"%", ))
            else:
                cur.execute(query)
            for path, tags in cur:
                yield FilesListItem(Path(path), json.loads(tags))
    def relative(self, root_path: Path, absolute_path: Path) -> Path:
        root_as_posix = root_path.as_posix() + '/'
        absolute_as_posix = absolute_path.as_posix()
        if absolute_as_posix.startswith(root_as_posix):
            absolute_path = Path(absolute_as_posix[len(root_as_posix):])
        return absolute_path
    def update(self, path: Path, tags: List[str]) -> None:
        with Txn.begin(self.context.conn) as cur:
            cur.execute("UPDATE images SET tags = ? WHERE path = ?", (json.dumps(tags), path.as_posix()))
    def append(self, path: Path, tags: List[str]) -> None:
        with Txn.begin(self.context.conn) as cur:
            cur.execute("SELECT tags FROM images WHERE path = ?", (path.as_posix(), ))
            old_tags = json.loads(cur.fetchone()[0])
            new_tags = list(set(old_tags) | set(tags))
            cur.execute("UPDATE images SET tags = ? WHERE path = ?", (json.dumps(new_tags), path.as_posix()))
