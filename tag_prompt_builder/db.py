# tag_prompt_builder/db.py
import sqlite3
from contextlib import contextmanager
from tag_prompt_builder.utils import make_tag_id

class TagDatabase:
    ALLOWED_FIELDS = {
        'display_name', 'starred', 'single_selection',
        'sort_order', 'wiki_url', 'description'
    }

    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with self.conn() as conn:
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
                    alias TEXT NOT NULL,
                    FOREIGN KEY (tag_id) REFERENCES tags(id)
                );
                CREATE TABLE IF NOT EXISTS tag_urls (
                    tag_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    FOREIGN KEY (tag_id) REFERENCES tags(id)
                );
                CREATE INDEX IF NOT EXISTS idx_parent ON tags(parent_id);
                CREATE INDEX IF NOT EXISTS idx_name ON tags(name);
                CREATE INDEX IF NOT EXISTS idx_display ON tags(display_name);
                CREATE INDEX IF NOT EXISTS idx_starred ON tags(starred);
                CREATE INDEX IF NOT EXISTS idx_tag_aliases_tag_id ON tag_aliases(tag_id);
                CREATE INDEX IF NOT EXISTS idx_tag_urls_tag_id ON tag_urls(tag_id);
            """)

    @contextmanager
    def conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---------- 基础查询 ----------
    def get_children(self, parent_id):
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tags WHERE parent_id=? ORDER BY sort_order, name",
                (parent_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_tag_by_id(self, tag_id):
        with self.conn() as conn:
            row = conn.execute("SELECT * FROM tags WHERE id=?", (tag_id,)).fetchone()
            return dict(row) if row else None

    def get_tags_by_ids(self, id_list):
        if not id_list:
            return {}
        placeholders = ','.join(['?' for _ in id_list])
        with self.conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM tags WHERE id IN ({placeholders})",
                id_list
            ).fetchall()
        return {row['id']: dict(row) for row in rows}

    def search_tags(self, query):
        like = f"%{query}%"
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT id, name, display_name, parent_id, is_folder, single_selection, starred, wiki_url, description "
                "FROM tags WHERE (name LIKE ? OR display_name LIKE ?) AND is_folder=0",
                (like, like)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_starred_tags(self):
        with self.conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tags WHERE starred=1 AND is_folder=0"
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- 增删改 ----------
    def add_tag(self, tag_dict):
        with self.conn() as conn:
            conn.execute(
                """INSERT INTO tags (id, name, display_name, is_folder, parent_id, sort_order, single_selection, wiki_url, starred, description)
                   VALUES (:id, :name, :display_name, :is_folder, :parent_id, :sort_order, :single_selection, :wiki_url, :starred, :description)""",
                tag_dict
            )

    def update_tag(self, tag_id, field, value):
        if field not in self.ALLOWED_FIELDS:
            raise ValueError(f"不允许的字段名: {field}")
        with self.conn() as conn:
            conn.execute(f"UPDATE tags SET {field}=? WHERE id=?", (value, tag_id))

    def set_starred(self, tag_id, starred: bool):
        self.update_tag(tag_id, 'starred', 1 if starred else 0)

    def set_display_name(self, tag_id, name: str):
        self.update_tag(tag_id, 'display_name', name)

    def set_single_selection(self, tag_id, flag: bool):
        self.update_tag(tag_id, 'single_selection', 1 if flag else 0)

    def set_wiki_url(self, tag_id, url: str):
        self.update_tag(tag_id, 'wiki_url', url)

    def set_description(self, tag_id, desc: str):
        self.update_tag(tag_id, 'description', desc)

    def set_sort_order(self, tag_id, order: int):
        self.update_tag(tag_id, 'sort_order', order)

    def delete_tag(self, tag_id):
        with self.conn() as conn:
            conn.execute("DELETE FROM tags WHERE id=?", (tag_id,))

    # ---------- 路径工具 ----------
    def get_full_path(self, tag_id):
        path = []
        current = self.get_tag_by_id(tag_id)
        while current and current['parent_id']:
            path.insert(0, current['name'])
            current = self.get_tag_by_id(current['parent_id'])
        return path

    def get_full_id(self, tag_id):
        parts = []
        current = self.get_tag_by_id(tag_id)
        while current:
            parent_id = current['parent_id']
            if parent_id is None:
                break
            siblings = self.get_children(parent_id)
            try:
                idx = next(i for i, s in enumerate(siblings) if s['id'] == tag_id)
            except StopIteration:
                idx = 0
            parts.insert(0, f"{current['name']}#{idx}")
            tag_id = parent_id
            current = self.get_tag_by_id(parent_id)
        return '#root/' + '/'.join(parts) if parts else '#root'

    # ---------- 子树复制 ----------
    def copy_subtree(self, source_id: str, new_parent_id: str, new_name: str = None) -> str:
        source = self.get_tag_by_id(source_id)
        if not source:
            raise ValueError(f"Source tag not found: {source_id}")

        name = new_name or source['name']
        siblings = self.get_children(new_parent_id)
        sort_order = len(siblings)
        new_id = make_tag_id(new_parent_id, name, sort_order)   # 使用统一 ID 函数

        with self.conn() as conn:
            conn.execute("""
                INSERT INTO tags (id, name, display_name, is_folder, parent_id,
                                  sort_order, single_selection, wiki_url, starred, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id,
                name,
                source['display_name'] if source['display_name'] != source['name'] else name,
                source['is_folder'],
                new_parent_id,
                sort_order,
                source['single_selection'],
                source['wiki_url'],
                source['starred'],
                source['description']
            ))

        if source['is_folder']:
            children = self.get_children(source_id)
            for child in children:
                self.copy_subtree(child['id'], new_id)

        return new_id