# ui/main_window.py
import sys
from PyQt6.QtWidgets import (QMainWindow, QSplitter, QVBoxLayout, QWidget,
                             QFileDialog, QMenuBar, QAction)
from PyQt6.QtCore import Qt
from models.tag_model import TagTreeModel
from managers.tag_manager import TagManager
from ui.widgets.tag_tree_view import TagTreeView
from ui.widgets.sort_panel import SortPanel
from ui.widgets.preview_panel import PreviewPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("提示词构建器 v0.1")
        self.resize(1200, 800)

        self.tag_manager = TagManager()
        self.tag_manager.load_default_library()

        self.model = TagTreeModel(self.tag_manager.root)
        self.tag_tree_view = TagTreeView(self.model, tag_manager=self.tag_manager)
        self.tag_tree_view.tag_checked_changed.connect(self.refresh_all)

        self.sort_panel = SortPanel()
        self.preview_panel = PreviewPanel()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.sort_panel)
        right_layout.addWidget(self.preview_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tag_tree_view)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self.init_menu()
        self.sort_panel.order_changed.connect(self.refresh_preview)

    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")

        save_folder = QAction("保存文件夹预设", self)
        save_folder.triggered.connect(self.save_folder_preset)
        file_menu.addAction(save_folder)

        load_folder = QAction("加载文件夹预设", self)
        load_folder.triggered.connect(self.load_folder_preset)
        file_menu.addAction(load_folder)

    def refresh_all(self):
        self.sort_panel.build_from_checked(self.tag_manager.root)
        self.refresh_preview()

    def refresh_preview(self):
        display, output = self.build_prompt_from_sort()
        self.preview_panel.update_preview(display, output)

    def build_prompt_from_sort(self):
        """遍历排序树，生成中文显示串和英文输出串"""
        display_parts = []
        output_parts = []
        self._traverse_sort(self.sort_panel.tree.invisibleRootItem(), display_parts, output_parts)
        return ', '.join(display_parts), ', '.join(output_parts)

    def _traverse_sort(self, parent_item, display_list, output_list):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.childCount() > 0:
                self._traverse_sort(child, display_list, output_list)
            else:
                tag_item = child.data(0, Qt.ItemDataRole.UserRole)
                if tag_item:
                    display_list.append(tag_item.display_name)
                    output_list.append(tag_item.name)
                else:
                    display_list.append(child.text(0))
                    output_list.append(child.text(0))

    def save_folder_preset(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "保存预设", "presets", "JSON (*.json)")
        if file_name:
            ids = []
            self._collect_checked(self.tag_manager.root, ids)
            self.tag_manager.save_folder_preset(file_name, ids, {})

    def load_folder_preset(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "加载预设", "presets", "JSON (*.json)")
        if file_name:
            preset = self.tag_manager.load_folder_preset(file_name)
            if preset:
                self._restore_preset(preset)

    def _collect_checked(self, folder, ids):
        for child in folder.children:
            if child.is_folder:
                self._collect_checked(child, ids)
            elif child.checked:
                ids.append(child)

    def _restore_preset(self, preset):
        # 重置所有选中
        def reset(item):
            for c in item.children:
                c.checked = False
                if c.is_folder:
                    reset(c)
        reset(self.tag_manager.root)
        # 根据路径设置选中（略）
        self.refresh_all()