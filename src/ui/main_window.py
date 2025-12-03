# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeyEvent, QImage, QPixmap
import os
import numpy as np

from src.core.hdf5_model import HDF5Model
from src.ui.image_window import ImageWindow
from src.ui.timeline_widget import TimelineWidget
from src.core.phrase_library import PhraseLibrary
from src.ui.phrase_selection_dialog import PhraseSelectionDialog


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("HDF5 Annotation Tool")
        self.resize(1200, 800)
        
        # 设置样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 12px;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # 初始化各种变量
        # 初始化图像窗口字典
        self.image_windows = {}
        
        # 初始化HDF5模型
        self.hdf5_model = None
        
        # 存储当前打开的文件夹路径
        self.current_folder = None
        
        # 存储文件夹中的所有HDF5文件列表
        self.hdf5_files = []
        
        # 当前打开的文件在列表中的索引
        self.current_file_index = -1
        
        # 图像展示区滚动布局
        self.images_scroll_area = None
        self.images_grid_layout = None
        
        # 当前选中的时间窗口
        self.selected_time_window = None

        # 当前文件路径
        self.current_file_path = None

        # 每帧分数映射 (从 data/<basename>.json 加载)
        self.frame_scores = {}
        self.scores_loaded = False
        self.scores_source = None

        # 初始化短语库
        self.phrase_library = PhraseLibrary()
        self.selected_window_index = None  # 当前选中的时间窗口索引

        # 当前加载的标注字段
        self.current_annotation_field = None

        # 初始化数据显示标签
        self.data_value_label = QLabel("请选择数据键和帧...")
        self.data_value_label.setWordWrap(True)
        self.data_value_label.setStyleSheet("""
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            min-height: 60px;
        """)
        
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建布局
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15) # 设置边距
        self.main_layout.setSpacing(15) # 设置间距
        
        # 创建左侧控制面板
        self.create_left_panel()
        
        # 创建右侧显示和控制区域
        self.create_right_panel()
        
        # 创建底部状态栏
        self.statusBar().showMessage("准备就绪")
        
        # 移除播放定时器 - 播放控制已移到TimelineWidget中
        
        # 添加窗口大小变化的延迟更新定时器
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize_finished)
        
        # 移除时间轴的多选信号连接 - 不再需要
    
    def create_left_panel(self):
        """创建左侧控制面板"""
        # 创建左侧面板容器
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建文件控制区域
        file_group = QWidget()
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(5, 5, 5, 10)
        
        # 添加文件打开按钮
        file_open_layout = QHBoxLayout()
        self.open_file_btn = QPushButton("打开文件")
        self.open_file_btn.clicked.connect(self.open_file)
        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.clicked.connect(self.open_folder)
        file_open_layout.addWidget(self.open_file_btn)
        file_open_layout.addWidget(self.open_folder_btn)
        file_layout.addLayout(file_open_layout)
        
        # 添加文件列表
        file_list_label = QLabel("文件列表:")
        file_list_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        file_layout.addWidget(file_list_label)
        
        self.file_list_widget = QListWidget()
        self.file_list_widget.setMinimumHeight(150)
        self.file_list_widget.itemClicked.connect(self.on_file_selected)
        file_layout.addWidget(self.file_list_widget)
        
        # 添加文件导航按钮
        file_nav_layout = QHBoxLayout()
        self.prev_file_btn = QPushButton("上一个文件")
        self.prev_file_btn.clicked.connect(self.prev_file)
        self.prev_file_btn.setEnabled(False)
        self.next_file_btn = QPushButton("下一个文件")
        self.next_file_btn.clicked.connect(self.next_file)
        self.next_file_btn.setEnabled(False)
        file_nav_layout.addWidget(self.prev_file_btn)
        file_nav_layout.addWidget(self.next_file_btn)
        file_layout.addLayout(file_nav_layout)
        
        left_layout.addWidget(file_group)
        
        # 移除Language编辑控制区域 - 根据需求简化界面
        
        # 移除批量设置区域 - 根据需求简化界面
        
        # 创建数据集显示区域（支持字段选择和加载）
        data_group = QWidget()
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(5, 5, 5, 10)

        # 添加其他数据集显示（除了图片外的字段）
        data_label = QLabel("数据字段:")
        data_label.setStyleSheet("font-weight: bold;")
        data_layout.addWidget(data_label)

        self.data_list_widget = QListWidget()
        self.data_list_widget.setMinimumHeight(120)
        self.data_list_widget.setSelectionMode(QListWidget.SingleSelection)  # 启用单选
        self.data_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                color: #333;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        data_layout.addWidget(self.data_list_widget)

        # 添加字段选择控制按钮
        field_control_layout = QHBoxLayout()
        self.load_field_button = QPushButton("加载选中字段")
        self.load_field_button.setEnabled(False)
        self.load_field_button.clicked.connect(self.load_selected_field)
        self.load_field_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        field_control_layout.addWidget(self.load_field_button)
        data_layout.addLayout(field_control_layout)

        # 添加字段管理按钮
        field_manage_layout = QHBoxLayout()

        self.create_field_button = QPushButton("创建新字段")
        self.create_field_button.setEnabled(False)
        self.create_field_button.clicked.connect(self.create_new_annotation_field)
        self.create_field_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        self.delete_field_button = QPushButton("删除选中字段")
        self.delete_field_button.setEnabled(False)
        self.delete_field_button.clicked.connect(self.delete_selected_field)
        self.delete_field_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        field_manage_layout.addWidget(self.create_field_button)
        field_manage_layout.addWidget(self.delete_field_button)
        data_layout.addLayout(field_manage_layout)

        # 显示当前加载的字段
        self.current_field_label = QLabel("当前字段: 未选择")
        self.current_field_label.setStyleSheet("""
            color: #666;
            font-style: italic;
            padding: 4px;
            background-color: #f9f9f9;
            border-radius: 3px;
        """)
        data_layout.addWidget(self.current_field_label)

        # 连接选择变化事件
        self.data_list_widget.itemSelectionChanged.connect(self.on_field_selection_changed)

        left_layout.addWidget(data_group)

        # 添加保存功能区域
        save_group = QWidget()
        save_layout = QVBoxLayout(save_group)
        save_layout.setContentsMargins(5, 5, 5, 10)

        # 保存标题
        save_title = QLabel("保存标注:")
        save_title.setStyleSheet("font-weight: bold; color: #ff6b35; font-size: 13px;")
        save_layout.addWidget(save_title)

        # 保存标注数据按钮（保存到HDF5）
        self.save_annotations_btn = QPushButton("保存标注数据到HDF5")
        self.save_annotations_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.save_annotations_btn.clicked.connect(self.save_annotations)
        self.save_annotations_btn.setEnabled(False)
        save_layout.addWidget(self.save_annotations_btn)

        # 保存为JSON按钮（新增）
        self.save_json_btn = QPushButton("保存标注数据为JSON")
        self.save_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.save_json_btn.clicked.connect(self.save_annotations_as_json)
        self.save_json_btn.setEnabled(False)
        save_layout.addWidget(self.save_json_btn)

        left_layout.addWidget(save_group)
        
        # 添加到主布局
        self.main_layout.addWidget(left_panel)
    
    def create_right_panel(self):
        """创建右侧显示和控制区域"""
        # 创建右侧面板容器
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)  # 减少间距
        
        # 创建当前subtask信息显示区域
        current_subtask_layout = QVBoxLayout()
        self.subtask_title = QLabel("当前Subtask信息:")
        self.subtask_title.setStyleSheet("font-weight: bold; color: #3c8b4b; font-size: 13px;")
        current_subtask_layout.addWidget(self.subtask_title)

        # 添加当前subtask信息标签
        self.subtask_info_label = QLabel("未选中任何时间窗口")
        self.subtask_info_label.setWordWrap(True)
        self.subtask_info_label.setStyleSheet("""
            background-color: #f0f8ff;
            border: 1px solid #d0e0f0;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
            min-height: 40px;
            color: #333;
        """)
        # 添加鼠标点击事件
        self.subtask_info_label.mousePressEvent = self.on_subtask_info_clicked
        current_subtask_layout.addWidget(self.subtask_info_label)

        # 添加编辑按钮
        edit_button_layout = QHBoxLayout()
        self.edit_annotation_btn = QPushButton("编辑标注")
        self.edit_annotation_btn.setEnabled(False)
        self.edit_annotation_btn.clicked.connect(self.edit_current_annotation)
        self.edit_annotation_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        edit_button_layout.addWidget(self.edit_annotation_btn)
        edit_button_layout.addStretch()
        current_subtask_layout.addLayout(edit_button_layout)
        right_layout.addLayout(current_subtask_layout)
        
        # 创建图像显示区域
        images_label = QLabel("图像显示区域:")
        images_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        right_layout.addWidget(images_label)
        
        # 创建滚动区域用于显示图像
        self.images_scroll_area = QScrollArea()
        self.images_scroll_area.setWidgetResizable(True)
        self.images_scroll_area.setMinimumHeight(300)  # 减少最小高度
        
        # 创建容器和网格布局用于放置图像
        images_container = QWidget()
        self.images_grid_layout = QGridLayout(images_container)
        self.images_grid_layout.setContentsMargins(5, 5, 5, 5)
        self.images_grid_layout.setSpacing(10)
        
        self.images_scroll_area.setWidget(images_container)
        # 让图像显示区域占据大部分空间
        right_layout.addWidget(self.images_scroll_area, 3)  # 权重为3
        
        # 创建时间轴和控制区域
        timeline_label = QLabel("时间轴:")
        timeline_label.setStyleSheet("font-weight: bold; margin-top: 5px; margin-bottom: 3px;")
        right_layout.addWidget(timeline_label)
        
        # 创建时间轴小部件
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.frameChanged.connect(self.on_frame_changed)
        self.timeline_widget.windowAdded.connect(self.on_window_added)
        # 设置时间轴的最大高度，让它不占用太多空间
        self.timeline_widget.setMaximumHeight(200)
        self.timeline_widget.setMinimumHeight(120)
        
        # 让时间轴占据较少空间
        right_layout.addWidget(self.timeline_widget, 1)  # 权重为1
        
        # 移除控制按钮区域，因为控制功能已经集成到时间轴组件中
        
        # 添加到主布局
        self.main_layout.addWidget(right_panel, 1)
    
    def open_file(self):
        """打开单个HDF5文件"""
        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开HDF5文件", "", "HDF5文件 (*.hdf5 *.h5);;所有文件 (*)"
        )
        
        if file_path:
            # 清除当前文件夹和文件列表状态
            self.current_folder = None
            self.hdf5_files = []
            self.current_file_index = -1
            self.file_list_widget.clear()
            
            # 单文件模式，无需特殊处理
            
            self.load_hdf5_file(file_path)
    
    def open_folder(self):
        """打开文件夹并加载其中的所有HDF5文件"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择包含HDF5文件的文件夹")
        
        if folder_path:
            self.current_folder = folder_path
            self.load_folder_files(folder_path)
    
    def natural_sort_key(self, file_name):
        """
        实现自然排序的键函数，用于对文件名进行排序
        这将同时考虑字母和数字的混合排序，例如 "file1", "file2", "file10" 会正确排序
        同时也能处理形如 "file_A_001", "file_B_002" 这样的混合模式
        
        Args:
            file_name: 文件名
            
        Returns:
            排序键
        """
        import re
        
        # 将文件名拆分为文本和数字部分
        def atoi(text):
            return int(text) if text.isdigit() else text
        
        # 将每个数字和非数字部分分开，并转换数字为整数
        parts = re.split(r'(\d+)', file_name)
        return [atoi(part) for part in parts]
        
    def load_folder_files(self, folder_path):
        """加载文件夹中的所有HDF5文件"""
        # 清除之前的文件列表
        self.file_list_widget.clear()
        self.hdf5_files = []
        
        # 查找文件夹中的所有HDF5文件
        file_names = []
        for file_name in os.listdir(folder_path):
            if (file_name.endswith(('.hdf5', '.h5'))) and (not file_name.startswith('.')):
                file_names.append(file_name)
        
        # 使用自然排序对文件名进行排序
        file_names.sort(key=self.natural_sort_key)
        print(f"排序后的文件列表: {file_names}")
        
        # 添加排序后的文件到列表
        for file_name in file_names:
            file_path = os.path.join(folder_path, file_name)
            self.hdf5_files.append(file_path)
            
            # 添加到列表小部件
            item = QListWidgetItem(file_name)
            item.setToolTip(file_path)
            self.file_list_widget.addItem(item)
        
        # 更新状态栏信息
        if self.hdf5_files:
            self.statusBar().showMessage(f"找到 {len(self.hdf5_files)} 个HDF5文件")
            
            # 文件夹模式，无需特殊处理
            
            # 默认加载第一个文件
            self.current_file_index = 0
            self.file_list_widget.setCurrentRow(0)
            self.load_hdf5_file(self.hdf5_files[0])
            
            # 启用文件导航按钮
            self.update_file_navigation_buttons()
        else:
            self.statusBar().showMessage("文件夹中没有找到HDF5文件")
            # 无HDF5文件，无需特殊处理
    
    def load_hdf5_file(self, file_path):
        """加载HDF5文件"""
        try:
            # 保存当前文件路径
            self.current_file_path = file_path

            # 清理旧的时间轴数据和字段选择状态
            print("清理旧的时间轴数据和字段选择状态")

            # 重置字段选择状态
            self.current_annotation_field = None
            self.current_field_label.setText("当前字段: 未选择")
            self.load_field_button.setEnabled(False)
            self.delete_field_button.setEnabled(False)
            self.create_field_button.setEnabled(False)

            # 清除字段选择
            self.data_list_widget.clearSelection()

            # 清理时间轴标注数据
            self.timeline_widget.time_windows.clear()

            # 清除时间轴上的所有annotation段
            for timeline in self.timeline_widget.timelines:
                timeline.segments = [seg for seg in timeline.segments if seg.key != "annotation"]

            # 关闭之前的模型
            if self.hdf5_model:
                self.hdf5_model.close()

            # 关闭所有图像窗口
            for window in self.image_windows.values():
                window.close()
            self.image_windows = {}

            # 创建新的HDF5模型
            self.hdf5_model = HDF5Model(file_path)

            # 更新UI
            self.update_ui_with_model()

            # 更新状态栏
            file_name = os.path.basename(file_path)
            compression_status = "压缩" if self.hdf5_model.is_compressed() else "非压缩"
            self.statusBar().showMessage(f"已加载文件: {file_name} ({compression_status}数据集)")
            self.setWindowTitle(f"HDF5文件可视化与标注工具 - {file_name}")

            # 初始化时间轴
            print("初始化时间轴")

            # 默认显示所有图像
            # 尝试加载与该HDF5同名的JSON分数文件（优先 repo/data）
            try:
                self.load_frame_scores_for_current_file()
            except Exception:
                # 加载失败不要中断流程
                pass

            self.display_all_images()

            # 确保状态栏显示当前帧与分数
            try:
                current_frame = self.timeline_widget.get_current_frame()
                self.on_frame_changed(current_frame)
            except Exception:
                pass

            # 注意：不再自动加载标注数据，需要用户手动选择字段后加载
            print("HDF5文件加载完成，请选择需要标注的字段")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载HDF5文件: {e}")
            self.statusBar().showMessage("文件加载失败")
    
    # 移除restore_selected_keys方法 - 不再需要
    
    def on_file_selected(self, item):
        """当文件列表中的文件被选中时的处理函数"""
        file_path = item.toolTip()
        index = self.file_list_widget.row(item)
        
        # 更新当前文件索引
        self.current_file_index = index
        
        # 加载选中的文件
        self.load_hdf5_file(file_path)
        
        # 更新文件导航按钮状态
        self.update_file_navigation_buttons()
    
    def prev_file(self):
        """加载上一个文件"""
        if self.current_file_index > 0:
            self.current_file_index -= 1
            self.file_list_widget.setCurrentRow(self.current_file_index)
            self.load_hdf5_file(self.hdf5_files[self.current_file_index])
            self.update_file_navigation_buttons()
    
    def next_file(self):
        """加载下一个文件"""
        if self.current_file_index < len(self.hdf5_files) - 1:
            self.current_file_index += 1
            self.file_list_widget.setCurrentRow(self.current_file_index)
            self.load_hdf5_file(self.hdf5_files[self.current_file_index])
            self.update_file_navigation_buttons()
    
    def update_file_navigation_buttons(self):
        """更新文件导航按钮的启用状态"""
        self.prev_file_btn.setEnabled(self.current_file_index > 0)
        self.next_file_btn.setEnabled(self.current_file_index < len(self.hdf5_files) - 1)
    
    def display_all_images(self):
        """显示当前帧的所有图像"""
        if not self.hdf5_model or self.images_grid_layout is None:
            return
        
        # 清除之前的图像
        self.clear_image_grid()
        
        # 获取所有图像键
        image_keys = self.hdf5_model.get_image_keys()
        
        if not image_keys:
            return
        
        # 获取当前帧
        current_frame = self.timeline_widget.get_current_frame()
        
        # 获取滚动区域的可用大小
        scroll_area_size = self.images_scroll_area.size()
        available_width = scroll_area_size.width() - 40  # 减去滚动条和边距
        available_height = scroll_area_size.height() - 40
        
        # 水平并排显示所有图像
        num_images = len(image_keys)
        
        # 计算每个图像的最大尺寸（水平排列）
        max_image_width = max(200, (available_width - num_images * 15) // num_images)  # 最小200像素
        max_image_height = max(150, available_height - 50)  # 减去标题高度
        
        # 为每个图像键创建并显示图像（水平排列）
        for i, key in enumerate(image_keys):
            # 获取图像数据
            image_data = self.hdf5_model.get_image(key, current_frame)
            
            if image_data is not None:
                # 创建图像容器
                image_container = QWidget()
                image_layout = QVBoxLayout(image_container)
                image_layout.setContentsMargins(5, 5, 5, 5)
                image_layout.setSpacing(5)
                
                # 创建图像标题标签
                title_label = QLabel(key)
                title_label.setAlignment(Qt.AlignCenter)
                title_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
                title_label.setMaximumHeight(25)
                title_label.setMinimumHeight(25)
                
                # 创建图像标签
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setMinimumSize(max_image_width, max_image_height)
                image_label.setMaximumSize(max_image_width, max_image_height)
                image_label.setStyleSheet("""
                    QLabel {
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        background-color: white;
                    }
                """)
                
                # 添加到布局
                image_layout.addWidget(title_label)
                image_layout.addWidget(image_label, 1)  # 让图像标签占据剩余空间
                
                # 将图像容器添加到网格（水平排列，都在第0行）
                self.images_grid_layout.addWidget(image_container, 0, i)
                
                # 显示图像
                self.display_image_in_label(image_data, image_label)
        
        # 设置网格布局的拉伸因子，让所有列均匀分布
        for col in range(num_images):
            self.images_grid_layout.setColumnStretch(col, 1)
        
        # 确保只有一行，并让这一行占据所有可用空间
        self.images_grid_layout.setRowStretch(0, 1)
    
    def clear_image_grid(self):
        """清除图像网格中的所有图像"""
        # 检查images_grid_layout是否已初始化
        if self.images_grid_layout is None:
            return
            
        # 移除网格布局中的所有部件
        while self.images_grid_layout.count():
            item = self.images_grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
    
    def display_image_in_label(self, image_data, label):
        """在标签中显示图像"""
        if image_data is None:
            label.clear()
            label.setText("无图像数据")
            label.setStyleSheet(label.styleSheet() + "color: #999;")
            return

        # 检查图像数据的维度
        if len(image_data.shape) != 3:
            label.clear()
            label.setText(f"无效的图像数据\n维度: {image_data.shape}")
            label.setStyleSheet(label.styleSheet() + "color: #ff6666;")
            return

        # 将numpy数组转换为QImage
        height, width, channels = image_data.shape
        bytes_per_line = channels * width
        
        if channels == 3:
            format = QImage.Format_RGB888
        elif channels == 4:
            format = QImage.Format_RGBA8888
        else:
            raise ValueError(f"不支持的通道数: {channels}")
        
        # 确保图像数据连续
        if not image_data.flags['C_CONTIGUOUS']:
            image_data = np.ascontiguousarray(image_data)
            
        # 创建QImage和QPixmap
        q_image = QImage(image_data.data, width, height, bytes_per_line, format)
        pixmap = QPixmap.fromImage(q_image)
        
        # 获取标签的实际可用大小（减去边距和边框）
        label_size = label.size()
        available_width = max(50, label_size.width() - 10)  # 减去边距
        available_height = max(50, label_size.height() - 10)
        
        # 缩放图像以适应标签大小，保持纵横比
        scaled_pixmap = pixmap.scaled(
            available_width, 
            available_height,
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        # 设置图像标签
        label.setPixmap(scaled_pixmap)
        label.setText("")  # 清除文本
        label.setStyleSheet(label.styleSheet().replace("color: #999;", ""))  # 移除文本颜色

        # 在图像上方添加分数覆盖（如果已加载）
        try:
            current_frame = self.timeline_widget.get_current_frame() if hasattr(self, 'timeline_widget') else None
            if getattr(self, 'scores_loaded', False) and current_frame is not None:
                sc = self.frame_scores.get(current_frame, None)
                overlay = label.findChild(QLabel, 'score_overlay')
                if overlay is None:
                    overlay = QLabel(label)
                    overlay.setObjectName('score_overlay')
                    overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
                    overlay.setStyleSheet(
                        'background-color: rgba(0, 0, 0, 0.55); color: white; padding: 4px 6px; border-radius: 4px; font-weight: bold;'
                    )

                # 设置文本并显示/隐藏
                if sc is None:
                    overlay.setText('N/A')
                else:
                    try:
                        overlay.setText(f"{float(sc):.2f}")
                    except Exception:
                        overlay.setText(str(sc))

                overlay.adjustSize()
                # 将overlay放在标签的右上角（留一点边距）
                margin = 6
                lx = max(0, label.width() - overlay.width() - margin)
                ly = margin
                overlay.move(lx, ly)
                overlay.show()
                overlay.raise_()
            else:
                # 如果没有加载分数，隐藏任何已有overlay
                overlay = label.findChild(QLabel, 'score_overlay')
                if overlay is not None:
                    overlay.hide()
        except Exception as e:
            # 不要因为overlay失败而中断主流程
            # print(f"score overlay error: {e}")
            pass
    
    def load_frame_scores_for_current_file(self):
        """尝试从 repository 的 `data/` 目录或 HDF5 同目录加载与当前 HDF5 同名的 JSON 文件，解析其中的 `score` 字段为 frame->score 映射。"""
        # 重置
        self.frame_scores = {}
        self.scores_loaded = False
        self.scores_source = None

        if not self.current_file_path:
            return False

        import json

        # 优先查找 repo 根下的 data/ 目录
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_dir = os.path.join(project_root, 'data')
        base = os.path.splitext(os.path.basename(self.current_file_path))[0]

        candidates = [
            os.path.join(data_dir, base + '.json'),
            os.path.join(os.path.dirname(self.current_file_path), base + '.json')
        ]

        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        doc = json.load(f)

                    scores = doc.get('score') if isinstance(doc, dict) else None

                    # 兼容不同格式
                    if not scores:
                        # 尝试其他常见键
                        scores = doc.get('scores') or doc.get('score_list')

                    if isinstance(scores, list):
                        for entry in scores:
                            if isinstance(entry, dict):
                                for k, v in entry.items():
                                    try:
                                        idx = int(k)
                                        self.frame_scores[idx] = v
                                    except Exception:
                                        continue
                    elif isinstance(scores, dict):
                        for k, v in scores.items():
                            try:
                                idx = int(k)
                                self.frame_scores[idx] = v
                            except Exception:
                                continue

                    self.scores_loaded = True
                    self.scores_source = p
                    print(f"已加载帧分数: {len(self.frame_scores)} 条, 来自: {p}")
                    # 将分数数据传递给时间轴用于绘图
                    try:
                        if hasattr(self, 'timeline_widget') and self.timeline_widget:
                            self.timeline_widget.plot_scores(self.frame_scores)
                    except Exception:
                        pass
                    return True

                except Exception as e:
                    print(f"加载JSON分数失败 ({p}): {e}")
                    continue

        print("未找到匹配的 JSON 分数文件或加载失败")
        return False

    def update_ui_with_model(self):
        """使用模型数据更新UI"""
        if not self.hdf5_model:
            return

        # 更新数据列表（只显示适合标注的字段）
        self.data_list_widget.clear()
        annotation_keys = self.hdf5_model.get_annotation_compatible_keys()

        if annotation_keys:
            for key in annotation_keys:
                self.data_list_widget.addItem(key)
            # 确保列表是启用状态
            self.data_list_widget.setEnabled(True)
            print(f"找到 {len(annotation_keys)} 个适合标注的字段")
        else:
            # 如果没有适合的字段，显示提示
            self.data_list_widget.addItem("没有找到适合标注的字段")
            self.data_list_widget.setEnabled(False)
            print("警告：没有找到适合标注的字段")

        # 更新时间轴帧数
        frame_count = self.hdf5_model.get_frame_count()
        self.timeline_widget.set_total_frames(frame_count)

        # 启用保存按钮和字段管理按钮
        self.save_annotations_btn.setEnabled(True)
        self.save_json_btn.setEnabled(True)  # 新增
        self.create_field_button.setEnabled(True)  # 启用创建字段按钮
    
    def on_frame_changed(self, frame: int):
        """
        当时间轴上的当前帧改变时的处理函数

        Args:
            frame: 新的帧索引
        """
        if not self.hdf5_model:
            return

        # 更新所有图像窗口
        for key, window in self.image_windows.items():
            if window.isVisible():
                image_data = self.hdf5_model.get_image(key, frame)
                window.set_image(image_data)

        # 更新状态栏
        self.statusBar().showMessage(f"当前帧: {frame}/{self.hdf5_model.get_frame_count() - 1}")

        # 更新图像网格中的所有图像
        self.display_all_images()

        # 更新当前subtask信息显示
        self.update_subtask_info_display(frame)

    def update_subtask_info_display(self, frame: int):
        """更新当前subtask信息显示"""
        if not self.timeline_widget.time_windows:
            self.subtask_info_label.setText("未选中任何时间窗口")
            self.selected_window_index = None
            self.edit_annotation_btn.setEnabled(False)
            return

        # 查找当前帧所在的时间窗口
        current_window = None
        window_index = None
        for i, (start, end, description) in enumerate(self.timeline_widget.time_windows):
            if start <= frame <= end:
                current_window = (start, end, description)
                window_index = i
                break

        if current_window:
            start, end, description = current_window
            self.selected_window_index = window_index

            # 获取英文翻译
            from src.core.phrase_library import PhraseMapping
            phrase_mapping = PhraseMapping()
            english_translation = phrase_mapping.get_english_translation(description) if description else None

            info_text = f"时间窗口: {start}-{end} 帧\n"
            info_text += f"中文描述: {description if description else '未标注'}\n"
            if english_translation:
                info_text += f"英文描述: {english_translation}"
            elif description:
                info_text += f"英文描述: [未找到映射]"

            self.subtask_info_label.setText(info_text)
            self.edit_annotation_btn.setEnabled(True)
        else:
            self.subtask_info_label.setText("当前帧不在任何时间窗口内")
            self.selected_window_index = None
            self.edit_annotation_btn.setEnabled(False)

    def on_segment_clicked(self, segment):
        """处理时间轴段点击事件"""
        # 根据段的时间区间找到对应的时间窗口
        for i, (start, end, description) in enumerate(self.timeline_widget.time_windows):
            if segment.start == start and segment.end == end:
                self.selected_window_index = i
                # 更新subtask信息显示
                self.update_subtask_info_display(segment.start)
                print(f"选中时间窗口: {start}-{end}, 描述: {description}")
                break

    def on_subtask_info_clicked(self, event):
        """处理subtask信息标签的点击事件"""
        # 忽略event参数，只处理点击逻辑
        if self.selected_window_index is not None:
            self.edit_current_annotation()

    def edit_current_annotation(self):
        """编辑当前选中的标注"""
        if self.selected_window_index is None or self.selected_window_index >= len(self.timeline_widget.time_windows):
            return

        # 获取当前窗口信息
        start, end, current_description = self.timeline_widget.time_windows[self.selected_window_index]

        # 打开短语选择对话框，传入时间区间信息
        dialog = PhraseSelectionDialog(self, self.phrase_library, current_description, start, end)
        if dialog.exec_() == dialog.Accepted:
            new_description = dialog.get_selected_phrase()
            new_start, new_end = dialog.get_time_interval()

            # 检查时间区间是否发生变化
            time_changed = dialog.has_time_changed()

            if time_changed:
                # 检查新的时间区间是否与其他窗口重合（排除当前窗口）
                if self.check_time_interval_conflict(new_start, new_end, self.selected_window_index):
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "时间区间冲突",
                                      f"新的时间区间 {new_start}-{new_end} 与现有窗口重合")
                    return

            if new_description is not None:
                # 更新时间窗口的数据
                old_start, old_end = start, end
                self.timeline_widget.time_windows[self.selected_window_index] = [new_start, new_end, new_description]

                if time_changed:
                    # 如果时间区间发生变化，需要更新时间轴上的段
                    self.timeline_widget.update_window_segment_with_time(
                        self.selected_window_index, old_start, old_end, new_start, new_end, new_description
                    )
                    print(f"更新标注: 窗口 {old_start}-{old_end} -> {new_start}-{new_end}, 描述: {new_description}")
                else:
                    # 只更新描述
                    self.timeline_widget.update_window_segment(self.selected_window_index, new_description)
                    print(f"更新标注: 窗口{start}-{end}, 新描述: {new_description}")

                # 更新当前显示
                current_frame = self.timeline_widget.get_current_frame()
                self.update_subtask_info_display(current_frame)

    def check_time_interval_conflict(self, start, end, exclude_index=None):
        """检查时间区间是否与现有窗口冲突"""
        for i, (window_start, window_end, _) in enumerate(self.timeline_widget.time_windows):
            # 跳过指定的窗口索引
            if exclude_index is not None and i == exclude_index:
                continue

            # 检查是否有重合
            if not (end < window_start or start > window_end):
                return True
        return False

    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件"""
        # 处理空格键播放/暂停
        if event.key() == Qt.Key_Space:
            if hasattr(self, 'timeline_widget') and self.timeline_widget:
                self.timeline_widget.toggle_play()
            event.accept()
            return
        
        # 处理左右方向键
        elif event.key() == Qt.Key_Left:
            if hasattr(self, 'timeline_widget') and self.timeline_widget:
                current_frame = self.timeline_widget.get_current_frame()
                if current_frame > 0:
                    self.timeline_widget.set_current_frame(current_frame - 1)
            event.accept()
            return
        
        elif event.key() == Qt.Key_Right:
            if hasattr(self, 'timeline_widget') and self.timeline_widget:
                current_frame = self.timeline_widget.get_current_frame()
                frame_count = self.hdf5_model.get_frame_count() if self.hdf5_model else 100
                if current_frame < frame_count - 1:
                    self.timeline_widget.set_current_frame(current_frame + 1)
            event.accept()
            return
        
        # 移除Enter键进入范围选择模式的功能
        # elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
        #     # 如果时间轴已初始化，则转发事件到时间轴
        #     if hasattr(self, 'timeline_widget') and self.timeline_widget:
        #         print("检测到Enter键，转发到时间轴进入范围选择模式")
        #         self.timeline_widget.keyPressEvent(event)
        
        # 其他键传递给父类
        super().keyPressEvent(event)
    
    # 移除load_subtasks方法 - 不再需要
    
    # 移除图像选择变化处理 - 不再需要
    
    def update_image_window(self, key: str):
        """更新图像窗口的内容"""
        if not self.hdf5_model or key not in self.image_windows:
            return
        
        # 获取当前帧的图像数据
        image_data = self.hdf5_model.get_image(key, self.timeline_widget.current_frame)
        
        # 更新图像窗口
        window = self.image_windows[key]
        window.set_image(image_data)
    
    def on_field_selection_changed(self):
        """处理字段选择变化"""
        selected_items = self.data_list_widget.selectedItems()

        if selected_items and self.data_list_widget.isEnabled():
            # 检查选中的是否是有效字段（不是提示信息）
            selected_text = selected_items[0].text()
            if selected_text != "没有找到适合标注的字段":
                self.load_field_button.setEnabled(True)
                self.delete_field_button.setEnabled(True)
                # 自动加载选中的字段
                self.load_selected_field()
            else:
                self.load_field_button.setEnabled(False)
                self.delete_field_button.setEnabled(False)
        else:
            self.load_field_button.setEnabled(False)
            self.delete_field_button.setEnabled(False)

    def load_selected_field(self):
        """加载选中的字段用于标注"""
        selected_items = self.data_list_widget.selectedItems()

        if not selected_items or not self.hdf5_model:
            return

        field_name = selected_items[0].text()

        # 检查是否是有效字段
        if field_name == "没有找到适合标注的字段":
            QMessageBox.warning(self, "无效选择", "请选择一个有效的字段")
            return

        # 验证字段是否适合标注
        compatible_keys = self.hdf5_model.get_annotation_compatible_keys()
        if field_name not in compatible_keys:
            QMessageBox.warning(self, "字段不兼容", f"字段 '{field_name}' 不适合保存标注数据")
            return

        self.current_annotation_field = field_name

        # 更新当前字段显示
        self.current_field_label.setText(f"当前字段: {field_name}")

        # 清除按钮现在在TimelineWidget中，会自动更新状态

        # 清除现有的时间轴标注
        self.timeline_widget.time_windows.clear()

        # 清除时间轴上的annotation段
        for timeline in self.timeline_widget.timelines:
            timeline.segments = [seg for seg in timeline.segments if seg.key != "annotation"]

        # 尝试从HDF5文件加载该字段的标注数据
        self.load_field_annotations(field_name)

        # 更新时间轴显示
        self.timeline_widget.update()

        # 更新当前subtask信息显示
        current_frame = self.timeline_widget.get_current_frame()
        self.update_subtask_info_display(current_frame)

        print(f"已加载字段 '{field_name}' 用于标注")

        # 更新时间轴清除按钮状态
        self.timeline_widget.update_clear_button_state()

    def clear_timeline_annotations(self):
        """清除时间轴上的标注"""
        # 清除时间窗口
        self.timeline_widget.time_windows.clear()

        # 清除时间轴上的annotation段
        for timeline in self.timeline_widget.timelines:
            timeline.segments = [seg for seg in timeline.segments if seg.key != "annotation"]

        # 重置当前字段
        self.current_annotation_field = None
        self.current_field_label.setText("当前字段: 未选择")

        # 清除按钮现在在TimelineWidget中，会自动更新状态

        # 更新时间轴显示
        self.timeline_widget.update()

        # 更新当前subtask信息显示
        current_frame = self.timeline_widget.get_current_frame()
        self.update_subtask_info_display(current_frame)

        print("已清除时间轴标注")

    def create_new_annotation_field(self):
        """创建新的标注字段"""
        if not self.hdf5_model:
            QMessageBox.warning(self, "错误", "请先加载HDF5文件")
            return

        # 弹出对话框让用户输入字段名
        from PyQt5.QtWidgets import QInputDialog
        field_name, ok = QInputDialog.getText(
            self, "创建新标注字段",
            "请输入新字段名称:\n(建议使用英文，如: my_annotations, task_labels等)"
        )

        if not ok or not field_name.strip():
            return

        field_name = field_name.strip()

        # 验证字段名
        if not field_name.replace('_', '').replace('/', '').isalnum():
            QMessageBox.warning(self, "无效字段名", "字段名只能包含字母、数字、下划线和斜杠")
            return

        # 检查字段是否已存在
        if field_name in self.hdf5_model.file:
            QMessageBox.warning(self, "字段已存在", f"字段 '{field_name}' 已经存在")
            return

        # 确认创建
        reply = QMessageBox.question(
            self, "确认创建",
            f"确定要创建新的标注字段 '{field_name}' 吗？\n\n"
            f"这将在HDF5文件中创建一个新的字符串类型数据集。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 创建新的标注字段
            success = self.hdf5_model.create_language_key(field_name)

            if success:
                # 刷新字段列表
                self.update_ui_with_model()

                # 自动选择新创建的字段
                for i in range(self.data_list_widget.count()):
                    item = self.data_list_widget.item(i)
                    if item.text() == field_name:
                        self.data_list_widget.setCurrentItem(item)
                        break

                QMessageBox.information(
                    self, "创建成功",
                    f"成功创建标注字段 '{field_name}'\n\n"
                    f"您现在可以选择该字段并开始标注。"
                )
                print(f"成功创建新标注字段: {field_name}")
            else:
                QMessageBox.critical(self, "创建失败", f"创建字段 '{field_name}' 失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建字段时发生错误: {str(e)}")
            print(f"创建字段失败: {e}")

    def delete_selected_field(self):
        """删除选中的标注字段"""
        selected_items = self.data_list_widget.selectedItems()

        if not selected_items or not self.hdf5_model:
            return

        field_name = selected_items[0].text()

        # 检查是否是有效字段
        if field_name == "没有找到适合标注的字段":
            QMessageBox.warning(self, "无效选择", "请选择一个有效的字段")
            return

        # 检查字段是否存在
        if field_name not in self.hdf5_model.file:
            QMessageBox.warning(self, "字段不存在", f"字段 '{field_name}' 不存在于HDF5文件中")
            return

        # 警告确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"⚠️ 警告：确定要删除字段 '{field_name}' 吗？\n\n"
            f"这将永久删除该字段及其所有标注数据！\n"
            f"此操作无法撤销。\n\n"
            f"如果这是当前正在编辑的字段，时间轴上的标注也会被清除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 如果删除的是当前字段，先清除时间轴
            if self.current_annotation_field == field_name:
                self.clear_timeline_annotations()

            # 从HDF5文件中删除字段
            del self.hdf5_model.file[field_name]

            # 从缓存中删除
            if field_name in self.hdf5_model.languages:
                del self.hdf5_model.languages[field_name]

            # 刷新数据键列表
            if field_name in self.hdf5_model.data_keys:
                self.hdf5_model.data_keys.remove(field_name)

            # 确保数据写入文件
            self.hdf5_model.file.flush()

            # 刷新UI
            self.update_ui_with_model()

            QMessageBox.information(
                self, "删除成功",
                f"字段 '{field_name}' 已成功删除"
            )
            print(f"成功删除字段: {field_name}")

        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除字段 '{field_name}' 时发生错误: {str(e)}")
            print(f"删除字段失败: {e}")

    def load_field_annotations(self, field_name):
        """从HDF5文件加载指定字段的标注数据"""
        if not self.hdf5_model:
            return

        try:
            # 检查是否存在该字段的标注数据
            if field_name in self.hdf5_model.file:
                # 获取标注数据 - 返回格式为 {(start, end): description}
                languages = self.hdf5_model.get_languages_for_key(field_name)

                if languages:
                    from src.core.phrase_library import PhraseMapping
                    phrase_mapping = PhraseMapping()

                    # 将标注数据转换为时间窗口
                    for (start, end), english_text in languages.items():
                        # 尝试将英文转换回中文显示
                        chinese_text = phrase_mapping.get_chinese_translation(english_text)
                        display_text = chinese_text if chinese_text else english_text

                        # 添加到时间窗口列表
                        self.timeline_widget.time_windows.append([start, end, display_text])

                        # 创建时间轴段
                        self.timeline_widget.create_window_segment([start, end, display_text])

                    print(f"从HDF5文件加载了字段 '{field_name}' 的 {len(languages)} 个标注")
                else:
                    print(f"字段 '{field_name}' 中没有找到标注数据")
            else:
                print(f"HDF5文件中没有字段 '{field_name}'")

        except Exception as e:
            print(f"加载字段 '{field_name}' 的标注数据失败: {e}")
            import traceback
            traceback.print_exc()

    def on_data_selection_changed(self):
        """处理数据选择变化（保留兼容性）"""
        selected_items = self.data_list_widget.selectedItems()

        if not selected_items:
            return

        # 只显示第一个选中项的数据
        first_item = selected_items[0]
        key = first_item.text()

        self.update_data_display(key)
    
    def update_data_display(self, key: str):
        """更新数据显示，添加安全错误处理"""
        if not self.hdf5_model:
            return
        
        current_frame = self.timeline_widget.current_frame
        
        try:
            # 获取数据
            data = self.hdf5_model.get_data(key, current_frame)
            
            if data is None:
                print(f"{key}: 无数据")
                return
            
            # 显示数据
            if isinstance(data, np.ndarray):
                if data.size > 100:  # 数据太大，只显示形状
                    print(f"{key}: 形状={data.shape}, 类型={data.dtype}")
                else:
                    # 处理可能的字节字符串
                    text = str(data)
                    # 限制显示长度，避免界面卡顿
                    if len(text) > 200:
                        text = text[:200] + "..."
                    print(f"{key}: {text}")
            else:
                # 处理单个字节字符串或其他类型
                if isinstance(data, bytes):
                    try:
                        text = data.decode('utf-8', errors='replace')
                    except:
                        text = str(data)
                else:
                    text = str(data)
                
                # 限制显示长度
                if len(text) > 200:
                    text = text[:200] + "..."
                # 简化数据显示，不再需要data_value_label
            print(f"{key}: {text}")

        except Exception as e:
            # 捕获所有异常，防止软件崩溃
            error_msg = f"{key}: 数据读取错误 - {str(e)[:100]}"
            print(error_msg)
            print(f"更新数据显示时出错: {key}, 错误: {e}")

            # 尝试获取数据集基本信息
            try:
                info = self.hdf5_model.get_data_info(key)
                if info:
                    print(f"{key}: 形状={info.get('shape', '未知')}, 类型={info.get('dtype', '未知')}")
            except:
                pass
    
    # 移除on_segment_clicked方法 - 不再需要，时间窗口编辑已在TimelineBar中实现
    
    # 移除remove_selected_keys_from_timeline方法 - 不再需要
    
    # 移除on_range_selected方法 - 不再需要
    
    # 移除update_language_display方法 - 不再需要
    
    # 移除reload_current_key_display方法 - 不再需要
    
    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        
        # 启动延迟更新定时器，避免频繁重绘
        if hasattr(self, 'resize_timer'):
            self.resize_timer.stop()
            self.resize_timer.start(300)  # 300ms延迟
    
    def on_resize_finished(self):
        """窗口大小变化完成后的处理"""
        # 如果有HDF5模型且图像显示区域已初始化，重新显示图像
        if self.hdf5_model and self.images_grid_layout is not None:
            self.display_all_images()
    
    # 移除reload_language_display方法 - 不再需要
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 停止播放
        if hasattr(self.timeline_widget, 'play_timer') and self.timeline_widget.play_timer.isActive():
            self.timeline_widget.play_timer.stop()
        
        # 关闭所有图像窗口
        for window in self.image_windows.values():
            window.close()
        
        # 关闭HDF5模型
        if self.hdf5_model:
            self.hdf5_model.close()
        
        # 接受关闭事件
        event.accept()
    
    # 移除on_segments_multi_selected方法 - 不再需要
    
    # 移除next_frame和toggle_play方法 - 播放控制已移到TimelineWidget中
    
    # 移除add_selected_keys_to_timeline方法 - 不再需要

    # 移除on_edit_key_changed方法 - 不再需要
    
    # 移除add_new_key方法 - 不再需要
    

    # 移除update_edit_key_combo方法 - 不再需要
    
    # 移除load_current_key_data方法 - 不再需要

    # 移除load_current_key_data_without_hiding_others方法 - 不再需要

    def on_window_added(self, start_frame, end_frame):
        """处理新增时间窗口事件"""
        print(f"主窗口收到新增时间窗口事件: {start_frame}-{end_frame}")
        # 更新当前subtask信息显示
        current_frame = self.timeline_widget.current_frame
        self.update_subtask_info_display(current_frame)
        print(f"新增时间窗口: {start_frame}-{end_frame}")
        # 可以在这里添加额外的处理逻辑，比如自动跳转到新窗口
        self.timeline_widget.set_current_frame(start_frame)

    def save_annotations(self):
        """保存标注数据到HDF5文件"""
        if not self.hdf5_model or not self.timeline_widget.time_windows:
            QMessageBox.information(self, "提示", "没有数据需要保存")
            return

        # 检查是否选择了标注字段
        if not self.current_annotation_field:
            QMessageBox.warning(self, "未选择字段", "请先选择要保存标注的字段")
            return

        # 验证时间窗口
        is_valid, error_message = self.timeline_widget.validate_time_windows()
        if not is_valid:
            QMessageBox.warning(self, "保存验证失败", f"无法保存：{error_message}\n\n请确保所有时间窗口相连且覆盖整个时间范围。")
            return

        # 确认保存操作 - 明确只保存到当前文件的指定字段
        file_name = os.path.basename(self.current_file_path) if self.current_file_path else "未知文件"
        annotation_count = len(self.timeline_widget.time_windows)

        reply = QMessageBox.question(
            self, "确认保存",
            f"确认将 {annotation_count} 个标注保存到字段 '{self.current_annotation_field}'？\n\n"
            f"目标文件: {file_name}\n"
            f"完整路径: {self.current_file_path}\n\n"
            f"注意：这将覆盖该字段现有的标注数据。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        # 额外安全检查：确保HDF5模型对应当前文件
        if self.hdf5_model.file_path != self.current_file_path:
            QMessageBox.critical(
                self, "错误",
                f"文件路径不匹配！\n"
                f"当前文件: {self.current_file_path}\n"
                f"模型文件: {self.hdf5_model.file_path}\n"
                f"为安全起见，取消保存操作。"
            )
            return

        # 调用TimelineWidget的保存方法，传递HDF5模型和字段名
        success = self.timeline_widget.save_annotations(self.hdf5_model, self.current_annotation_field)

        if success:
            print(f"标注数据已成功保存到HDF5文件字段 '{self.current_annotation_field}': {self.current_file_path}")
            # 显示保存成功的详细信息
            QMessageBox.information(
                self, "保存成功",
                f"已成功保存 {len(self.timeline_widget.time_windows)} 个标注到:\n"
                f"文件: {file_name}\n"
                f"字段: {self.current_annotation_field}"
            )
        else:
            print("保存标注数据失败")

    def load_existing_annotations(self):
        """从HDF5文件加载已有的标注数据（已弃用，现在通过字段选择加载）"""
        # 这个方法现在不再自动调用，标注数据的加载通过用户选择字段来控制
        print("load_existing_annotations方法已弃用，请使用字段选择功能加载标注数据")
        pass

    # 移除execute_batch_setting方法 - 不再需要

    def save_annotations_as_json(self):
        """保存标注数据为JSON文件"""
        if not self.timeline_widget.time_windows:
            QMessageBox.information(self, "提示", "没有时间窗口需要保存")
            return

        # 检查是否选择了标注字段
        if not self.current_annotation_field:
            QMessageBox.warning(self, "未选择字段", "请先选择要保存标注的字段")
            return

        # 验证时间窗口
        is_valid, error_message = self.timeline_widget.validate_time_windows()
        if not is_valid:
            QMessageBox.warning(self, "保存验证失败", f"无法保存：{error_message}\n\n请确保所有时间窗口相连且覆盖整个时间范围。")
            return

        # 准备保存数据，只保存英文标注
        from src.core.phrase_library import PhraseMapping
        phrase_mapping = PhraseMapping()

        annotations = []
        for start, end, description in self.timeline_widget.time_windows:
            # 获取英文翻译，如果没有映射则使用原文
            english_translation = phrase_mapping.get_english_translation(description)
            save_description = english_translation if english_translation else description

            annotation_data = {
                "start_frame": start,
                "end_frame": end,
                "description": save_description,  # 只保存英文标注
                "duration_frames": end - start + 1
            }
            annotations.append(annotation_data)

        # 选择保存文件
        from PyQt5.QtWidgets import QFileDialog
        import os

        # 生成默认文件名，包含字段名
        default_filename = f"annotations_{self.current_annotation_field}.json"
        if self.current_file_path:
            base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
            default_filename = f"{base_name}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存标注数据为JSON", default_filename, "JSON文件 (*.json);;所有文件 (*)"
        )

        if file_path:
            # 确保文件扩展名是.json
            if not file_path.lower().endswith('.json'):
                file_path += '.json'

            try:
                import json
                from PyQt5.QtCore import QDateTime

                # 准备保存的数据结构，使用选择的字段名作为数据键
                save_data = {
                    "total_frames": self.timeline_widget.total_frames,
                    self.current_annotation_field: annotations,  # 使用选择的字段名作为键
                    "annotation_field": self.current_annotation_field,  # 记录标注字段名
                    "created_time": QDateTime.currentDateTime().toString("ddd MMM dd hh:mm:ss yyyy"),
                    "source_file": self.current_file_path if hasattr(self, 'current_file_path') else "unknown"
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(
                    self, "成功",
                    f"标注数据已保存到: {file_path}\n字段: {self.current_annotation_field}\n格式: JSON"
                )
                print(f"标注数据已保存到JSON文件: {file_path} (字段: {self.current_annotation_field})")
                return True

            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存JSON文件失败: {str(e)}")
                print(f"保存JSON标注数据失败: {e}")
                return False

        return False

    def load_annotations_from_json(self):
        """从JSON文件加载标注数据"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载标注数据", "", "JSON文件 (*.json);;所有文件 (*)"
        )

        if file_path:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 清除现有时间窗口
                self.timeline_widget.time_windows.clear()

                # 清除时间轴上的段
                for timeline in self.timeline_widget.timelines:
                    timeline.segments = [seg for seg in timeline.segments if seg.key != "annotation"]

                # 检测JSON格式并加载时间窗口
                annotations_data = []
                loaded_field = None

                # 新格式：检查是否有annotation_field字段
                if "annotation_field" in data:
                    loaded_field = data["annotation_field"]
                    annotations_data = data.get(loaded_field, [])
                    print(f"检测到新格式JSON，字段: {loaded_field}")
                # 兼容旧格式：直接查找annotations键
                elif "annotations" in data:
                    annotations_data = data["annotations"]
                    loaded_field = "annotations"
                    print("检测到旧格式JSON，使用默认annotations字段")
                else:
                    # 尝试查找其他可能的标注字段
                    for key, value in data.items():
                        if (isinstance(value, list) and key not in ["total_frames", "created_time", "source_file"]
                            and len(value) > 0 and isinstance(value[0], dict)
                            and "start_frame" in value[0]):
                            annotations_data = value
                            loaded_field = key
                            print(f"自动检测到标注字段: {key}")
                            break

                if not annotations_data:
                    QMessageBox.warning(self, "格式错误", "JSON文件中没有找到有效的标注数据")
                    return False

                # 加载时间窗口
                for annotation in annotations_data:
                    window = [
                        annotation["start_frame"],
                        annotation["end_frame"],
                        annotation.get("description", "")
                    ]
                    self.timeline_widget.time_windows.append(window)
                    self.timeline_widget.create_window_segment(window)

                # 如果加载了字段信息，更新当前字段状态
                if loaded_field and self.hdf5_model:
                    compatible_keys = self.hdf5_model.get_annotation_compatible_keys()
                    if loaded_field in compatible_keys:
                        self.current_annotation_field = loaded_field
                        self.current_field_label.setText(f"当前字段: {loaded_field}")
                        # 清除按钮现在在TimelineWidget中，会自动更新状态
                        print(f"已设置当前标注字段为: {loaded_field}")

                print(f"从 {file_path} 加载了 {len(self.timeline_widget.time_windows)} 个时间窗口")

                # 更新时间轴显示
                self.timeline_widget.update()

                # 更新当前subtask信息显示
                current_frame = self.timeline_widget.get_current_frame()
                self.update_subtask_info_display(current_frame)

                QMessageBox.information(
                    self, "成功",
                    f"从 {file_path} 加载了 {len(self.timeline_widget.time_windows)} 个标注\n"
                    f"字段: {loaded_field if loaded_field else '未知'}"
                )
                return True

            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载JSON文件失败: {str(e)}")
                print(f"加载JSON标注数据失败: {e}")
                return False

        return False