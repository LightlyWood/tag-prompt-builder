import json
import os
from models.tag_item import TagItem
from app_config import TAGS_FILE, PRESETS_DIR

class TagManager:
    def __init__(self):
        self.root = TagItem("root", is_folder=True)

    def load_default_library(self):
        if os.path.exists(TAGS_FILE):
            with open(TAGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._build_from_dict(data, self.root)
        else:
            self._create_demo()
            self.save_library()

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
                                urls=entry.get('urls', [])
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
                                urls=entry.get('urls', [])
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
                        urls=entry.get('urls', [])
                    ))

    def _create_demo(self):
        demo = {
            "#基础人物标签": [
                {"display": "一个女孩", "value": "1girl"},
                {"display": "单人", "value": "solo"}
            ],
            "#角色锚定": {
                "children": {
                    "发色": {
                        "single_selection": True,
                        "tags": [
                            {"display": "金发", "value": "blonde hair",
                             "urls": ["https://danbooru.donmai.us/wiki_pages/blonde_hair"]},
                            {"display": "银发", "value": "silver hair"}
                        ]
                    }
                }
            }
        }
        self._build_from_dict(demo, self.root)

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
                    if child.urls:
                        tag_obj["urls"] = child.urls
                    tags.append(tag_obj if len(tag_obj) > 1 else child.name)
            if children:
                result['children'] = children
            if tags:
                result['tags'] = tags
            return {item.name: result} if item.parent is self.root else result
        else:
            if item.display_name != item.name or item.urls:
                obj = {"value": item.name}
                if item.display_name != item.name:
                    obj["display"] = item.display_name
                if item.urls:
                    obj["urls"] = item.urls
                return obj
            return item.name

    # ---------- 预设部分（不变，略） ----------
    def save_folder_preset(self, preset_name, selected_items, sort_order):
        preset = {
            'type': 'folder_preset',
            'selected': [item.full_id() for item in selected_items],
            'sort_order': sort_order
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

    def save_tag_preset(self, preset_name, tag_paths):
        preset = {'type': 'tag_preset', 'tags': tag_paths}
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(preset, f, ensure_ascii=False, indent=2)

    def load_tag_preset(self, preset_name):
        path = os.path.join(PRESETS_DIR, f'{preset_name}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tags', [])
        return []