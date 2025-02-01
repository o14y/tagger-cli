from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional
import re

from controllers.captions import Captions
from models.context import Context
from .transaction import Txn

import Levenshtein as levenshtein

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
    def verify(self, items: Iterable[TagsListItem]) -> Iterable[TagsListItem]:
        for i in items:
            text = self.context.lookup(i.tag)
            if text is None:
                yield i
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
    def prune(self, min_length:int=3, inclusion=False, character=False) -> tuple[int, List[str]]:
        c = Captions(self.context)
        target = c.list(selected=True)
        count = 0
        pruned = []
        if inclusion:
            with Txn.begin(self.context.conn) as cur:
                for i in target:
                    res = []
                    for t in i.tags:
                        if len(t) <= min_length:
                            res.append(t)
                            continue
                        is_contained = False
                        for r in i.tags:
                            if t == r:
                                continue
                            if t in r:
                                is_contained = True
                                break
                        if not is_contained:
                            res.append(t)
                        elif t not in pruned:
                            pruned.append(t)
                    c.update(i.path, tags=res)
                    count += 1
        if character:
            with open('assets/character_tags.txt', 'r') as file:
                keywords = [line.strip() for line in file.readlines() if not len(line) == 0 or not line.isspace()]
            with Txn.begin(self.context.conn) as cur:
                for i in target:
                    res = []
                    for t in i.tags:
                        if not any(re.match(keyword, t) for keyword in keywords):
                            res.append(t)
                        elif t not in pruned:
                            pruned.append(t)
                    c.update(i.path, tags=res)
                    count += 1
        return count, 
    def distance(self, threshold:int) -> Iterable[tuple[str, str, int]]:
        """
        タグ間のレーベンシュタイン距離を計算し、指定された閾値以下のものを返却します。

        引数:
            threshold (int): 返却する最大距離

        yield:
            Iterable[Tuple[str, str, int]]: タグとその距離を含むタプル。

        注意:
            この関数は、リスト内の各タグを他のすべてのタグと比較し、レーベンシュタイン距離を計算します。
            距離が閾値以下の場合、タグとその距離が生成されます。
        """
        tags = list(self.list())
        while len(tags) > 0:
            t = tags.pop(0)
            for a in tags:
                d = levenshtein.distance(t.tag, a.tag)
                if d <= threshold:
                    yield (t.tag, a.tag, d)