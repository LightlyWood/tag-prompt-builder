import uuid
from typing import Optional, List

class TagItem:
    def __init__(self, name: str, is_folder: bool = False,
                 parent: Optional['TagItem'] = None,
                 display_name: Optional[str] = None,
                 urls: Optional[List[str]] = None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name                           # 英文真实值
        self.display_name = display_name if display_name is not None else name
        self.is_folder = is_folder
        self.parent = parent
        self.children: List['TagItem'] = []
        self.checked = False
        self.locked = False
        self.single_selection = False
        self.urls = urls if urls is not None else []   # 新增：参考网址列表

    def add_child(self, child: 'TagItem'):
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'TagItem'):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def path(self) -> str:
        if self.parent is None:
            return ''
        return f'{self.parent.path()}/{self.name}'

    def full_id(self) -> str:
        if self.parent is None:
            return '#root'
        siblings = self.parent.children
        idx = siblings.index(self) if self in siblings else -1
        return f'{self.parent.full_id()}/{self.name}#{idx}'