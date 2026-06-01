# tests/conftest.py
import pytest
from PyQt6.QtWidgets import QApplication
from tag_prompt_builder.managers.tag_manager import TagManager

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def tag_manager():
    """返回一个不加载数据库的空 TagManager"""
    return TagManager(skip_load=True)

@pytest.fixture
def sample_tree(tag_manager):
    """使用 TagManager 的 _build_from_dict 构建测试树"""
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
    return tag_manager.root