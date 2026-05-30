import pytest
from tag_prompt_builder.models.tag_item import TagItem

def test_tag_item_creation():
    item = TagItem("test", is_folder=True)
    assert item.name == "test"
    assert item.is_folder is True
    assert item.parent is None
    assert len(item.children) == 0

def test_add_child():
    parent = TagItem("parent", is_folder=True)
    child = TagItem("child", is_folder=False)
    parent.add_child(child)
    assert child.parent is parent
    assert parent.children == [child]

def test_path():
    root = TagItem("root", is_folder=True)
    sub = TagItem("sub", is_folder=True)
    root.add_child(sub)
    leaf = TagItem("leaf")
    sub.add_child(leaf)
    assert leaf.path() == "/sub/leaf"
    assert sub.path() == "/sub"      # 父节点相对于根的路径
    assert root.path() == ""         # 根路径为空

def test_full_id():
    root = TagItem("root", is_folder=True)
    sub = TagItem("sub", is_folder=True)
    root.add_child(sub)
    leaf1 = TagItem("leaf1")
    leaf2 = TagItem("leaf2")
    sub.add_child(leaf1)
    sub.add_child(leaf2)
    assert leaf1.full_id() == "#root/sub#0/leaf1#0"   # 修正
    assert leaf2.full_id() == "#root/sub#0/leaf2#1"   # 修正