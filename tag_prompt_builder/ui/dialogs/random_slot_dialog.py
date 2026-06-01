# tag_prompt_builder/ui/dialogs/random_slot_dialog.py
from PyQt6.QtWidgets import (QDialog, QFormLayout, QComboBox, QSpinBox, QCheckBox,
                             QDialogButtonBox, QMessageBox)
from tag_prompt_builder.managers.tag_manager import TagManager

class RandomSlotDialog(QDialog):
    def __init__(self, tag_manager: TagManager, parent=None, existing_config=None):
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.setWindowTitle("配置随机槽")
        layout = QFormLayout(self)

        self.pool_combo = QComboBox()
        pool_names = self.tag_manager.random_pool_manager.list_pool_names()
        self.pool_combo.addItems(pool_names)

        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(20)
        self.count_spin.setValue(1)

        self.dup_check = QCheckBox("允许重复抽取")
        self.dup_check.setChecked(False)

        layout.addRow("随机池:", self.pool_combo)
        layout.addRow("抽取数量:", self.count_spin)
        layout.addRow("", self.dup_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if existing_config:
            self.pool_combo.setCurrentText(existing_config.get("pool_name", ""))
            self.count_spin.setValue(existing_config.get("count", 1))
            self.dup_check.setChecked(existing_config.get("allow_duplicates", False))

    def get_config(self):
        return {
            "pool_name": self.pool_combo.currentText(),
            "count": self.count_spin.value(),
            "allow_duplicates": self.dup_check.isChecked()
        }