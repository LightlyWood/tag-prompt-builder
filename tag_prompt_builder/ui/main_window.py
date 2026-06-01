# tag_prompt_builder/ui/main_window.py
import sys
import json
import os
import re
from PyQt6.QtWidgets import (QMainWindow, QSplitter, QVBoxLayout, QWidget,
                             QFileDialog, QMenuBar, QInputDialog, QMessageBox,
                             QTabWidget, QMenu)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QModelIndex
from tag_prompt_builder.models.tag_model import TagTreeModel
from tag_prompt_builder.managers.tag_manager import TagManager
from tag_prompt_builder.ui.widgets.tag_tree_view import TagTreeView
from tag_prompt_builder.ui.widgets.preview_panel import PreviewPanel
from tag_prompt_builder.ui.widgets.favorites_panel import FavoritesPanel
from tag_prompt_builder.ui.widgets.tag_detail_panel import TagDetailPanel
from tag_prompt_builder.ui.dialogs.preset_manager_dialog import PresetManagerDialog
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.app_config import RECENT_FILE, PRESETS_DIR
from tag_prompt_builder.ui.widgets.graphic_sort_panel import GraphicSortPanel
from tag_prompt_builder.ui.dialogs.random_pool_manager_dialog import RandomPoolManagerDialog


class MainWindow(QMainWindow):
    MAX_HISTORY = 20

    @staticmethod
    def _parse_prompt_tags(raw_text: str) -> list:
        tags = []
        text = raw_text.replace('\n', ',')
        def tokenize(s):
            s = s.strip()
            if not s:
                return []
            m = re.match(r'^[\[\(]\s*([^:]+?)\s*:\s*\d+(?:\.\d+)?\s*[\]\)]$', s)
            if m:
                return [m.group(1).strip()]
            m = re.match(r'^[\[\(](.*)[\]\)]$', s)
            if m:
                inner = m.group(1)
                parts = re.split(r',', inner)
                result = []
                for part in parts:
                    result.extend(tokenize(part))
                return result
            return [s]
        for segment in re.split(r',', text):
            segment = segment.strip()
            if segment:
                tags.extend(tokenize(segment))
        return tags

    def __init__(self):
        super().__init__()
        self.setWindowTitle("提示词构建器 v0.9")
        self.resize(1200, 800)

        self.tag_manager = TagManager()
        self.model = TagTreeModel(self.tag_manager)

        self.tab_widget = QTabWidget()
        self.tag_tree_view = TagTreeView(self.model, tag_manager=self.tag_manager)
        self.tag_tree_view.tag_checked_changed.connect(self.refresh_all)
        self.tag_tree_view.favorites_changed.connect(self.refresh_favorites)
        self.tag_tree_view.tag_detail_requested.connect(self.show_tag_detail)

        self.favorites_panel = FavoritesPanel(self.tag_manager)
        self.favorites_panel.tag_checked_changed.connect(self.refresh_all)

        self.tab_widget.addTab(self.tag_tree_view, "标签库")
        self.tab_widget.addTab(self.favorites_panel, "收藏")

        self.sort_panel = GraphicSortPanel()
        self.sort_panel.set_tag_manager(self.tag_manager)
        self.sort_panel.order_changed.connect(self.refresh_preview)
        self.sort_panel.tag_detail_requested.connect(self.show_tag_detail)

        self.preview_panel = PreviewPanel()
        self.preview_panel.clipboard_copied.connect(self.on_clipboard_copied)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.sort_panel, 2)
        right_layout.addWidget(self.preview_panel, 1)

        self.detail_panel = TagDetailPanel()
        right_layout.addWidget(self.detail_panel, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self.recent_list = self.load_recent()
        self.init_menu()
        self.refresh_favorites()
        self.update_recent_menu()

    def show_tag_detail(self, tag: TagItem):
        self.detail_panel.show_tag_detail(tag)

    def refresh_all(self):
        checked_tags = [item for item in self.model.all_items() if item.checked]
        self.sort_panel.sync_from_checked_list(checked_tags)
        self.refresh_preview()

    def refresh_preview(self):
        display, output = self.build_prompt_from_sort()
        self.preview_panel.update_preview(display, output)

    def build_prompt_from_sort(self):
        display_parts = []
        output_parts = []
        def traverse(node):
            if node.is_random_slot:
                tags = self.sort_panel.perform_random_slot(node)
                for tag in tags:
                    display_parts.append(tag.display_name)
                    output_parts.append(tag.name)
            elif not node.is_folder:
                tag = self.tag_manager.find_item_by_full_id(node.full_id)
                if tag and not tag.is_folder:
                    display_parts.append(tag.display_name)
                    if node.weight != 1.0:
                        output_parts.append(f"({tag.name}:{node.weight})")
                    else:
                        output_parts.append(tag.name)
                else:
                    display_parts.append(node.display_name)
                    if node.weight != 1.0:
                        output_parts.append(f"({node.display_name}:{node.weight})")
                    else:
                        output_parts.append(node.display_name)
            else:
                for child in node.children:
                    traverse(child)
        for top in self.sort_panel.sort_root.children:
            traverse(top)
        return ', '.join(display_parts), ', '.join(output_parts)

    def on_clipboard_copied(self, text: str):
        text = text.strip()
        if not text:
            return
        if text in self.recent_list:
            self.recent_list.remove(text)
        self.recent_list.insert(0, text)
        if len(self.recent_list) > self.MAX_HISTORY:
            self.recent_list = self.recent_list[:self.MAX_HISTORY]
        self.save_recent()
        self.update_recent_menu()

    # ---------- 公用辅助方法 ----------
    def _reset_all_checks(self):
        """将所有标签的勾选状态置为 False"""
        for item in self.tag_manager._items.values():
            item.checked = False

    def _get_name_mappings(self):
        """返回 {小写英文名: TagItem} 和 {小写显示名: TagItem} 的映射"""
        name_map = {}
        display_map = {}
        for item in self.tag_manager._items.values():
            if not item.is_folder:
                name_map[item.name.lower()] = item
                display_map[item.display_name.lower()] = item
        return name_map, display_map

    # ---------- 方案加载 ----------
    def apply_tag_preset(self, preset_name: str):
        preset = self.tag_manager.load_folder_preset(preset_name)
        if not preset:
            QMessageBox.warning(self, "方案不存在", "找不到该方案。")
            return
        tag_ids = preset.get('selected', [])
        if not tag_ids:
            QMessageBox.warning(self, "空方案", "该方案不含任何标签。")
            return

        self._reset_all_checks()
        matched = 0
        for fid in tag_ids:
            tag = self.tag_manager.find_item_by_full_id(fid)
            if tag and not tag.is_folder:
                tag.checked = True
                matched += 1
        self.model.beginResetModel()
        self.model.endResetModel()
        self.refresh_all()
        QMessageBox.information(self, "加载完成", f"成功勾选 {matched}/{len(tag_ids)} 个标签。")

    def save_folder_preset(self):
        preset_name, ok = QInputDialog.getText(self, "保存方案", "方案名称：")
        if not ok or not preset_name.strip():
            return
        preset_name = preset_name.strip()
        sort_structure = self.sort_panel.get_sort_structure()
        selected_ids = [item.full_id() for item in self.model.all_items() if item.checked]
        self.tag_manager.save_folder_preset(preset_name, selected_ids, sort_structure)

    def load_folder_preset(self):
        presets = self.tag_manager.list_tag_presets()
        if not presets:
            QMessageBox.information(self, "无方案", "还没有保存任何方案。")
            return
        name, ok = QInputDialog.getItem(self, "加载方案", "选择方案：", presets, 0, False)
        if not ok or not name:
            return
        self.apply_tag_preset(name)

    def manage_presets(self):
        dialog = PresetManagerDialog(self.tag_manager, self)
        dialog.exec()

    def import_from_prompt(self):
        text, ok = QInputDialog.getMultiLineText(self, "导入提示词", "粘贴以逗号分隔的提示词：")
        if not ok or not text.strip():
            return
        self.apply_tag_list(text)
        if QMessageBox.question(self, "保存方案", "是否保存为方案？",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.save_folder_preset()

    def apply_tag_list(self, raw_tags):
        """优化后的导入提示词方法，使用缓存映射"""
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        raw_text = ', '.join(raw_tags)
        clean_tags = self._parse_prompt_tags(raw_text)

        name_map, display_map = self._get_name_mappings()

        matched = []
        unmatched = []
        for tag in clean_tags:
            lt = tag.lower()
            if lt in name_map:
                matched.append(name_map[lt])
            elif lt in display_map:
                matched.append(display_map[lt])
            else:
                unmatched.append(tag)

        # 处理未匹配标签：询问是否添加到“未匹配标签”文件夹
        if unmatched:
            reply = QMessageBox.question(
                self, "未匹配标签",
                f"以下 {len(unmatched)} 个标签未找到：\n\n" +
                "\n".join(unmatched) +
                "\n\n是否将它们添加到标签库的“未匹配标签”文件夹中？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # 寻找或创建“未匹配标签”文件夹
                unmatched_folder = None
                for child in self.tag_manager.get_root_children():
                    if child.is_folder and child.name == "未匹配标签":
                        unmatched_folder = child
                        break
                if not unmatched_folder:
                    root_idx = QModelIndex()
                    new_idx = self.model.append_tag(root_idx, "未匹配标签", is_folder=True, display_name="未匹配标签")
                    if new_idx.isValid():
                        unmatched_folder = self.model.item_from_index(new_idx)
                if unmatched_folder:
                    for tag_text in unmatched:
                        folder_idx = self.model.index_from_item(unmatched_folder)
                        new_idx = self.model.append_tag(folder_idx, tag_text, is_folder=False, display_name=tag_text)
                        if new_idx.isValid():
                            self.model.setData(new_idx, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
                    self.tag_manager.save_library()
            else:
                QMessageBox.information(self, "未匹配标签", "未匹配标签已被忽略。")

        # 重置所有勾选并应用匹配到的标签
        self._reset_all_checks()
        for t in matched:
            t.checked = True
            idx = self.model.index_from_item(t)
            if idx.isValid():
                self.model.setData(idx, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
        self.model.beginResetModel()
        self.model.endResetModel()
        self.refresh_all()

    # ---------- 最近使用 ----------
    def load_recent(self):
        if os.path.exists(RECENT_FILE):
            try:
                with open(RECENT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data[:self.MAX_HISTORY] if isinstance(data, list) else []
            except:
                pass
        return []

    def restore_recent(self, text: str):
        raw_tags = [t.strip() for t in text.split(',') if t.strip()]
        if raw_tags:
            self.apply_tag_list(raw_tags)

    def update_recent_menu(self):
        self.recent_menu.clear()
        if not self.recent_list:
            a = QAction("（无记录）", self)
            a.setEnabled(False)
            self.recent_menu.addAction(a)
            return
        for t in self.recent_list:
            d = t if len(t) <= 50 else t[:47] + '...'
            act = QAction(d, self)
            act.setToolTip(t)
            act.triggered.connect(lambda checked, text=t: self.restore_recent(text))
            self.recent_menu.addAction(act)
        self.recent_menu.addSeparator()
        clear_act = QAction("清空历史", self)
        clear_act.triggered.connect(self.clear_recent)
        self.recent_menu.addAction(clear_act)

    def clear_recent(self):
        self.recent_list.clear()
        self.save_recent()
        self.update_recent_menu()

    def manage_random_pools(self):
        dialog = RandomPoolManagerDialog(self.tag_manager.random_pool_manager, self.tag_manager, self)
        dialog.exec()

    def save_recent(self):
        try:
            with open(RECENT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.recent_list, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    # ---------- 菜单栏 ----------
    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        file_menu.addAction(QAction("从提示词导入", self, triggered=self.import_from_prompt))
        file_menu.addSeparator()
        file_menu.addAction(QAction("保存方案", self, triggered=self.save_folder_preset))
        file_menu.addAction(QAction("加载方案", self, triggered=self.load_folder_preset))
        file_menu.addAction(QAction("管理组合", self, triggered=self.manage_presets))
        manage_pools_action = QAction("管理随机池", self)
        manage_pools_action.triggered.connect(self.manage_random_pools)
        file_menu.addAction(manage_pools_action)
        self.recent_menu = QMenu("最近使用", self)
        menubar.addMenu(self.recent_menu)

    def refresh_favorites(self):
        self.favorites_panel.refresh()