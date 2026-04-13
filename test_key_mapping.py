#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试键名映射功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from src.ui.timeline_widget import TimelineWidget

class KeyMappingTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("键名映射测试")
        self.setGeometry(100, 100, 1200, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 创建说明标签
        info_label = QLabel("键名映射测试说明：\n1. 观察时间轴标签是否显示为中文\n2. 'annotation'应该显示为'标注标签轨道:'\n3. 'language'应该显示为'语言标签轨道:'\n4. 其他键名保持原样")
        info_label.setStyleSheet("font-size: 12px; padding: 10px; background-color: #f0f8ff; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # 创建时间轴控件
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.set_total_frames(100)  # 设置总帧数为100
        layout.addWidget(self.timeline_widget)
        
        # 创建测试按钮
        button_layout = QHBoxLayout()
        
        # 测试annotation时间轴
        test_annotation_button = QPushButton("测试Annotation时间轴")
        test_annotation_button.clicked.connect(self.test_annotation_timeline)
        button_layout.addWidget(test_annotation_button)
        
        # 测试language时间轴
        test_language_button = QPushButton("测试Language时间轴")
        test_language_button.clicked.connect(self.test_language_timeline)
        button_layout.addWidget(test_language_button)
        
        # 测试普通时间轴
        test_normal_button = QPushButton("测试普通时间轴")
        test_normal_button.clicked.connect(self.test_normal_timeline)
        button_layout.addWidget(test_normal_button)
        
        # 清除按钮
        clear_button = QPushButton("清除所有")
        clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_button)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.timeline_widget.frameChanged.connect(self.on_frame_changed)
        
        # 测试键名映射功能
        self.test_key_mapping()
    
    def test_key_mapping(self):
        """测试键名映射功能"""
        print("=== 键名映射测试 ===")
        print(f"annotation -> {self.timeline_widget.get_key_display_name('annotation')}")
        print(f"language -> {self.timeline_widget.get_key_display_name('language')}")
        print(f"segment -> {self.timeline_widget.get_key_display_name('segment')}")
        print(f"unknown -> {self.timeline_widget.get_key_display_name('unknown')}")
        print("==================")
    
    def test_annotation_timeline(self):
        """测试annotation时间轴"""
        # 添加annotation时间轴和区间
        self.timeline_widget.add_segment("annotation", 10, 30)
        self.timeline_widget.add_segment("annotation", 40, 60)
        print("添加了annotation时间轴和区间")
    
    def test_language_timeline(self):
        """测试language时间轴"""
        # 添加language时间轴和区间
        self.timeline_widget.add_segment("language", 15, 35)
        self.timeline_widget.add_segment("language", 45, 65)
        print("添加了language时间轴和区间")
    
    def test_normal_timeline(self):
        """测试普通时间轴"""
        # 添加普通时间轴和区间
        self.timeline_widget.add_segment("test_key", 20, 40)
        self.timeline_widget.add_segment("test_key", 50, 70)
        print("添加了普通时间轴和区间")
    
    def clear_all(self):
        """清除所有区间"""
        self.timeline_widget.clear_segments()
        print("已清除所有区间")
    
    def on_frame_changed(self, frame):
        """处理帧变化"""
        pass

def main():
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = KeyMappingTestWindow()
    window.show()
    
    print("=== 键名映射功能测试 ===")
    print("测试目标：")
    print("- annotation显示为'标注标签轨道:'")
    print("- language显示为'语言标签轨道:'")
    print("- segment显示为'区间标签轨道:'")
    print("- 其他键名保持原样")
    print("========================")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 