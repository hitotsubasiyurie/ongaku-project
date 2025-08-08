from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QBrush, QLinearGradient
import sys

class ProgressDelegate(QStyledItemDelegate):
    def __init__(self, progress_values, parent=None):
        super().__init__(parent)
        self.progress_values = progress_values
    
    def paint(self, painter, option, index):
        # Get progress value for this item
        progress = self.progress_values[index.row()]
        
        if 0 <= progress <= 1:
            # Set up colors - gradient from start to end
            start_color = QColor(100, 200, 100)  # Green
            end_color = QColor(200, 200, 200)     # Gray
            
            # Create a gradient that fills based on progress
            rect = option.rect
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
            gradient.setColorAt(0, start_color)
            gradient.setColorAt(progress, start_color)
            gradient.setColorAt(min(progress + 0.001, 1.0), end_color)
            
            # Save painter state
            painter.save()
            
            # Clip the painting area to only paint the background
            clip_rect = QRect(rect)
            painter.setClipRect(clip_rect)
            
            # Fill with gradient
            painter.fillRect(rect, QBrush(gradient))
            
            # Restore painter state
            painter.restore()
        super().paint(painter, option, index)

# Example usage
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Sample data
    strings = ["Task 1", "Task 2", "Task 3", "Task 4", "Task 5"]
    progress = [0.25, 0.5, 0.75, 0.9, 0.1]  # Progress values between 0 and 1
    
    # Create and show the widget
    widget = QListWidget()
    widget.addItems(list(zip(strings, progress)))
    widget.setItemDelegate(ProgressDelegate(progress))
    widget.resize(300, 200)
    widget.show()
    
    sys.exit(app.exec())