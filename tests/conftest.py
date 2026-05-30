# tests/conftest.py
import pytest
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.managers.tag_manager import TagManager
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def root_item():
    """根节点"""
    return TagItem("root", is_folder=True)

@pytest.fixture
def tag_manager():
    """一个空的 TagManager 实例（未加载库）"""
    return TagManager()

@pytest.fixture
def sample_tree():
    """构建一个简单的测试树：
    root
    └── Characters
        ├── Blonde (tag)
        └── Hair (folder, single_selection)
            ├── Long (tag)
            └── Short (tag)
    """
    root = TagItem("root", is_folder=True)
    chars = TagItem("Characters", is_folder=True)
    root.add_child(chars)
    chars.add_child(TagItem("Blonde", is_folder=False, display_name="金发"))
    hair = TagItem("Hair", is_folder=True)
    hair.single_selection = True
    chars.add_child(hair)
    hair.add_child(TagItem("Long", is_folder=False, display_name="长发"))
    hair.add_child(TagItem("Short", is_folder=False, display_name="短发"))
    return root