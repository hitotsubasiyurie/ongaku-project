from PySide6.QtWidgets import (QMessageBox, QScrollArea, QPlainTextEdit, 
                              QLabel, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt

class CheckMessageBox(QMessageBox):
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        
        # 创建滚动区域和文本编辑框
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        scroll.setWidget(text_edit)
        
        # 设置大小策略和最小尺寸
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setMinimumSize(400, 300)  # 设置最小尺寸
        
        # 获取布局并移除原有标签
        layout = self.layout()
        for child in self.children():
            if isinstance(child, QLabel) and child.text() == "":
                layout.removeWidget(child)
                child.deleteLater()
                break
        
        # 添加滚动区域到布局（占据原标签位置）
        layout.addWidget(scroll, 0, 1, 1, layout.columnCount()-1)
        
        # 调整对话框大小策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

# 使用示例
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    
    long_text = "\n".join([f"这是第 {i} 行文本..." for i in range(1, 101)])
    
    box = CheckMessageBox("长文本消息", long_text)
    box.setStandardButtons(QMessageBox.Ok)
    box.exec()
    
    app.exec()