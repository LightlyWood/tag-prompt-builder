# tag_prompt_builder/resources/schema.sql
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
    description TEXT,
    FOREIGN KEY (parent_id) REFERENCES tags(id)
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