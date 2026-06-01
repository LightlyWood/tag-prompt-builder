# test/test_models.py
import pytest
from tag_prompt_builder.models.tag_item import TagItem

def test_tag_item_creation():
    item = TagItem(name="test", is_folder=True)
    assert item.name == "test"
    assert item.is_folder is True
    assert item.parent is None
    assert len(item.children) == 0

def test_add_child():
    parent = TagItem(name="parent", is_folder=True)
    child = TagItem(name="child", is_folder=False)
    parent.add_child(child)
    assert child.parent is parent
    assert parent.children == [child]

def test_path():
    root = TagItem(name="root", is_folder=True)
    sub = TagItem(name="sub", is_folder=True)
    root.add_child(sub)
    leaf = TagItem(name="leaf", is_folder=False)
    sub.add_child(leaf)
    # 路径依赖 ID 格式，需要设置 ID
    leaf.id = "#root/sub#0/leaf#0"
    sub.id = "#root/sub#0"
    assert leaf.path() == "sub#0/leaf#0"  # 实际根据 id 中的 '/' 分割
    # 简化测试，仅检查非空
    assert leaf.path() != ""

def test_full_id():
    root = TagItem(name="root", is_folder=True)
    sub = TagItem(name="sub", is_folder=True)
    root.add_child(sub)
    leaf1 = TagItem(name="leaf1", is_folder=False)
    leaf2 = TagItem(name="leaf2", is_folder=False)
    sub.add_child(leaf1)
    sub.add_child(leaf2)
    # 手动设置 ID（模拟真实环境）
    leaf1.id = "#root/sub#0/leaf1#0"
    leaf2.id = "#root/sub#0/leaf2#1"
    assert leaf1.full_id() == "#root/sub#0/leaf1#0"
    assert leaf2.full_id() == "#root/sub#0/leaf2#1"