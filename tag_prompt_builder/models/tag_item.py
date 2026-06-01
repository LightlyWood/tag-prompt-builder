# tag_prompt_builder/models/tag_item.py
class TagItem:
    __slots__ = ('id', 'name', 'display_name', 'is_folder', 'parent_id',
                 'single_selection', 'wiki_url', 'aliases', 'urls',
                 'starred', 'description', 'checked', 'locked',
                 '_db', 'children', 'parent')

    def __init__(self, row_dict=None, **kwargs):
        if row_dict is None:
            row_dict = {}
        # 允许关键字参数覆盖字典值
        data = {**row_dict, **kwargs}
        self.id = data.get('id', '')
        self.name = data.get('name', '')
        self.display_name = data.get('display_name') or self.name
        self.is_folder = bool(data.get('is_folder', False))
        self.parent_id = data.get('parent_id')
        self.single_selection = bool(data.get('single_selection', False))
        self.wiki_url = data.get('wiki_url', '')
        self.starred = bool(data.get('starred', False))
        self.description = data.get('description', '')
        self.aliases = []
        self.urls = []
        self.checked = False
        self.locked = False
        self.children = []      # 子节点列表
        self.parent = None      # 父节点引用

    def add_child(self, child: 'TagItem'):
        child.parent = self
        self.children.append(child)

    def full_id(self):
        return self.id

    def path(self):
        return '/'.join(self.id.split('/')[1:])