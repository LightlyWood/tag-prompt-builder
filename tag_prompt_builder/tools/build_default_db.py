#!/usr/bin/env python3
"""将 default_tags.json 转为内置 SQLite 数据库 resources/tags.db"""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tag_prompt_builder.db import TagDatabase
from tag_prompt_builder.managers.tag_manager import make_tag_id

def insert_node(db, parent_id, key, value, sort):
    """递归插入节点，返回下一个 sort_order 值"""
    node_id = make_tag_id(parent_id, key, sort)
    is_folder = isinstance(value, dict)

    db.add_tag({
        'id': node_id,
        'name': key,
        'display_name': key,
        'is_folder': 1 if is_folder else 0,
        'parent_id': parent_id,
        'sort_order': sort,
        'single_selection': value.get('single_selection', False) if isinstance(value, dict) else 0,
        'wiki_url': '',
        'starred': 0,
        'description': ''
    })
    next_sort = sort + 1

    if isinstance(value, dict):
        children = value.get('children', {})
        for child_key, child_val in children.items():
            next_sort = insert_node(db, node_id, child_key, child_val, next_sort)

        tags = value.get('tags', [])
        for tag_entry in tags:
            if isinstance(tag_entry, str):
                tag_name = tag_entry
                display = tag_name
                extra = {}
            elif isinstance(tag_entry, dict):
                tag_name = tag_entry['value']
                display = tag_entry.get('display', tag_name)
                extra = {
                    'wiki_url': tag_entry.get('wiki_url', ''),
                    'starred': tag_entry.get('starred', 0),
                    'description': tag_entry.get('description', '')
                }
            else:
                continue

            tag_id = make_tag_id(node_id, tag_name, next_sort)
            db.add_tag({
                'id': tag_id,
                'name': tag_name,
                'display_name': display,
                'is_folder': 0,
                'parent_id': node_id,
                'sort_order': next_sort,
                'single_selection': 0,
                'wiki_url': extra.get('wiki_url', ''),
                'starred': extra.get('starred', 0),
                'description': extra.get('description', '')
            })
            next_sort += 1

    return next_sort

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(project_root, 'tag_prompt_builder', 'resources', 'default_tags.json')
    db_path = os.path.join(project_root, 'tag_prompt_builder', 'resources', 'tags.db')

    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"正在从 {json_path} 构建数据库...")
    db = TagDatabase(db_path)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sort = 0
    for key, value in data.items():
        sort = insert_node(db, '#root', key, value, sort)

    root_children = db.get_children('#root')
    print(f"成功！一级标签组数量: {len(root_children)}")
    for child in root_children:
        print(f"  - {child['display_name']}")

if __name__ == '__main__':
    main()