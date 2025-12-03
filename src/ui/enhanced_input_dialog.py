#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QTabWidget, QWidget, QTextEdit, QSplitter,
                             QGroupBox, QComboBox, QCheckBox, QSpacerItem,
                             QSizePolicy, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette
from typing import Optional
from src.utils.phrase_library import PhraseLibrary

class EnhancedInputDialog(QDialog):
    """增强版Language输入对话框，支持手动输入和词库选择"""
    
    def __init__(self, parent=None, start_idx: int = 0, end_idx: int = 0, 
                 current_key: str = "language", initial_text: str = ""):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            start_idx: 起始帧索引
            end_idx: 结束帧索引
            current_key: 当前编辑的键名
            initial_text: 初始文本（用于编辑已有内容）
        """
        super().__init__(parent)
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.current_key = current_key
        self.initial_text = initial_text
        self.phrase_library = PhraseLibrary()
        self.selected_phrase = ""
        
        self.setWindowTitle(f"设置 {current_key} 描述 (帧 {start_idx} - {end_idx})")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setup_ui()
        self.connect_signals()
        
        # 如果有初始文本，填充到输入框
        if initial_text:
            self.manual_input.setText(initial_text)
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题信息
        info_label = QLabel(f"为帧 {self.start_idx} 至 {self.end_idx} 设置 '{self.current_key}' 描述")
        info_label.setFont(QFont("Arial", 10, QFont.Bold))
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧：手动输入区域
        self.setup_manual_input_area(main_splitter)
        
        # 右侧：词库选择区域
        self.setup_phrase_library_area(main_splitter)
        
        # 设置分割器比例
        main_splitter.setSizes([250, 350])
        
        # 底部按钮区域
        self.setup_button_area(layout)
    
    def setup_manual_input_area(self, parent_widget):
        """设置手动输入区域"""
        manual_group = QGroupBox("手动输入")
        manual_layout = QVBoxLayout(manual_group)
        
        # 输入框
        self.manual_input = QTextEdit()
        self.manual_input.setMaximumHeight(100)
        self.manual_input.setPlaceholderText("请输入描述文本...")
        manual_layout.addWidget(self.manual_input)
        
        # 输入提示
        tip_label = QLabel("支持多行输入，Ctrl+Enter快速确认")
        tip_label.setStyleSheet("color: #666; font-size: 10px;")
        manual_layout.addWidget(tip_label)
        
        # 添加当前输入到词库的按钮
        add_to_library_btn = QPushButton("添加到词库")
        add_to_library_btn.setToolTip("将当前输入的文本添加到词库中")
        add_to_library_btn.clicked.connect(self.add_current_text_to_library)
        manual_layout.addWidget(add_to_library_btn)
        
        # 添加弹簧
        manual_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        parent_widget.addWidget(manual_group)
    
    def setup_phrase_library_area(self, parent_widget):
        """设置词库选择区域"""
        library_group = QGroupBox("词库选择")
        library_layout = QVBoxLayout(library_group)
        
        # 顶部控制区域
        control_layout = QHBoxLayout()
        
        # 分类选择
        category_label = QLabel("分类:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("全部")
        categories = self.phrase_library.get_categories()
        for category in categories.keys():
            self.category_combo.addItem(category)
        
        control_layout.addWidget(category_label)
        control_layout.addWidget(self.category_combo)
        
        # 搜索框
        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        
        control_layout.addWidget(search_label)
        control_layout.addWidget(self.search_input)
        
        library_layout.addLayout(control_layout)
        
        # 短语列表
        self.phrase_list = QListWidget()
        self.phrase_list.setAlternatingRowColors(True)
        self.populate_phrase_list()
        library_layout.addWidget(self.phrase_list)
        
        # 底部操作按钮
        library_btn_layout = QHBoxLayout()
        
        self.use_phrase_btn = QPushButton("使用选中短语")
        self.use_phrase_btn.setEnabled(False)
        
        edit_library_btn = QPushButton("管理词库")
        edit_library_btn.setToolTip("添加、删除或编辑词库中的短语")
        
        reload_library_btn = QPushButton("重新加载")
        reload_library_btn.setToolTip("重新加载词库文件")
        
        library_btn_layout.addWidget(self.use_phrase_btn)
        library_btn_layout.addWidget(edit_library_btn)
        library_btn_layout.addWidget(reload_library_btn)
        
        library_layout.addLayout(library_btn_layout)
        
        # 连接信号
        self.use_phrase_btn.clicked.connect(self.use_selected_phrase)
        edit_library_btn.clicked.connect(self.open_library_manager)
        reload_library_btn.clicked.connect(self.reload_phrase_library)
        
        parent_widget.addWidget(library_group)
    
    def setup_button_area(self, layout):
        """设置底部按钮区域"""
        button_layout = QHBoxLayout()
        
        # 预览区域
        preview_group = QGroupBox("当前选择预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("未选择任何内容")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                min-height: 40px;
            }
        """)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        # 主要操作按钮
        main_button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.setDefault(True)
        self.ok_button.setMinimumHeight(35)
        
        cancel_button = QPushButton("取消")
        cancel_button.setMinimumHeight(35)
        
        main_button_layout.addWidget(self.ok_button)
        main_button_layout.addWidget(cancel_button)
        
        layout.addLayout(main_button_layout)
        
        # 连接信号
        self.ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
    
    def connect_signals(self):
        """连接信号"""
        # 分类变化
        self.category_combo.currentTextChanged.connect(self.filter_phrases)
        
        # 搜索
        self.search_input.textChanged.connect(self.filter_phrases)
        
        # 列表选择
        self.phrase_list.itemSelectionChanged.connect(self.on_phrase_selection_changed)
        self.phrase_list.itemDoubleClicked.connect(self.on_phrase_double_clicked)
        
        # 手动输入变化
        self.manual_input.textChanged.connect(self.update_preview)
        
        # 词库更新
        self.phrase_library.library_updated.connect(self.on_library_updated)
        
        # 快捷键
        self.manual_input.keyPressEvent = self.manual_input_key_press
    
    def populate_phrase_list(self, phrases=None):
        """填充短语列表"""
        self.phrase_list.clear()
        
        if phrases is None:
            phrases = self.phrase_library.get_all_phrases()
        
        for phrase in phrases:
            item = QListWidgetItem(phrase)
            item.setToolTip(phrase)
            self.phrase_list.addItem(item)
    
    def filter_phrases(self):
        """根据分类和搜索条件过滤短语"""
        category = self.category_combo.currentText()
        search_text = self.search_input.text().strip()
        
        # 获取基础短语列表
        if category == "全部":
            phrases = self.phrase_library.get_all_phrases()
        else:
            phrases = self.phrase_library.get_phrases_by_category(category)
        
        # 应用搜索过滤
        if search_text:
            search_text = search_text.lower()
            phrases = [p for p in phrases if search_text in p.lower()]
        
        self.populate_phrase_list(phrases)
    
    def on_phrase_selection_changed(self):
        """处理短语选择变化"""
        selected_items = self.phrase_list.selectedItems()
        
        if selected_items:
            self.selected_phrase = selected_items[0].text()
            self.use_phrase_btn.setEnabled(True)
        else:
            self.selected_phrase = ""
            self.use_phrase_btn.setEnabled(False)
        
        self.update_preview()
    
    def on_phrase_double_clicked(self, item):
        """处理短语双击"""
        self.use_selected_phrase()
    
    def use_selected_phrase(self):
        """使用选中的短语"""
        if self.selected_phrase:
            self.manual_input.setText(self.selected_phrase)
            self.update_preview()
    
    def update_preview(self):
        """更新预览"""
        manual_text = self.manual_input.toPlainText().strip()
        
        if manual_text:
            self.preview_label.setText(f"将设置: {manual_text}")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #e8f5e8;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                    padding: 8px;
                    min-height: 40px;
                    color: #2e7d32;
                }
            """)
        elif self.selected_phrase:
            self.preview_label.setText(f"已选择: {self.selected_phrase}")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #e3f2fd;
                    border: 1px solid #2196f3;
                    border-radius: 4px;
                    padding: 8px;
                    min-height: 40px;
                    color: #1565c0;
                }
            """)
        else:
            self.preview_label.setText("请输入文本或选择词库中的短语")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 8px;
                    min-height: 40px;
                    color: #666;
                }
            """)
    
    def add_current_text_to_library(self):
        """添加当前输入的文本到词库"""
        text = self.manual_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请先输入要添加的文本")
            return
        
        # 询问分类
        categories = list(self.phrase_library.get_categories().keys())
        if not categories:
            categories = ["默认"]
        
        category, ok = QInputDialog.getItem(
            self, "选择分类", "请选择要添加到的分类:", 
            categories + ["新建分类..."], 0, False
        )
        
        if not ok:
            return
        
        if category == "新建分类...":
            category, ok = QInputDialog.getText(
                self, "新建分类", "请输入新分类名称:"
            )
            if not ok or not category.strip():
                return
            category = category.strip()
        
        # 添加到词库
        if self.phrase_library.add_phrase(text, category):
            QMessageBox.information(self, "成功", f"已将 '{text}' 添加到分类 '{category}'")
            self.filter_phrases()  # 刷新列表
        else:
            QMessageBox.warning(self, "失败", "该短语已存在于词库中")
    
    def open_library_manager(self):
        """打开词库管理器"""
        from src.ui.phrase_library_manager import PhraseLibraryManager
        manager = PhraseLibraryManager(self, self.phrase_library)
        manager.exec_()
    
    def reload_phrase_library(self):
        """重新加载词库"""
        self.phrase_library.reload_library()
        
        # 重新填充分类下拉框
        self.category_combo.clear()
        self.category_combo.addItem("全部")
        categories = self.phrase_library.get_categories()
        for category in categories.keys():
            self.category_combo.addItem(category)
        
        # 刷新列表
        self.filter_phrases()
        
        QMessageBox.information(self, "完成", "词库已重新加载")
    
    def on_library_updated(self):
        """词库更新时的处理"""
        current_category = self.category_combo.currentText()
        
        # 重新填充分类下拉框
        self.category_combo.clear()
        self.category_combo.addItem("全部")
        categories = self.phrase_library.get_categories()
        for category in categories.keys():
            self.category_combo.addItem(category)
        
        # 尝试恢复之前的分类选择
        index = self.category_combo.findText(current_category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        
        # 刷新列表
        self.filter_phrases()
    
    def manual_input_key_press(self, event):
        """处理手动输入框的键盘事件"""
        # Ctrl+Enter 快速确认
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            self.accept()
        else:
            # 调用原始的keyPressEvent
            QTextEdit.keyPressEvent(self.manual_input, event)
    
    def get_description(self) -> str:
        """获取用户输入的描述"""
        return self.manual_input.toPlainText().strip()
    
    def accept(self):
        """确认对话框"""
        text = self.get_description()
        if not text:
            QMessageBox.warning(self, "警告", "请输入描述或选择词库中的短语")
            return
        
        super().accept() 