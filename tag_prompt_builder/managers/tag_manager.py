# tag_prompt_builder/managers/tag_manager.py
import json
import os
import shutil
from collections import defaultdict
from tag_prompt_builder.app_config import USER_DATA_DIR, PRESETS_DIR
from tag_prompt_builder.db import TagDatabase
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.managers.random_pool_manager import RandomPoolManager
from tag_prompt_builder.utils import make_tag_id


class TagManager:
    def __init__(self, skip_load=False):
        """
        skip_load: 为 True 时不访问数据库，仅初始化空缓存（用于测试）
        """
        if not skip_load:
            db_path = os.path.join(USER_DATA_DIR, 'tags.db')
            if not os.path.exists(db_path):
                self._copy_default_db(db_path)
            self.db = TagDatabase(db_path)
            self._load_cache()
        else:
            self.db = None
            self._items = {}
            self._children_ids = defaultdict(list)
        self.random_pool_manager = RandomPoolManager()

    # ---------- 缓存 ----------
    def _load_cache(self):
        self._items = {}
        self._children_ids = defaultdict(list)
        with self.db.conn() as conn:
            rows = conn.execute("SELECT * FROM tags ORDER BY sort_order, name").fetchall()
        for row in rows:
            item = TagItem(dict(row))
            self._items[item.id] = item
            pid = item.parent_id or '#root'
            self._children_ids[pid].append(item.id)
        # 建立树结构：为每个 item 设置 parent 和 children
        for item in self._items.values():
            if item.parent_id and item.parent_id in self._items:
                parent = self._items[item.parent_id]
                item.parent = parent
                parent.children.append(item)

    def _reload_cache(self):
        self._items.clear()
        self._children_ids.clear()
        if self.db:
            self._load_cache()

    # ---------- 数据库初始化 ----------
    def _copy_default_db(self, target_path):
        from tag_prompt_builder.app_config import get_resource_path
        resource_db = get_resource_path('tags.db')
        if not os.path.exists(resource_db):
            raise FileNotFoundError(
                f"默认标签数据库未找到：{resource_db}\n"
                "请将预构建的 tags.db 放置于 tag_prompt_builder/resources/ 目录下。"
            )
        shutil.copy2(resource_db, target_path)

    # 测试辅助方法：直接从字典构建内存树（不访问数据库）
    def _build_from_dict(self, data, parent_id):
        sort = 0
        for key, value in data.items():
            folder_id = make_tag_id(parent_id, key, sort)
            folder_item = TagItem({
                'id': folder_id,
                'name': key,
                'display_name': key,
                'is_folder': 1,
                'parent_id': parent_id,
                'sort_order': sort,
                'single_selection': value.get('single_selection', False) if isinstance(value, dict) else 0,
                'wiki_url': '',
                'starred': 0,
                'description': ''
            })
            self._items[folder_id] = folder_item
            self._children_ids[parent_id].append(folder_id)
            sort += 1
            if isinstance(value, dict):
                children = value.get('children', {})
                tags = value.get('tags', [])
                self._build_from_dict(children, folder_id)
                for i, tag_entry in enumerate(tags):
                    if isinstance(tag_entry, str):
                        tag_id = make_tag_id(folder_id, tag_entry, len(self._children_ids[folder_id]))
                        tag_item = TagItem({
                            'id': tag_id,
                            'name': tag_entry,
                            'display_name': tag_entry,
                            'is_folder': 0,
                            'parent_id': folder_id,
                            'sort_order': i,
                            'single_selection': 0,
                            'wiki_url': '',
                            'starred': 0,
                            'description': ''
                        })
                        self._items[tag_id] = tag_item
                        self._children_ids[folder_id].append(tag_id)
                    elif isinstance(tag_entry, dict):
                        tag_name = tag_entry['value']
                        display = tag_entry.get('display', tag_name)
                        tag_id = make_tag_id(folder_id, tag_name, len(self._children_ids[folder_id]))
                        tag_item = TagItem({
                            'id': tag_id,
                            'name': tag_name,
                            'display_name': display,
                            'is_folder': 0,
                            'parent_id': folder_id,
                            'sort_order': i,
                            'single_selection': 0,
                            'wiki_url': tag_entry.get('wiki_url', ''),
                            'starred': tag_entry.get('starred', 0),
                            'description': tag_entry.get('description', '')
                        })
                        self._items[tag_id] = tag_item
                        self._children_ids[folder_id].append(tag_id)
        # 建立树结构
        for item in self._items.values():
            if item.parent_id and item.parent_id in self._items:
                item.parent = self._items[item.parent_id]
                item.parent.children.append(item)

    @property
    def root(self):
        """返回虚拟根节点（测试用）"""
        root = TagItem({'id': '#root', 'name': 'root', 'display_name': 'root', 'is_folder': 1, 'parent_id': None})
        root.children = [self._items[cid] for cid in self._children_ids.get('#root', [])]
        return root

    # ---------- 查询接口 ----------
    def get_root_children(self):
        return [self._items[cid] for cid in self._children_ids.get('#root', [])]

    def get_children(self, parent_id):
        return [self._items[cid] for cid in self._children_ids.get(parent_id, [])]

    def find_item_by_full_id(self, full_id):
        return self._items.get(full_id)

    def find_item_by_id(self, tag_id):
        return self.find_item_by_full_id(tag_id)

    def search(self, query):
        query = query.lower()
        results = []
        for item in self._items.values():
            if not item.is_folder and (query in item.name.lower() or query in item.display_name.lower()):
                results.append(item)
        return results

    def get_starred(self):
        return [item for item in self._items.values() if item.starred and not item.is_folder]

    def toggle_star(self, tag_id, starred):
        if self.db:
            self.db.set_starred(tag_id, starred)
        if tag_id in self._items:
            self._items[tag_id].starred = starred

    # ---------- 增删改 ----------
    def add_new_tag(self, parent_id, name, is_folder=False, display_name=None, **kwargs):
        siblings = self._children_ids.get(parent_id, [])
        new_sort = len(siblings)
        new_id = make_tag_id(parent_id, name, new_sort)
        tag_dict = {
            'id': new_id,
            'name': name,
            'display_name': display_name or name,
            'is_folder': 1 if is_folder else 0,
            'parent_id': parent_id,
            'sort_order': new_sort,
            'single_selection': 0,
            'wiki_url': '',
            'starred': 0,
            'description': ''
        }
        if self.db:
            self.db.add_tag(tag_dict)
        new_item = TagItem(tag_dict)
        self._items[new_id] = new_item
        self._children_ids[parent_id].append(new_id)
        # 设置父子关系
        if parent_id in self._items:
            new_item.parent = self._items[parent_id]
            self._items[parent_id].children.append(new_item)
        return new_item

    def delete_tag(self, tag_id):
        def _recursive_delete(tid):
            for child_id in self._children_ids.get(tid, []):
                _recursive_delete(child_id)
            # 先获取父节点信息
            item = self._items.get(tid)
            parent_id = item.parent_id if item else None
            if self.db:
                self.db.delete_tag(tid)
            if tid in self._items:
                del self._items[tid]
            # 从父节点的子列表中移除
            if parent_id and parent_id in self._children_ids and tid in self._children_ids[parent_id]:
                self._children_ids[parent_id].remove(tid)
                # 同时从父节点的 children 列表中移除
                if parent_id in self._items:
                    parent = self._items[parent_id]
                    parent.children = [c for c in parent.children if c.id != tid]
            elif tid in self._children_ids.get('#root', []):
                self._children_ids['#root'].remove(tid)
        _recursive_delete(tag_id)

    def copy_subtree(self, source_id, new_parent_id=None, new_name=None):
        if not self.db:
            raise RuntimeError("Database not available")
        source = self.db.get_tag_by_id(source_id)
        if not source:
            raise ValueError("源标签不存在")
        if new_parent_id is None:
            new_parent_id = source['parent_id'] or '#root'
        if new_name is None:
            new_name = f"{source['name']}_copy"
        new_id = self.db.copy_subtree(source_id, new_parent_id, new_name)
        self._reload_cache()
        return new_id

    def save_library(self):
        pass

    def load_default_library(self):
        pass

    # ---------- 预设管理 ----------
    def save_folder_preset(self, preset_name, selected_ids, sort_structure=None):
        preset = {
            'type': 'folder_preset',
            'selected': selected_ids,
            'sort_structure': sort_structure
        }
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)

    def load_folder_preset(self, preset_name):
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def list_tag_presets(self):
        presets = []
        if os.path.exists(PRESETS_DIR):
            for fname in os.listdir(PRESETS_DIR):
                if fname.endswith('.json'):
                    presets.append(fname[:-5])
        return presets

    def delete_preset(self, preset_name):
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        if os.path.exists(path):
            os.remove(path)

    def save_tag_preset(self, preset_name, tag_ids):
        preset = {'type': 'tag_preset', 'tag_ids': tag_ids}
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)

    def load_tag_preset(self, preset_name):
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('tag_ids', []) if data.get('type') == 'tag_preset' else []
        return []

    def find_tag_exact(self, name_or_display):
        for item in self._items.values():
            if not item.is_folder and (item.name.lower() == name_or_display.lower() or item.display_name.lower() == name_or_display.lower()):
                return item
        return None