import json
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional
from .transaction import Txn

@dataclass
class TagsListItem:
    tag: str
    count: int

class Tags:
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
            tail: bool=False,
            progress_wrapper: Optional[Callable] = None, 
            progress_post: Optional[Callable] = None):
        target = self.context.get_paths()
        if progress_wrapper:
            target = progress_wrapper(target)
        count = 0
        with Txn.begin(self.context.conn) as cur:
            for p in target:
                existing = list(self.context.get_tags(p))
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
                cur.execute("UPDATE images SET tags = ? WHERE path = ?", (json.dumps(existing), str(p)))
                count += 1
        if progress_post:
            progress_post()
        return count
    def remove(self, 
               tags: List[str], 
               progress_wrapper: Optional[Callable] = None, 
               progress_post: Optional[Callable] = None):
        target = self.context.get_paths()
        if progress_wrapper:
            target = progress_wrapper(target)
        count = 0
        with Txn.begin(self.context.conn) as cur:
            for p in target:
                existing = list(self.context.get_tags(p))
                removing: List[str] = []
                for t in tags:
                    if t in existing:
                        removing.append(t)
                if len(removing) == 0:
                    continue
                for t in removing:
                    existing.remove(t)
                cur.execute("UPDATE image SET tags = ? WHERE path = ?", (json.dumps(existing), str(p)))
                count += 1
        if progress_post:
            progress_post()
        return count