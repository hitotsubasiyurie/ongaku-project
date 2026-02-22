import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import QObject, Signal

# 定义一个流对象，用于捕获输出
class StreamToWrapper(QObject):
    text_written = Signal(str)

    def write(self, text):
        self.text_written.emit(str(text))
    
    def flush(self): # 必须实现，防止报错
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.text_area = QTextEdit()
        self.btn = QPushButton("运行逻辑函数")
        
        layout = QVBoxLayout()
        layout.addWidget(self.text_area)
        layout.addWidget(self.btn)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 重定向 stdout
        self.output_wrapper = StreamToWrapper()
        self.output_wrapper.text_written.connect(self.append_text)
        sys.stdout = self.output_wrapper

        self.btn.clicked.connect(self.my_logic_function)

    def append_text(self, text):
        self.text_area.insertPlainText(text)

    def my_logic_function(self):
        # 这里的 print 会自动显示在 UI 上
        print("正在处理数据...")
        print("处理完成！")

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()