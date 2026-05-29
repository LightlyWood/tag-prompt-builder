# app_config.py
"""应用全局配置，集中管理路径、常量，方便未来扩展（如多语言、主题切换）"""
import os
import sys

# 基础路径：exe 运行时指向所在目录，开发时指向脚本目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
PRESETS_DIR = os.path.join(BASE_DIR, 'presets')
TAGS_FILE = os.path.join(DATA_DIR, 'default_tags.json')
STYLE_BASES_FILE = os.path.join(DATA_DIR, 'style_bases.json')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PRESETS_DIR, exist_ok=True)

# 可扩展：语言、主题配置等
LANGUAGE = 'zh'  # 预留
THEME = 'light'  # 预留