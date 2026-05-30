import pytest
import json
import os
from tag_prompt_builder.managers.tag_manager import TagManager

class TestTagManager:
    def test_load_from_dict(self):
        mgr = TagManager()
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
        mgr._build_from_dict(data, mgr.root)
        chars = mgr.root.children[0]
        assert chars.name == "Characters"
        hair = chars.children[0]
        assert hair.single_selection is True
        assert len(hair.children) == 2
        assert hair.children[0].name == "blonde"

    def test_find_item_by_full_id(self):
        mgr = TagManager()
        # 手动构建简单树
        data = {
            "Characters": {
                "tags": [{"display": "金发", "value": "blonde"}]
            }
        }
        mgr._build_from_dict(data, mgr.root)
        item = mgr.find_item_by_full_id("#root/Characters/blonde#0")
        assert item is not None
        assert item.name == "blonde"
        assert item.display_name == "金发"

    def test_save_and_load_preset(self, tmp_path):
        """测试词组预设的保存与加载"""
        mgr = TagManager()
        # 临时修改 PRESETS_DIR
        import tag_prompt_builder.app_config as app_config
        original_dir = app_config.PRESETS_DIR
        app_config.PRESETS_DIR = str(tmp_path)
        try:
            tag_ids = ["#root/a/b#0", "#root/c#0"]
            mgr.save_tag_preset("test", tag_ids)
            loaded = mgr.load_tag_preset("test")
            assert loaded == tag_ids
        finally:
            app_config.PRESETS_DIR = original_dir