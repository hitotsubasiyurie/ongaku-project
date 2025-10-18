import sys
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont

class ShadowTextWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("阴影文字绘制示例")
        self.resize(400, 200)
        
        # 设置文字内容
        self.text = "阴影文字"
        
        # 设置字体
        self.font = QFont("Arial", 36, QFont.Bold)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
        # 获取窗口尺寸
        rect = self.rect()
        
        # 设置字体
        painter.setFont(self.font)
        
        # 计算文字位置（居中）
        text_rect = painter.boundingRect(rect, Qt.AlignCenter, self.text)
        x = (rect.width() - text_rect.width()) / 2
        y = (rect.height() + text_rect.height()) / 2
        
        # 绘制阴影
        shadow_color = QColor(100, 100, 100, 150)  # 半透明灰色阴影
        painter.setPen(shadow_color)
        painter.drawText(int(x + 3), int(y + 3), self.text)  # 阴影偏移3像素
        
        # 绘制前景文字
        text_color = QColor(255, 255, 255)  # 白色文字
        painter.setPen(text_color)
        painter.drawText(int(x), int(y), self.text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置窗口背景色为深色，以便更好地显示阴影效果
    app.setStyleSheet("QWidget { background-color: #2b2b2b; }")
    
    widget = ShadowTextWidget()
    widget.show()
    
    sys.exit(app.exec())