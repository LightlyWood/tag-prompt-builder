import json
import sqlite3
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tag_prompt_builder.db import TagDatabase
from tag_prompt_builder.managers.tag_manager import make_tag_id

def create_db():
    JSON_PATH = os.path.join('tag_prompt_builder', 'resources', 'default_tags.json')
    DB_PATH = os.path.join('tag_prompt_builder', 'resources', 'tags.db')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            display_name TEXT,
            is_folder INTEGER DEFAULT 0,
            parent_id TEXT,
            sort_order INTEGER DEFAULT 0,
            single_selection INTEGER DEFAULT 0,
            wiki_url TEXT,
            starred INTEGER DEFAULT 0,
            description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS tag_aliases (
            tag_id TEXT NOT NULL,
            alias TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tag_urls (
            tag_id TEXT NOT NULL,
            url TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_parent ON tags(parent_id);
        CREATE INDEX IF NOT EXISTS idx_name ON tags(name);
        CREATE INDEX IF NOT EXISTS idx_display ON tags(display_name);
    """)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def insert_node(parent_id, name, is_folder=True, sort_order=0, single_selection=False,
                     wiki_url='', starred=0, description='', display_name=None):
        if display_name is None:
            display_name = name
        tag_id = make_tag_id(parent_id, name, sort_order)
        existing = conn.execute("SELECT id FROM tags WHERE id=?", (tag_id,)).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO tags (id, name, display_name, is_folder, parent_id, sort_order, single_selection, wiki_url, starred, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tag_id, name, display_name, int(is_folder), parent_id, sort_order, int(single_selection),
                 wiki_url, starred, description)
            )
        return tag_id

    def parse_dict(d, parent_id, sort_start=0):
        sort = sort_start
        for key, value in d.items():
            single = False
            if isinstance(value, dict):
                single = value.get('single_selection', False)
            tag_id = insert_node(parent_id, key, is_folder=True, sort_order=sort, single_selection=single)
            sort += 1
            if isinstance(value, dict):
                if 'children' in value:
                    parse_dict(value['children'], tag_id)
                if 'tags' in value:
                    for i, tag_entry in enumerate(value['tags']):
                        if isinstance(tag_entry, str):
                            insert_node(tag_id, tag_entry, is_folder=False, sort_order=i, display_name=tag_entry)
                        elif isinstance(tag_entry, dict):
                            tag_name = tag_entry['value']
                            display = tag_entry.get('display', tag_name)
                            wiki = tag_entry.get('wiki_url', '')
                            desc = tag_entry.get('description', '')
                            starred = 1 if tag_entry.get('starred') else 0
                            insert_node(tag_id, tag_name, is_folder=False, sort_order=i,
                                        display_name=display, wiki_url=wiki, description=desc, starred=starred)
            elif isinstance(value, list):
                for i, tag_entry in enumerate(value):
                    if isinstance(tag_entry, str):
                        insert_node(tag_id, tag_entry, is_folder=False, sort_order=i, display_name=tag_entry)
                    elif isinstance(tag_entry, dict):
                        tag_name = tag_entry['value']
                        display = tag_entry.get('display', tag_name)
                        insert_node(tag_id, tag_name, is_folder=False, sort_order=i, display_name=display)
            elif isinstance(value, str):
                insert_node(tag_id, value, is_folder=False, sort_order=0, display_name=value)

    parse_dict(data, '#root')
    conn.commit()
    conn.close()
    print(f"数据库已生成: {DB_PATH}")

if __name__ == '__main__':
    create_db()