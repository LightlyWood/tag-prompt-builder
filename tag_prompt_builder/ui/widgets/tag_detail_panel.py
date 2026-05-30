# ui/widgets/tag_detail_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from tag_prompt_builder.models.tag_item import TagItem

class TagDetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.current_tag = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.title_label = QLabel("标签详情")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-weight: bold;")
        self.scroll_layout.addWidget(self.name_label)

        self.wiki_link = QLabel()
        self.wiki_link.setOpenExternalLinks(True)
        self.wiki_link.setWordWrap(True)
        self.wiki_link.setTextFormat(Qt.TextFormat.RichText)  # 确保 HTML 链接生效
        self.scroll_layout.addWidget(self.wiki_link)

        self.aliases_label = QLabel()
        self.aliases_label.setWordWrap(True)
        self.aliases_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.scroll_layout.addWidget(self.aliases_label)

        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.scroll_layout.addWidget(self.desc_label)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.clear()

    def show_tag_detail(self, tag: TagItem):
        self.current_tag = tag
        self.name_label.setText(f"中文名：{tag.display_name}\n英文名：{tag.name}")

        if tag.wiki_url:
            self.wiki_link.setText(f'<a href="{tag.wiki_url}">打开 Danbooru Wiki</a>')
        else:
            self.wiki_link.setText("无 Wiki 链接")

        if tag.aliases:
            aliases_text = "别称：" + "、".join(tag.aliases)
        else:
            aliases_text = "别称：无"
        self.aliases_label.setText(aliases_text)

        if tag.description:
            self.desc_label.setText(f"简介：\n{tag.description}")
        else:
            self.desc_label.setText("简介：无")

    def clear(self):
        self.name_label.setText("点击标签查看详情")
        self.wiki_link.setText("")
        self.aliases_label.setText("")
        self.desc_label.setText("")