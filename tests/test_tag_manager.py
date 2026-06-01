# tests/test_tag_manager.py
import pytest
import json
import os
from tag_prompt_builder.managers.tag_manager import TagManager

class TestTagManager:
    def test_load_from_dict(self, tag_manager):
        data = {
            "Characters": {
                "children": {
                    "Hair": {
                        "single_selection": True,
                        "tags": ["blonde", "silver"]
                    }
                }
            }
        }
        tag_manager._build_from_dict(data, '#root')
        root = tag_manager.root
        chars = root.children[0]
        assert chars.name == "Characters"
        hair = chars.children[0]
        assert hair.single_selection is True
        assert len(hair.children) == 2
        assert hair.children[0].name == "blonde"

    def test_find_item_by_full_id(self, tag_manager):
        data = {
            "Characters": {
                "tags": [{"display": "金发", "value": "blonde"}]
            }
        }
        tag_manager._build_from_dict(data, '#root')
        item = tag_manager.find_item_by_full_id("#root/Characters#0/blonde#0")
        assert item is not None
        assert item.name == "blonde"
        assert item.display_name == "金发"

    def test_save_and_load_preset(self, tmp_path):
        import tag_prompt_builder.app_config as app_config
        original_dir = app_config.PRESETS_DIR
        app_config.PRESETS_DIR = str(tmp_path)
        # 使用 skip_load 避免数据库操作
        mgr = TagManager(skip_load=True)
        try:
            tag_ids = ["#root/a/b#0", "#root/c#0"]
            mgr.save_tag_preset("test", tag_ids)
            loaded = mgr.load_tag_preset("test")
            assert loaded == tag_ids
        finally:
            app_config.PRESETS_DIR = original_dir