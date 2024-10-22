import json
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from controllers.captions import Captions
from models.context import Context
from .transaction import Txn

@dataclass
class TagsListItem:
    tag: str
    count: int

class Tags:
    context: Context
    def __init__(self, context):
        self.context = context
    def list(self, filter:str = None, skip:int = 0, head:int = -1, threshold:int = 1) -> Iterable[TagsListItem]:
        with Txn.begin(self.context.conn) as cur:
            query = \
                "SELECT JSON_EACH.VALUE, COUNT(*) as count " \
                "FROM images as i, JSON_EACH(i.tags), selected as s " \
                "WHERE i.path = s.path " \
                "GROUP BY JSON_EACH.VALUE "
            query += f"HAVING count >= {threshold} "
            if filter:
                query += f"AND JSON_EACH.VALUE LIKE '%{filter}%' "
            query += f"ORDER BY count DESC LIMIT {head} OFFSET {skip} "
            cur.execute(query)
            for tag, count in cur:
                yield TagsListItem(tag, count)
    def add(self, 
            tags: List[str], 
            tail: bool=False):
        c = Captions(self.context)
        target = c.list(selected=True)
        count = 0
        with Txn.begin(self.context.conn) as cur:
            for i in target:
                existing = i.tags
                adding: List[str] = []
                for tag in tags:
                    if tag not in existing:
                        adding.append(tag)
                if len(adding) == 0:
                    continue
                if tail:
                    existing += tags
                else:
                    existing = tags + existing
                c.update(i.path, tags=existing)
                count += 1
        return count
    def remove(self, 
               tags: List[str], 
               progress_wrapper: Optional[Callable] = None, 
               progress_post: Optional[Callable] = None):
        c = Captions(self.context)
        target = c.list(selected=True)
        if progress_wrapper:
            target = progress_wrapper(target)
        count = 0
        with Txn.begin(self.context.conn) as cur:
            for i in target:
                existing = i.tags
                removing: List[str] = []
                for t in tags:
                    if t in existing:
                        removing.append(t)
                if len(removing) == 0:
                    continue
                for t in removing:
                    existing.remove(t)
                c.update(i.path, tags=existing)
                count += 1
        if progress_post:
            progress_post()
        return count
    def replace(self, old: str, new: str):
        c = Captions(self.context)
        target = c.list(selected=True, filter=old)
        count = 0
        with Txn.begin(self.context.conn) as cur:
            for i in target:
                res = []
                for t in i.tags:
                    t = t.replace(old, new).strip(' ')
                    if len(t) != 0 and t not in res:
                        res.append(t)
                c.update(i.path, tags=res)
                count += 1
        return count
