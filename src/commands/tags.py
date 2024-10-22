from typing import *
from dataclasses import dataclass
from simple_parsing import field, subparsers
from tqdm import tqdm
from models.context import Context
from controllers.tags import Tags as TagsController
from controllers.captions import Captions
from controllers.infer import infer_tags


@dataclass
class AddTags:
    tags :List[str] = field(positional=True, hint='Tags to add')
    tail :Optional[bool] = field(default=False, hint='Add the tags to the end of the list')
    def run(self, context :Context):
        c = TagsController(context)
        count = c.add(self.tags, tail=self.tail)
        print(f'{count} file{'s' if count>1 else ''} updated')

@dataclass
class RemoveTags:
    tags :List[str] = field(positional=True, hint='Tags to remove')
    def run(self, context :Context):
        c = TagsController(context)
        count = c.remove(self.tags)
        print(f'{count} file{'s' if count>1 else ''} updated')

@dataclass
class ListTags:
    threshold :Optional[int] = field(default=None, hint='Minimum count to show the caption')
    head :Optional[int] = field(default=None, hint='Show only the top N tags')
    skip :Optional[int] = field(default=None, hint='Skip the first N tags')
    filter :Optional[str] = field(default=None, hint='Filter the tags')
    def run(self, context :Context):
        c = TagsController(context)
        kv = {k:v for k,v in self.__dict__.items() if v is not None}
        index = c.list(**kv)
        for i in index:
            text = context.dictionary[i.tag]
            if text is None:
                text = context.dictionary[i.tag.replace(' ', '_')]
            print(f'{i.count:4d} {i.tag}, {text}')

@dataclass
class InferTags:
    overwrite: bool = field(default=False, help='Overwrite existing tags')
    model: str = field(default='vit', help='Model to use for inference. vit, swinv2 or convnext')
    def run(self, context :Context):
        c = Captions(context)
        files = [x.path for x in c.list(selected=True) if self.overwrite or x.tags is None or len(x.tags) == 0]
        if len(files) == 0:
            return
        progress = tqdm(infer_tags(files, model=self.model), total=len(files))
        progress.colour = 'green'
        for r in progress:
            c.update(r.path, r.tags)

@dataclass
class ReplaceTags:
    old :str = field(positional=True, hint='a part of tag to be replaced')
    new :str = field(positional=True, hint='string to replace with', default='')
    def run(self, context :Context):
        c = TagsController(context)
        count = c.replace(self.old, self.new)
        print(f'{count} file{"s" if count>1 else ""} updated')

@dataclass
class Tags(ListTags):
    command :Any = subparsers(default=None,
                              subcommands={'add': AddTags,
                                           'remove': RemoveTags,
                                           'list': ListTags,
                                           'auto': InferTags, 
                                           'replace': ReplaceTags,
                                           })
    def run(self, context :Context):
        if self.command:
            return self.command.run(context)
        return super().run(context)
