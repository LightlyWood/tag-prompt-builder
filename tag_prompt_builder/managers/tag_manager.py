# managers/tag_manager.py
import json
import os
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.app_config import TAGS_FILE, PRESETS_DIR, get_default_tags_path
from tag_prompt_builder.managers.random_pool_manager import RandomPoolManager

class TagManager:
    def __init__(self):
        self.root = TagItem("root", is_folder=True)
        self.random_pool_manager = RandomPoolManager()

    def get_exclusion_groups(self, tags):
        groups = {}
        for tag in tags:
            folder = tag.parent
            while folder and not folder.single_selection:
                folder = folder.parent
            if folder and folder.single_selection:
                fid = folder.full_id()
                groups.setdefault(fid, []).append(tag)   # 已修正为 setdefault
        return groups

    def load_default_library(self):
        if os.path.exists(TAGS_FILE):
            with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            default_path = get_default_tags_path()
            with open(default_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        self._build_from_dict(data, self.root)

    def _build_from_dict(self, data, parent):
        if isinstance(data, dict):
            for key, value in data.items():
                folder = TagItem(key, is_folder=True)
                parent.add_child(folder)
                if isinstance(value, dict):
                    folder.single_selection = value.get('single_selection', False)
                    children = value.get('children', {})
                    tags = value.get('tags', [])
                    self._build_from_dict(children, folder)
                    for entry in tags:
                        if isinstance(entry, str):
                            folder.add_child(TagItem(entry, is_folder=False))
                        elif isinstance(entry, dict):
                            folder.add_child(TagItem(
                                entry['value'],
                                is_folder=False,
                                display_name=entry.get('display'),
                                urls=entry.get('urls', []),
                                starred=entry.get('starred', False),
                                wiki_url=entry.get('wiki_url'),
                                aliases=entry.get('aliases', []),
                                description=entry.get('description', '')
                            ))
                elif isinstance(value, list):
                    for entry in value:
                        if isinstance(entry, str):
                            folder.add_child(TagItem(entry, is_folder=False))
                        elif isinstance(entry, dict):
                            folder.add_child(TagItem(
                                entry['value'],
                                is_folder=False,
                                display_name=entry.get('display'),
                                urls=entry.get('urls', []),
                                starred=entry.get('starred', False),
                                wiki_url=entry.get('wiki_url'),
                                aliases=entry.get('aliases', []),
                                description=entry.get('description', '')
                            ))
        elif isinstance(data, list):
            for entry in data:
                if isinstance(entry, str):
                    parent.add_child(TagItem(entry, is_folder=False))
                elif isinstance(entry, dict):
                    parent.add_child(TagItem(
                        entry['value'],
                        is_folder=False,
                        display_name=entry.get('display'),
                        urls=entry.get('urls', []),
                        starred=entry.get('starred', False),
                        wiki_url=entry.get('wiki_url'),
                        aliases=entry.get('aliases', []),
                        description=entry.get('description', '')
                    ))

    def save_library(self):
        data = self._to_dict(self.root)
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _to_dict(self, item):
        if item.is_folder:
            result = {}
            if item.single_selection:
                result['single_selection'] = True
            children = {}
            tags = []
            for child in item.children:
                if child.is_folder:
                    children.update(self._to_dict(child))
                else:
                    tag_obj = {"value": child.name}
                    if child.display_name != child.name:
                        tag_obj["display"] = child.display_name
                    if child.wiki_url:
                        tag_obj["wiki_url"] = child.wiki_url
                    if child.aliases:
                        tag_obj["aliases"] = child.aliases
                    if child.description:
                        tag_obj["description"] = child.description
                    if child.urls:
                        tag_obj["urls"] = child.urls
                    if child.starred:
                        tag_obj["starred"] = True
                    tags.append(tag_obj if len(tag_obj) > 1 else child.name)
            if children:
                result['children'] = children
            if tags:
                result['tags'] = tags
            # ---------- 修正根节点返回 ----------
            if item.parent is None:   # 根节点
                return children        # 直接返回子文件夹字典，符合原始JSON格式
            else:
                return {item.name: result}
        else:
            # 叶子节点
            if item.display_name != item.name or item.wiki_url or item.aliases or item.description or item.urls or item.starred:
                obj = {"value": item.name}
                if item.display_name != item.name:
                    obj["display"] = item.display_name
                if item.wiki_url:
                    obj["wiki_url"] = item.wiki_url
                if item.aliases:
                    obj["aliases"] = item.aliases
                if item.description:
                    obj["description"] = item.description
                if item.urls:
                    obj["urls"] = item.urls
                if item.starred:
                    obj["starred"] = True
                return obj
            return item.name

    def find_item_by_full_id(self, full_id: str) -> TagItem:
        if not full_id or not full_id.startswith('#root/'):
            return None
        parts = full_id[len('#root/'):].split('/')
        current = self.root
        for part in parts:
            if '#' in part:
                name = part[:part.rindex('#')]
            else:
                name = part
            found = None
            for child in current.children:
                if child.name == name:
                    found = child
                    break
            if not found:
                return None
            current = found
        return current if not current.is_folder else None

    # ---------- 预设管理 ----------
    def save_folder_preset(self, preset_name, selected_items, sort_structure=None):
        preset = {
            'type': 'folder_preset',
            'selected': [item.full_id() for item in selected_items],
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
        """列出所有预设（包括文件夹预设和词组预设）"""
        presets = []
        if not os.path.exists(PRESETS_DIR):
            return presets
        for fname in os.listdir(PRESETS_DIR):
            if fname.endswith('.json'):
                presets.append(fname[:-5])
        return presets

    def delete_preset(self, preset_name: str):
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        if os.path.exists(path):
            os.remove(path)

    def save_tag_preset(self, preset_name, tag_ids):
        """保存简单的标签 ID 列表为词组预设"""
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