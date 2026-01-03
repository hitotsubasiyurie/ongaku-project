import sys
import time
from PySide6.QtWidgets import QApplication, QProgressDialog
from PySide6.QtCore import Qt


if __name__ == "__main__":
    app = QApplication(sys.argv)

    dlg = QProgressDialog("", "取消", 0, 100)
    dlg.setWindowTitle("加载数据")
    dlg.setMinimumDuration(0)
    dlg.show()

    for i in range(101):
        time.sleep(0.03)
        dlg.setValue(i)
        QApplication.processEvents()

        if dlg.wasCanceled():
            dlg.close()
            app.quit()
            sys.exit(app.exec())

    dlg.close()

    # 其他的业务逻辑
    # xxx

    sys.exit(app.exec())
