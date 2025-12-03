# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import numpy as np


class ImageWindow(QMainWindow):
    """
    图像显示窗口，用于显示HDF5文件中的图像数据
    支持自由拖动和调整大小
    """
    
    def __init__(self, title: str, parent=None):
        """
        初始化图像窗口
        
        Args:
            title: 窗口标题
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.title = title
        self.setWindowTitle(title)
        self.setMinimumSize(320, 240)
        
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建布局
        self.layout = QVBoxLayout(self.central_widget)
        
        # 创建图像标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)
        
        # 设置窗口属性，使其可以自由拖动
        self.setWindowFlags(Qt.Window)
    
    def set_image(self, image: np.ndarray):
        """
        设置要显示的图像
        
        Args:
            image: 图像数据，格式为(height, width, channels)的numpy数组
        """
        if image is None:
            self.image_label.clear()
            return
            
        # 将numpy数组转换为QImage
        height, width, channels = image.shape
        bytes_per_line = channels * width
        
        if channels == 3:
            format = QImage.Format_RGB888
        elif channels == 4:
            format = QImage.Format_RGBA8888
        else:
            raise ValueError(f"不支持的通道数: {channels}")
        
        # 确保图像数据连续
        if not image.flags['C_CONTIGUOUS']:
            image = np.ascontiguousarray(image)
            
        # 创建QImage和QPixmap
        q_image = QImage(image.data, width, height, bytes_per_line, format)
        pixmap = QPixmap.fromImage(q_image)
        
        # 设置图像标签
        self.image_label.setPixmap(pixmap)
        self.image_label.setMinimumSize(1, 1)
        
        # 调整大小以适应图像
        self.adjustSize()
    
    def clear(self):
        """清除图像"""
        self.image_label.clear()
    
    def closeEvent(self, event):
        """
        重写关闭事件处理函数
        
        Args:
            event: 关闭事件
        """
        # 在这里可以添加关闭窗口时的处理逻辑
        super().closeEvent(event) 