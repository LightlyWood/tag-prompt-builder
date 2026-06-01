# tag_prompt_builder/app_config.py
"""应用全局配置，集中管理路径、常量"""
import os
import sys
import importlib.resources

# ---------- 资源包内路径 ----------
_RESOURCE_PACKAGE = 'tag_prompt_builder.resources'

def get_resource_path(filename: str) -> str:
    return str(importlib.resources.files(_RESOURCE_PACKAGE).joinpath(filename))

def get_default_tags_path() -> str:
    return get_resource_path('default_tags.json')

# ---------- 用户数据目录 ----------
def get_user_data_dir() -> str:
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(base, 'tag_prompt_builder')
    else:
        base = os.environ.get('XDG_DATA_HOME', os.path.join(os.path.expanduser('~'), '.local', 'share'))
        data_dir = os.path.join(base, 'tag_prompt_builder')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

USER_DATA_DIR = get_user_data_dir()
PRESETS_DIR = os.path.join(USER_DATA_DIR, 'presets')
TAGS_FILE = os.path.join(USER_DATA_DIR, 'tags.json')
RECENT_FILE = os.path.join(USER_DATA_DIR, 'recent.json')
STYLE_BASES_FILE = os.path.join(USER_DATA_DIR, 'style_bases.json')

os.makedirs(PRESETS_DIR, exist_ok=True)

# ---------- 可扩展配置 ----------
LANGUAGE = 'zh'
THEME = 'light'

# 添加此行以兼容 random_pool_manager.py 的导入
DATA_DIR = USER_DATA_DIR