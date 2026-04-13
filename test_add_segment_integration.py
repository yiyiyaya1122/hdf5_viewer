#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试在现有时间轴上添加区间的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt
from src.ui.timeline_widget import TimelineWidget

class AddSegmentIntegrationTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("增加区间集成测试")
        self.setGeometry(100, 100, 1400, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 创建说明标签
        info_label = QLabel("切分区间集成测试说明：\n1. 点击'创建测试时间轴'创建包含多个区间的时间轴\n2. 调整滑块到区间内部位置\n3. 点击'切分区间'按钮测试切分功能\n4. 观察原区间如何被切分成两个新区间")
        info_label.setStyleSheet("font-size: 12px; padding: 10px; background-color: #e8f4f8; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # 创建时间轴控件
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.set_total_frames(200)  # 设置总帧数为200
        layout.addWidget(self.timeline_widget)
        
        # 创建控制面板
        control_layout = QHBoxLayout()
        
        # 创建测试时间轴按钮
        create_button = QPushButton("创建测试时间轴")
        create_button.clicked.connect(self.create_test_timeline)
        control_layout.addWidget(create_button)
        
        # 切分区间按钮
        add_button = QPushButton("切分区间")
        add_button.clicked.connect(self.add_segment)
        control_layout.addWidget(add_button)
        
        # 清除所有按钮
        clear_button = QPushButton("清除所有")
        clear_button.clicked.connect(self.clear_all)
        control_layout.addWidget(clear_button)
        
        # 当前帧信息
        self.frame_info_label = QLabel("当前帧: 0")
        control_layout.addWidget(self.frame_info_label)
        
        layout.addLayout(control_layout)
        
        # 创建日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        layout.addWidget(self.log_text)
        
        # 连接信号
        self.timeline_widget.frameChanged.connect(self.on_frame_changed)
        
        # 重定向print输出到日志区域
        self.original_print = print
        print = self.log_print
        
        # 创建初始测试数据
        self.create_test_timeline()
    
    def log_print(self, *args, **kwargs):
        """将print输出重定向到日志区域"""
        text = " ".join(str(arg) for arg in args)
        self.log_text.append(text)
        self.original_print(*args, **kwargs)
    
    def create_test_timeline(self):
        """创建测试时间轴"""
        # 清除现有区间
        self.timeline_widget.clear_segments()
        
        # 创建一个annotation时间轴并添加一些区间
        self.timeline_widget.add_segment("annotation", 20, 40)
        self.timeline_widget.add_segment("annotation", 60, 80)
        self.timeline_widget.add_segment("annotation", 100, 120)
        self.timeline_widget.add_segment("annotation", 140, 160)
        
        print("=== 创建了测试时间轴 ===")
        print("现有区间:")
        print("- annotation: 20-40")
        print("- annotation: 60-80") 
        print("- annotation: 100-120")
        print("- annotation: 140-160")
        print("间隙位置:")
        print("- 0-20 (开头)")
        print("- 40-60 (第一个间隙)")
        print("- 80-100 (第二个间隙)")
        print("- 120-140 (第三个间隙)")
        print("- 160-200 (结尾)")
        print("现在可以测试切分区间功能：")
        print("1. 在区间内部切分：应该将原区间切分成两个新区间")
        print("2. 在区间边界切分：应该提示无法切分")
        print("==========================")
    
    def add_segment(self):
        """切分区间"""
        current_frame = self.timeline_widget.get_current_frame()
        print(f"在当前帧 {current_frame} 位置切分区间")
        self.timeline_widget.split_segment_at_current()
    
    def clear_all(self):
        """清除所有区间"""
        self.timeline_widget.clear_segments()
        print("已清除所有区间")
    
    def on_frame_changed(self, frame):
        """处理帧变化"""
        self.frame_info_label.setText(f"当前帧: {frame}")

def main():
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = AddSegmentIntegrationTestWindow()
    window.show()
    
    print("=== 切分区间集成测试 ===")
    print("测试目标：")
    print("- 新区间直接添加到现有时间轴上")
    print("- 智能避免与现有区间重叠")
    print("- 优先在间隙中插入新区间")
    print("- 自动更新边界信息")
    print("========================")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 