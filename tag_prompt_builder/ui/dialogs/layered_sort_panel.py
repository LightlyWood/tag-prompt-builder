# ui/widgets/layered_sort_panel.py
import uuid
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QLabel, QMenu, QDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from tag_prompt_builder.models.tag_item import TagItem
from typing import List, Dict, Optional

class SortNode:
    def __init__(self, full_id: str, is_folder: bool = False, display_name: str = "",
                 is_random_slot: bool = False, random_slot_config: dict = None):
        self.full_id = full_id
        self.is_folder = is_folder
        self.display_name = display_name
        self.is_random_slot = is_random_slot
        self.random_slot_config = random_slot_config or {}
        self.children: List['SortNode'] = []
        self.parent: Optional['SortNode'] = None

    def add_child(self, child: 'SortNode'):
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'SortNode'):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

class LayeredSortPanel(QWidget):
    order_changed = pyqtSignal()
    random_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tag_manager = None

        self.sort_root = SortNode("root", is_folder=True, display_name="root")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 面包屑
        breadcrumb_layout = QHBoxLayout()
        breadcrumb_layout.addWidget(QLabel("路径："))
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(2)
        breadcrumb_layout.addWidget(self.breadcrumb_widget)
        breadcrumb_layout.addStretch()
        layout.addLayout(breadcrumb_layout)

        # 当前层级列表
        self.current_list = QListWidget()
        self.current_list.setDragEnabled(True)
        self.current_list.setAcceptDrops(True)
        self.current_list.setDropIndicatorShown(True)
        self.current_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.current_list.model().rowsMoved.connect(lambda: self.order_changed.emit())
        self.current_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        # 右键菜单
        self.current_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.current_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.current_list)

        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_up = QPushButton("上移")
        btn_up.clicked.connect(self.move_item_up)
        btn_down = QPushButton("下移")
        btn_down.clicked.connect(self.move_item_down)
        btn_enter = QPushButton("进入子层级")
        btn_enter.clicked.connect(self.enter_selected_folder)
        btn_back = QPushButton("返回上级")
        btn_back.clicked.connect(self.go_to_parent)
        btn_layout.addWidget(btn_up)
        btn_layout.addWidget(btn_down)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_enter)
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        self.current_folder_node: SortNode = self.sort_root
        self.node_map: Dict[str, SortNode] = {}
        self.setMinimumWidth(250)

    def set_tag_manager(self, mgr):
        self.tag_manager = mgr

    # ---------- 面包屑与导航 ----------
    def update_breadcrumb(self):
        for i in reversed(range(self.breadcrumb_layout.count())):
            widget = self.breadcrumb_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        path = []
        node = self.current_folder_node
        while node and node.full_id != "root":
            path.append((node.display_name, node.full_id))
            node = node.parent
        path.reverse()
        root_btn = QPushButton("根")
        root_btn.setFlat(True)
        root_btn.clicked.connect(lambda: self.navigate_to("root"))
        self.breadcrumb_layout.addWidget(root_btn)
        for name, fid in path:
            sep = QLabel(">")
            sep.setFixedWidth(15)
            sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.breadcrumb_layout.addWidget(sep)
            btn = QPushButton(name)
            btn.setFlat(True)
            btn.clicked.connect(lambda checked, f=fid: self.navigate_to(f))
            self.breadcrumb_layout.addWidget(btn)
        self.breadcrumb_layout.addStretch()

    def navigate_to(self, full_id: str):
        node = self.node_map.get(full_id)
        if node and node.is_folder:
            self.current_folder_node = node
            self.refresh_current_view()
            self.update_breadcrumb()

    def go_to_parent(self):
        if self.current_folder_node.parent and self.current_folder_node.full_id != "root":
            self.current_folder_node = self.current_folder_node.parent
            self.refresh_current_view()
            self.update_breadcrumb()
            self.order_changed.emit()

    def refresh_current_view(self):
        self.current_list.blockSignals(True)
        self.current_list.clear()
        for child in self.current_folder_node.children:
            item = QListWidgetItem(child.display_name)
            item.setData(Qt.ItemDataRole.UserRole, child.full_id)
            self.current_list.addItem(item)
        self.current_list.blockSignals(False)

    # ---------- 同步已选标签 ----------
    def sync_from_checked(self, root_tag_item: TagItem):
        if not self.tag_manager:
            return

        checked_tags = []
        def collect(item):
            if not item.is_folder:
                if item.checked:
                    checked_tags.append(item)
            else:
                for child in item.children:
                    collect(child)
        collect(root_tag_item)

        checked_ids = set(tag.full_id() for tag in checked_tags)

        # 添加新标签
        for tag in checked_tags:
            fid = tag.full_id()
            if fid not in self.node_map:
                tag_node = SortNode(fid, is_folder=False, display_name=tag.display_name)
                parent_node = self._ensure_folder_path(tag.parent)
                parent_node.add_child(tag_node)
                self.node_map[fid] = tag_node

        # 移除取消勾选的标签
        to_remove = [fid for fid, node in self.node_map.items() if not node.is_folder and fid not in checked_ids]
        for fid in to_remove:
            node = self.node_map.pop(fid)
            parent = node.parent
            if parent:
                parent.remove_child(node)
                while parent and parent.full_id != "root" and not parent.children:
                    grand = parent.parent
                    if grand:
                        grand.remove_child(parent)
                        del self.node_map[parent.full_id]
                    parent = grand

        if self.current_folder_node.full_id not in self.node_map and self.current_folder_node.full_id != "root":
            self.current_folder_node = self.sort_root
        self.refresh_current_view()
        self.update_breadcrumb()

    def _ensure_folder_path(self, folder_tag: TagItem) -> SortNode:
        if folder_tag is None or folder_tag.full_id() == '#root':
            return self.sort_root
        parent_node = self._ensure_folder_path(folder_tag.parent)
        folder_fid = folder_tag.full_id()
        if folder_fid in self.node_map:
            return self.node_map[folder_fid]
        folder_node = SortNode(folder_fid, is_folder=True, display_name=folder_tag.name)
        parent_node.add_child(folder_node)
        self.node_map[folder_fid] = folder_node
        return folder_node

    # ---------- 移动操作 ----------
    def move_item_up(self):
        row = self.current_list.currentRow()
        if row > 0:
            self._swap_items(row, row - 1)

    def move_item_down(self):
        row = self.current_list.currentRow()
        if row < self.current_list.count() - 1:
            self._swap_items(row, row + 1)

    def _swap_items(self, i, j):
        item_i = self.current_list.takeItem(i)
        self.current_list.insertItem(j, item_i)
        self.current_list.setCurrentRow(j)
        children = self.current_folder_node.children
        children[i], children[j] = children[j], children[i]
        self.order_changed.emit()

    def on_item_double_clicked(self, item):
        fid = item.data(Qt.ItemDataRole.UserRole)
        node = self.node_map.get(fid)
        if node and node.is_folder:
            self.current_folder_node = node
            self.refresh_current_view()
            self.update_breadcrumb()
            self.order_changed.emit()

    def enter_selected_folder(self):
        item = self.current_list.currentItem()
        if item:
            self.on_item_double_clicked(item)

    # ---------- 右键菜单 ----------
    def show_context_menu(self, pos):
        menu = QMenu(self)
        insert_random_action = QAction("插入随机槽", self)
        insert_random_action.triggered.connect(self.insert_random_slot)
        menu.addAction(insert_random_action)

        cur_item = self.current_list.currentItem()
        if cur_item:
            fid = cur_item.data(Qt.ItemDataRole.UserRole)
            node = self.node_map.get(fid)
            if node and node.is_random_slot:
                edit_action = QAction("编辑随机槽", self)
                edit_action.triggered.connect(self.edit_random_slot)
                menu.addAction(edit_action)
                test_action = QAction("试抽一次", self)
                test_action.triggered.connect(self.test_random_slot)
                menu.addAction(test_action)
                delete_action = QAction("删除随机槽", self)
                delete_action.triggered.connect(self.delete_random_slot)
                menu.addAction(delete_action)
        menu.exec(self.current_list.viewport().mapToGlobal(pos))

    # ---------- 随机槽操作 ----------
    def insert_random_slot(self):
        if not self.tag_manager:
            return
        from tag_prompt_builder.ui.dialogs.random_slot_dialog import RandomSlotDialog
        dialog = RandomSlotDialog(self.tag_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            slot_id = f"random_slot_{uuid.uuid4().hex[:8]}"
            node = SortNode(slot_id, is_folder=False, display_name="🎲 " + config.get("pool_name", "随机槽"),
                            is_random_slot=True, random_slot_config=config)
            self.current_folder_node.add_child(node)
            self.node_map[slot_id] = node
            self.refresh_current_view()
            self.update_breadcrumb()
            self.order_changed.emit()

    def edit_random_slot(self):
        cur = self.current_list.currentItem()
        fid = cur.data(Qt.ItemDataRole.UserRole)
        node = self.node_map.get(fid)
        if node and node.is_random_slot:
            from tag_prompt_builder.ui.dialogs.random_slot_dialog import RandomSlotDialog
            dialog = RandomSlotDialog(self.tag_manager, self, node.random_slot_config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                node.random_slot_config = dialog.get_config()
                node.display_name = "🎲 " + node.random_slot_config.get("pool_name", "随机槽")
                self.refresh_current_view()
                self.order_changed.emit()

    def test_random_slot(self):
        cur = self.current_list.currentItem()
        fid = cur.data(Qt.ItemDataRole.UserRole)
        node = self.node_map.get(fid)
        if node and node.is_random_slot:
            result = self.perform_random_slot(node)
            QMessageBox.information(self, "试抽结果", "抽取到的标签：\n" + ", ".join(tag.display_name for tag in result))

    def delete_random_slot(self):
        cur = self.current_list.currentItem()
        if cur:
            fid = cur.data(Qt.ItemDataRole.UserRole)
            node = self.node_map.pop(fid, None)
            if node:
                self.current_folder_node.remove_child(node)
                self.refresh_current_view()
                self.order_changed.emit()

    def perform_random_slot(self, slot_node: SortNode) -> List[TagItem]:
        """根据随机槽配置执行抽取，返回 TagItem 列表"""
        config = slot_node.random_slot_config
        pool_name = config.get("pool_name")
        count = config.get("count", 1)
        allow_duplicates = config.get("allow_duplicates", False)

        if not pool_name or count <= 0:
            return []

        pool_tags = self.tag_manager.random_pool_manager.get_pool_tags(pool_name, self.tag_manager)
        if not pool_tags:
            return []

        # 互斥分组
        exclusion_groups = self.tag_manager.get_exclusion_groups(pool_tags)

        # 拆分互斥组和个体标签
        group_map = {}  # group_id -> list of tags
        individual_tags = []
        for tag in pool_tags:
            folder = tag.parent
            while folder and not folder.single_selection:
                folder = folder.parent
            if folder and folder.single_selection:
                gid = folder.full_id()
                group_map.setdefault(gid, []).append(tag)
            else:
                individual_tags.append(tag)

        chosen = []

        if not allow_duplicates:
            # 不重复：每个互斥组随机选一个，剩余从个体标签随机取
            for gid, tags in group_map.items():
                chosen.append(random.choice(tags))
            remaining = count - len(chosen)
            if remaining > 0 and individual_tags:
                if remaining >= len(individual_tags):
                    chosen.extend(individual_tags)
                else:
                    chosen.extend(random.sample(individual_tags, remaining))
            return chosen[:count]
        else:
            # 允许重复：多次抽取，避开互斥冲突
            for _ in range(count):
                available = list(pool_tags)
                # 移除与已选标签互斥的标签
                for existing in chosen:
                    folder = existing.parent
                    while folder and not folder.single_selection:
                        folder = folder.parent
                    if folder and folder.single_selection:
                        gid = folder.full_id()
                        available = [t for t in available if not self._is_in_exclusive_group(t, gid)]
                if not available:
                    break
                chosen.append(random.choice(available))
            return chosen

    def _is_in_exclusive_group(self, tag: TagItem, group_id: str) -> bool:
        folder = tag.parent
        while folder and not folder.single_selection:
            folder = folder.parent
        return folder is not None and folder.single_selection and folder.full_id() == group_id

    # ---------- 排序结构导出/导入 ----------
    def get_sort_structure(self):
        def export_node(node):
            if node.is_random_slot:
                return {"is_random_slot": True, "config": node.random_slot_config}
            if not node.is_folder:
                return node.full_id
            children_list = [export_node(c) for c in node.children]
            return {node.full_id: children_list}
        result = []
        for child in self.sort_root.children:
            result.append(export_node(child))
        return result

    def restore_sort_structure(self, structure, tag_manager):
        self.sort_root.children.clear()
        self.node_map.clear()

        def build_node(item, parent):
            if isinstance(item, str):
                tag = tag_manager.find_item_by_full_id(item)
                display = tag.display_name if (tag and not tag.is_folder) else item
                node = SortNode(item, is_folder=False, display_name=display)
                parent.add_child(node)
                self.node_map[item] = node
            elif isinstance(item, dict):
                if "is_random_slot" in item:
                    # 随机槽节点
                    config = item.get("config", {})
                    slot_id = f"random_slot_{uuid.uuid4().hex[:8]}"
                    display = "🎲 " + config.get("pool_name", "随机槽")
                    node = SortNode(slot_id, is_folder=False, display_name=display,
                                    is_random_slot=True, random_slot_config=config)
                    parent.add_child(node)
                    self.node_map[slot_id] = node
                else:
                    for fid, children in item.items():
                        folder_tag = tag_manager.find_item_by_full_id(fid)
                        folder_name = folder_tag.name if (folder_tag and folder_tag.is_folder) else fid
                        folder_node = SortNode(fid, is_folder=True, display_name=folder_name)
                        parent.add_child(folder_node)
                        self.node_map[fid] = folder_node
                        for child in children:
                            build_node(child, folder_node)

        for top_item in structure:
            build_node(top_item, self.sort_root)

        self.current_folder_node = self.sort_root
        self.refresh_current_view()
        self.update_breadcrumb()
        self.order_changed.emit()