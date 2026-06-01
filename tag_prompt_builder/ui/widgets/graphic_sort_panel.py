# tag_prompt_builder/ui/widgets/graphic_sort_panel.py
import uuid
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
                             QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem,
                             QGraphicsPathItem, QMenu, QMessageBox, QDialog, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import (QPen, QBrush, QColor, QFont, QPainter, QPainterPath,
                         QAction, QWheelEvent)
from tag_prompt_builder.models.tag_item import TagItem
from typing import List, Dict, Optional
from collections import defaultdict
from tag_prompt_builder.ui.helpers.random_util import perform_random_slot as _perform_random_slot

LAYER_HORIZONTAL_GAP = 180
NODE_VERTICAL_GAP = 15
NODE_WIDTH = 130
NODE_HEIGHT = 28
WEIGHT_BOX_WIDTH = 40


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
        self.weight: float = 1.0
        self.graphic_item: Optional['SortNodeItem'] = None
        self._layout_x: float = 0.0
        self._layout_y: float = 0.0

    def add_child(self, child: 'SortNode'):
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: 'SortNode'):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def tag_depth(self) -> int:
        if self.parent is None:
            return 0
        return self.parent.tag_depth() + 1 if self.parent.is_folder else 0


class SortNodeItem(QGraphicsRectItem):
    FOLDER_BG = QColor(220, 220, 220)
    TAG_BG = QColor(200, 230, 255)
    RANDOM_BG = QColor(255, 255, 150)
    SELECTED_PEN = QPen(QColor(0, 120, 215), 2)
    NORMAL_PEN = QPen(Qt.GlobalColor.gray)

    def __init__(self, node: SortNode):
        super().__init__()
        self.node = node
        node.graphic_item = self
        self.setRect(0, 0, NODE_WIDTH, NODE_HEIGHT)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self._update_style()

        self.text = QGraphicsTextItem(node.display_name, self)
        self.text.setDefaultTextColor(QColor(0, 0, 0))
        self.text.setPos(5, 3)
        font = QFont()
        font.setPointSize(9)
        self.text.setFont(font)

        self.weight_text = None
        if not node.is_folder and not node.is_random_slot:
            self.weight_text = QGraphicsTextItem(f"w:{node.weight:.1f}", self)
            self.weight_text.setDefaultTextColor(QColor(100, 100, 100))
            self.weight_text.setPos(NODE_WIDTH - WEIGHT_BOX_WIDTH - 5, 5)
            font2 = QFont()
            font2.setPointSize(7)
            self.weight_text.setFont(font2)

        self.layer_x = 0.0

    def _update_style(self):
        if self.node.is_random_slot:
            bg = self.RANDOM_BG
        elif self.node.is_folder:
            bg = self.FOLDER_BG
        else:
            bg = self.TAG_BG
        self.setBrush(QBrush(bg))
        self.setPen(self.NORMAL_PEN)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(self.SELECTED_PEN)
            painter.drawRect(self.rect())

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            new_pos.setX(self.layer_x)
            return new_pos
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            panel = self.scene().views()[0].parent()
            if isinstance(panel, GraphicSortPanel):
                panel.update_edges()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        panel = self.scene().views()[0].parent()
        if isinstance(panel, GraphicSortPanel):
            if not self.node.is_folder and not self.node.is_random_slot:
                weight, ok = QInputDialog.getDouble(None, "设置权重", "输入权重值 (0.1-5.0):",
                                                    self.node.weight, 0.1, 5.0, 1)
                if ok:
                    self.node.weight = weight
                    self.weight_text.setPlainText(f"w:{weight:.1f}")
                    panel.order_changed.emit()
            elif self.node.is_random_slot:
                panel.edit_random_slot(self.node)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            panel = self.scene().views()[0].parent()
            if isinstance(panel, GraphicSortPanel) and not self.node.is_folder and not self.node.is_random_slot:
                tag = panel.tag_manager.find_item_by_full_id(self.node.full_id)
                if tag:
                    panel.tag_detail_requested.emit(tag)
        super().mousePressEvent(event)


class EdgeItem(QGraphicsPathItem):
    def __init__(self, parent_item, child_item):
        super().__init__()
        self.parent_item = parent_item
        self.child_item = child_item
        self.setPen(QPen(QColor(150, 150, 150), 1))
        self.update_path()

    def update_path(self):
        if not self.parent_item or not self.child_item:
            return
        p_rect = self.parent_item.rect()
        c_rect = self.child_item.rect()
        p_center = self.parent_item.pos() + QPointF(p_rect.width(), p_rect.height() / 2)
        c_center = self.child_item.pos() + QPointF(0, c_rect.height() / 2)
        path = QPainterPath()
        path.moveTo(p_center)
        mid_x = (p_center.x() + c_center.x()) / 2
        path.cubicTo(QPointF(mid_x, p_center.y()), QPointF(mid_x, c_center.y()), c_center)
        self.setPath(path)


class GraphicSortPanel(QWidget):
    order_changed = pyqtSignal()
    random_requested = pyqtSignal()
    tag_detail_requested = pyqtSignal(TagItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tag_manager = None
        self.sort_root = SortNode("root", is_folder=True, display_name="root")
        self.node_map: Dict[str, SortNode] = {}

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.setMinimumWidth(250)
        self._current_scale = 1.0
        self._layout_dirty = False
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._do_rebuild_graphics)

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        self.view.viewport().installEventFilter(self)

    def set_tag_manager(self, mgr):
        self.tag_manager = mgr

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.view.scale(factor, factor)
        self._current_scale *= factor

    # ---------- 拖拽结束排序 ----------
    def eventFilter(self, obj, event):
        if obj is self.view.viewport() and event.type() == event.Type.MouseButtonRelease:
            for item in self.scene.selectedItems():
                if isinstance(item, SortNodeItem):
                    self._finish_drag(item)
                    break
        return super().eventFilter(obj, event)

    def _finish_drag(self, dragged_item: SortNodeItem):
        node = dragged_item.node
        if not node.parent:
            return
        siblings = node.parent.children
        if len(siblings) <= 1:
            return
        y_nodes = [(sib.graphic_item.pos().y(), sib) for sib in siblings if sib.graphic_item]
        if not y_nodes:
            return
        y_nodes.sort(key=lambda x: x[0])
        new_order = [sib for _, sib in y_nodes]
        node.parent.children = new_order
        self._rebuild_graphics()

    # ---------- 数据同步（增量更新） ----------
    def sync_from_checked_list(self, checked_tags):
        if not self.tag_manager:
            return

        checked_ids = set(tag.full_id() for tag in checked_tags)

        # 移除取消勾选的标签
        to_remove = [fid for fid, node in self.node_map.items()
                     if not node.is_folder and fid not in checked_ids]
        for fid in to_remove:
            self._remove_node_graphics(fid)

        # 添加新勾选的标签
        for tag in checked_tags:
            fid = tag.full_id()
            if fid not in self.node_map:
                tag_node = SortNode(fid, is_folder=False, display_name=tag.display_name)
                parent_node = self._ensure_folder_path_by_tag(tag)
                parent_node.add_child(tag_node)
                self.node_map[fid] = tag_node
                self._add_node_graphics(tag_node)

        # 使用防抖重建
        self._rebuild_graphics()
        self.order_changed.emit()

    # 需保证 _relayout_subtree 仍存在（用于其他调用）
    # 由于 _rebuild_graphics 内部会调用 _do_rebuild_graphics，其中会清空并重建所有图形，所以安全。
    # 注意：_rebuild_graphics 设置 _layout_dirty，然后启动定时器。确保 _do_rebuild_graphics 会处理所有节点。
    # 在 _do_rebuild_graphics 中保留原有的全量重建逻辑（已存在），因此这里只调用 _rebuild_graphics() 。

        checked_ids = set(tag.full_id() for tag in checked_tags)

        # 移除取消勾选的标签
        to_remove = [fid for fid, node in self.node_map.items()
                     if not node.is_folder and fid not in checked_ids]
        for fid in to_remove:
            self._remove_node_graphics(fid)

        # 添加新勾选的标签
        for tag in checked_tags:
            fid = tag.full_id()
            if fid not in self.node_map:
                tag_node = SortNode(fid, is_folder=False, display_name=tag.display_name)
                parent_node = self._ensure_folder_path_by_tag(tag)
                parent_node.add_child(tag_node)
                self.node_map[fid] = tag_node
                self._add_node_graphics(tag_node)

        # 增量布局并更新所有边的路径
        self._relayout_subtree(self.sort_root, 0, 0)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        self.update_edges()
        self.order_changed.emit()

    def _ensure_folder_path_by_tag(self, tag):
        if tag.parent_id is None or tag.parent_id == '#root':
            return self.sort_root
        parent_id = tag.parent_id
        if parent_id in self.node_map:
            return self.node_map[parent_id]
        # 从 tag_manager 获取父标签信息并创建 SortNode
        parent_item = self.tag_manager.find_item_by_full_id(parent_id)
        if parent_item:
            folder_node = SortNode(parent_id, is_folder=True, display_name=parent_item.display_name)
            grand_parent = self._ensure_folder_path_by_id(parent_item.parent_id) if parent_item.parent_id and parent_item.parent_id != '#root' else self.sort_root
            grand_parent.add_child(folder_node)
            self.node_map[parent_id] = folder_node
            return folder_node
        return self.sort_root

    def _ensure_folder_path_by_id(self, folder_id):
        if folder_id is None or folder_id == '#root':
            return self.sort_root
        if folder_id in self.node_map:
            return self.node_map[folder_id]
        parent_item = self.tag_manager.find_item_by_full_id(folder_id)
        if parent_item:
            folder_node = SortNode(folder_id, is_folder=True, display_name=parent_item.display_name)
            grand_parent = self._ensure_folder_path_by_id(parent_item.parent_id) if parent_item.parent_id and parent_item.parent_id != '#root' else self.sort_root
            grand_parent.add_child(folder_node)
            self.node_map[folder_id] = folder_node
            return folder_node
        return self.sort_root

    def sync_from_checked(self, root_tag_item):
        checked_tags = []
        def collect(item):
            if not item.is_folder:
                if item.checked:
                    checked_tags.append(item)
            else:
                for child in item.children:
                    collect(child)
        collect(root_tag_item)
        self.sync_from_checked_list(checked_tags)

    # ---------- 图形节点增删 ----------
    def _add_node_graphics(self, node: SortNode):
        if node.graphic_item is not None:
            return
        item = SortNodeItem(node)
        self.scene.addItem(item)
        if node.parent and node.parent.graphic_item:
            edge = EdgeItem(node.parent.graphic_item, item)
            self.scene.addItem(edge)
        if node.is_folder:
            for child in node.children:
                if child.graphic_item:
                    edge = EdgeItem(item, child.graphic_item)
                    self.scene.addItem(edge)

    def _remove_node_graphics(self, fid):
        node = self.node_map.pop(fid, None)
        if node is None:
            return
        for edge in list(self.scene.items()):
            if isinstance(edge, EdgeItem):
                if edge.parent_item is node.graphic_item or edge.child_item is node.graphic_item:
                    self.scene.removeItem(edge)
        if node.graphic_item:
            self.scene.removeItem(node.graphic_item)
            node.graphic_item = None
        parent = node.parent
        if parent:
            parent.remove_child(node)
        while parent and parent.full_id != "root" and not parent.children:
            self._remove_node_graphics(parent.full_id)
            parent = parent.parent

    # ---------- 布局 ----------
    def _relayout_subtree(self, node: SortNode, depth: int, y_start: float) -> float:
        if node is self.sort_root:
            current_y = y_start
            for child in node.children:
                current_y = self._relayout_subtree(child, 0, current_y)
            return current_y

        leaf_column = self._get_max_folder_depth(self.sort_root)
        col = depth if node.is_folder else leaf_column
        x = 50 + col * LAYER_HORIZONTAL_GAP

        if node.is_folder and node.children:
            child_y = y_start
            for child in node.children:
                child_y = self._relayout_subtree(child, depth + 1, child_y)
            total_height = child_y - y_start
            folder_y = y_start + (total_height - NODE_HEIGHT) / 2.0
            if node.graphic_item:
                node.graphic_item.layer_x = x
                node.graphic_item.setPos(x, folder_y)
            return y_start + total_height
        else:
            if node.graphic_item:
                node.graphic_item.layer_x = x
                node.graphic_item.setPos(x, y_start)
            return y_start + NODE_HEIGHT + NODE_VERTICAL_GAP

    def _rebuild_graphics(self):
        """防抖后的重建标记，实际重建在 _do_rebuild_graphics"""
        if not self._layout_dirty:
            self._layout_dirty = True
            self._layout_timer.start(20)
            return

    def _do_rebuild_graphics(self):
        self._layout_dirty = False
        self.scene.clear()
        # 递归布局并创建图形项
        self._relayout_and_create_items(self.sort_root, 0, 0)
        self._create_edges()
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))

    def _relayout_and_create_items(self, node: SortNode, depth: int, y_start: float) -> float:
        if node is self.sort_root:
            current_y = y_start
            for child in node.children:
                current_y = self._relayout_and_create_items(child, 0, current_y)
            return current_y

        leaf_column = self._get_max_folder_depth(self.sort_root)
        col = depth if node.is_folder else leaf_column
        x = 50 + col * LAYER_HORIZONTAL_GAP

        item = SortNodeItem(node)
        self.scene.addItem(item)
        item.layer_x = x

        if node.is_folder and node.children:
            child_y = y_start
            for child in node.children:
                child_y = self._relayout_and_create_items(child, depth + 1, child_y)
            total_height = child_y - y_start
            folder_y = y_start + (total_height - NODE_HEIGHT) / 2.0
            item.setPos(x, folder_y)
            return y_start + total_height
        else:
            item.setPos(x, y_start)
            return y_start + NODE_HEIGHT + NODE_VERTICAL_GAP

    def _get_max_folder_depth(self, node, current_depth=0):
        if node is self.sort_root:
            max_d = 0
            for child in node.children:
                max_d = max(max_d, self._get_max_folder_depth(child, 0))
            return max_d
        elif node.is_folder:
            max_d = current_depth
            for child in node.children:
                max_d = max(max_d, self._get_max_folder_depth(child, current_depth + 1))
            return max_d
        else:
            return current_depth

    def _create_edges(self):
        for item in self.scene.items():
            if isinstance(item, SortNodeItem):
                node = item.node
                if node.parent and node.parent.graphic_item:
                    edge = EdgeItem(node.parent.graphic_item, item)
                    self.scene.addItem(edge)

    def update_edges(self):
        for item in self.scene.items():
            if isinstance(item, EdgeItem):
                item.update_path()

    # ---------- 上下文菜单 ----------
    def show_context_menu(self, pos):
        scene_pos = self.view.mapToScene(pos)
        items = self.scene.items(scene_pos)
        selected_node = None
        for it in items:
            if isinstance(it, SortNodeItem):
                selected_node = it.node
                break

        menu = QMenu(self)
        insert_random_action = QAction("插入随机槽", self)
        insert_random_action.triggered.connect(self.insert_random_slot)
        menu.addAction(insert_random_action)

        if selected_node:
            if selected_node.is_random_slot:
                edit_action = QAction("编辑随机槽", self)
                edit_action.triggered.connect(lambda: self.edit_random_slot(selected_node))
                menu.addAction(edit_action)
                test_action = QAction("试抽一次", self)
                test_action.triggered.connect(lambda: self.test_random_slot(selected_node))
                menu.addAction(test_action)
                delete_action = QAction("删除随机槽", self)
                delete_action.triggered.connect(lambda: self.delete_random_slot(selected_node))
                menu.addAction(delete_action)
            elif not selected_node.is_folder:
                detail_action = QAction("查看详情", self)
                detail_action.triggered.connect(lambda: self._show_detail(selected_node))
                menu.addAction(detail_action)
                weight_action = QAction("设置权重", self)
                weight_action.triggered.connect(lambda: self._set_weight(selected_node))
                menu.addAction(weight_action)
                menu.addSeparator()
                delete_action = QAction("移除", self)
                delete_action.triggered.connect(lambda: self.delete_tag_node(selected_node))
                menu.addAction(delete_action)
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def _show_detail(self, node):
        if self.tag_manager:
            tag = self.tag_manager.find_item_by_full_id(node.full_id)
            if tag:
                self.tag_detail_requested.emit(tag)

    def _set_weight(self, node):
        weight, ok = QInputDialog.getDouble(self, "设置权重", "输入权重值 (0.1-5.0):",
                                            node.weight, 0.1, 5.0, 1)
        if ok:
            node.weight = weight
            if node.graphic_item and node.graphic_item.weight_text:
                node.graphic_item.weight_text.setPlainText(f"w:{weight:.1f}")
            self.order_changed.emit()

    def delete_tag_node(self, node):
        if node.parent:
            node.parent.remove_child(node)
            if node.full_id in self.node_map:
                del self.node_map[node.full_id]
            self._rebuild_graphics()
            self.order_changed.emit()

    # ---------- 随机槽 ----------
    def insert_random_slot(self):
        if not self.tag_manager:
            return
        from tag_prompt_builder.ui.dialogs.random_slot_dialog import RandomSlotDialog
        dialog = RandomSlotDialog(self.tag_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            slot_id = f"random_slot_{uuid.uuid4().hex[:8]}"
            node = SortNode(slot_id, is_folder=False,
                            display_name="🎲 " + config.get("pool_name", "随机槽"),
                            is_random_slot=True, random_slot_config=config)
            self.sort_root.add_child(node)
            self.node_map[slot_id] = node
            self._rebuild_graphics()
            self.order_changed.emit()

    def edit_random_slot(self, node):
        from tag_prompt_builder.ui.dialogs.random_slot_dialog import RandomSlotDialog
        dialog = RandomSlotDialog(self.tag_manager, self, node.random_slot_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            node.random_slot_config = dialog.get_config()
            node.display_name = "🎲 " + node.random_slot_config.get("pool_name", "随机槽")
            if node.graphic_item:
                node.graphic_item.text.setPlainText(node.display_name)
            self.order_changed.emit()

    def test_random_slot(self, node):
        result = self.perform_random_slot(node)
        QMessageBox.information(self, "试抽结果", "抽取到的标签：\n" + ", ".join(tag.display_name for tag in result))

    def delete_random_slot(self, node):
        if node.parent:
            node.parent.remove_child(node)
            del self.node_map[node.full_id]
            self._rebuild_graphics()
            self.order_changed.emit()

    def perform_random_slot(self, slot_node: SortNode) -> List[TagItem]:
        return _perform_random_slot(slot_node, self.tag_manager)

    # ---------- 导出/导入 ----------
    def get_sort_structure(self):
        def export_node(node):
            if node.is_random_slot:
                return {"is_random_slot": True, "config": node.random_slot_config}
            if not node.is_folder:
                return {"full_id": node.full_id, "weight": node.weight, "display": node.display_name}
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
            if isinstance(item, dict):
                if "is_random_slot" in item:
                    config = item.get("config", {})
                    slot_id = f"random_slot_{uuid.uuid4().hex[:8]}"
                    display = "🎲 " + config.get("pool_name", "随机槽")
                    node = SortNode(slot_id, is_folder=False, display_name=display,
                                    is_random_slot=True, random_slot_config=config)
                    parent.add_child(node)
                    self.node_map[slot_id] = node
                elif "full_id" in item:
                    fid = item["full_id"]
                    tag = tag_manager.find_item_by_full_id(fid)
                    display = item.get("display", tag.display_name if tag else fid)
                    node = SortNode(fid, is_folder=False, display_name=display)
                    node.weight = item.get("weight", 1.0)
                    parent.add_child(node)
                    self.node_map[fid] = node
                else:
                    for fid, children in item.items():
                        folder_tag = tag_manager.find_item_by_full_id(fid)
                        folder_name = folder_tag.name if (folder_tag and folder_tag.is_folder) else fid
                        folder_node = SortNode(fid, is_folder=True, display_name=folder_name)
                        parent.add_child(folder_node)
                        self.node_map[fid] = folder_node
                        for child in children:
                            build_node(child, folder_node)
            elif isinstance(item, str):
                tag = tag_manager.find_item_by_full_id(item)
                display = tag.display_name if (tag and not tag.is_folder) else item
                node = SortNode(item, is_folder=False, display_name=display)
                parent.add_child(node)
                self.node_map[item] = node

        for top_item in structure:
            build_node(top_item, self.sort_root)
        self._rebuild_graphics()
        self.order_changed.emit()