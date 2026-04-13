#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QPushButton, QLineEdit, QLabel,
                             QGroupBox, QMessageBox, QInputDialog, QTextEdit,
                             QSplitter, QComboBox, QMenu, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class PhraseLibraryManager(QDialog):
    """词库管理器对话框"""
    
    def __init__(self, parent=None, phrase_library=None):
        super().__init__(parent)
        self.phrase_library = phrase_library
        
        self.setWindowTitle("词库管理器")
        self.setModal(True)
        self.resize(700, 500)
        
        self.setup_ui()
        self.connect_signals()
        self.populate_tree()
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("语言短语库管理")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧：树形显示
        self.setup_tree_area(main_splitter)
        
        # 右侧：编辑区域
        self.setup_edit_area(main_splitter)
        
        # 底部按钮
        self.setup_bottom_buttons(layout)
    
    def setup_tree_area(self, parent_widget):
        """设置树形显示区域"""
        tree_group = QGroupBox("词库内容")
        tree_layout = QVBoxLayout(tree_group)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        search_layout.addWidget(self.search_input)
        tree_layout.addLayout(search_layout)
        
        # 树形控件
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["分类/短语", "数量"])
        self.tree_widget.setAlternatingRowColors(True)
        tree_layout.addWidget(self.tree_widget)
        
        parent_widget.addWidget(tree_group)
    
    def setup_edit_area(self, parent_widget):
        """设置编辑区域"""
        edit_group = QGroupBox("编辑操作")
        edit_layout = QVBoxLayout(edit_group)
        
        # 添加分类
        edit_layout.addWidget(QLabel("添加新分类:"))
        category_layout = QHBoxLayout()
        self.new_category_input = QLineEdit()
        self.add_category_btn = QPushButton("添加分类")
        category_layout.addWidget(self.new_category_input)
        category_layout.addWidget(self.add_category_btn)
        edit_layout.addLayout(category_layout)
        
        # 添加短语
        edit_layout.addWidget(QLabel("添加新短语:"))
        self.category_combo = QComboBox()
        edit_layout.addWidget(self.category_combo)
        
        self.new_phrase_input = QTextEdit()
        self.new_phrase_input.setMaximumHeight(80)
        edit_layout.addWidget(self.new_phrase_input)
        
        self.add_phrase_btn = QPushButton("添加短语")
        edit_layout.addWidget(self.add_phrase_btn)
        
        parent_widget.addWidget(edit_group)
    
    def setup_bottom_buttons(self, layout):
        """设置底部按钮"""
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存词库")
        close_btn = QPushButton("关闭")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        close_btn.clicked.connect(self.accept)
    
    def connect_signals(self):
        """连接信号"""
        self.add_category_btn.clicked.connect(self.add_new_category)
        self.add_phrase_btn.clicked.connect(self.add_new_phrase)
        self.save_btn.clicked.connect(self.save_library)
        self.search_input.textChanged.connect(self.filter_tree)
    
    def populate_tree(self):
        """填充树形控件"""
        if not self.phrase_library:
            return
            
        self.tree_widget.clear()
        categories = self.phrase_library.get_categories()
        
        for category, phrases in categories.items():
            category_item = QTreeWidgetItem(self.tree_widget)
            category_item.setText(0, category)
            category_item.setText(1, f"{len(phrases)} 项")
            
            for phrase in phrases:
                phrase_item = QTreeWidgetItem(category_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, f"{len(phrase)} 字")
        
        self.tree_widget.expandAll()
        self.populate_category_combo()
    
    def populate_category_combo(self):
        """填充分类下拉框"""
        if not self.phrase_library:
            return
            
        self.category_combo.clear()
        categories = self.phrase_library.get_categories()
        for category in categories.keys():
            self.category_combo.addItem(category)
    
    def filter_tree(self):
        """过滤树形显示"""
        keyword = self.search_input.text().strip().lower()
        
        for i in range(self.tree_widget.topLevelItemCount()):
            category_item = self.tree_widget.topLevelItem(i)
            category_visible = False
            
            if not keyword:
                category_item.setHidden(False)
                for j in range(category_item.childCount()):
                    category_item.child(j).setHidden(False)
                category_visible = True
            else:
                for j in range(category_item.childCount()):
                    phrase_item = category_item.child(j)
                    phrase_text = phrase_item.text(0).lower()
                    
                    if keyword in phrase_text:
                        phrase_item.setHidden(False)
                        category_visible = True
                    else:
                        phrase_item.setHidden(True)
                
                category_item.setHidden(not category_visible)
    
    def add_new_category(self):
        """添加新分类"""
        category_name = self.new_category_input.text().strip()
        if not category_name:
            QMessageBox.warning(self, "警告", "请输入分类名称")
            return
        
        if not self.phrase_library:
            return
            
        categories = self.phrase_library.get_categories()
        if category_name in categories:
            QMessageBox.warning(self, "警告", f"分类 '{category_name}' 已存在")
            return
        
        self.phrase_library.categories[category_name] = []
        self.phrase_library.save_library()
        
        self.new_category_input.clear()
        self.populate_tree()
        
        QMessageBox.information(self, "成功", f"已添加分类 '{category_name}'")
    
    def add_new_phrase(self):
        """添加新短语"""
        phrase_text = self.new_phrase_input.toPlainText().strip()
        category = self.category_combo.currentText()
        
        if not phrase_text:
            QMessageBox.warning(self, "警告", "请输入短语内容")
            return
        
        if not category:
            QMessageBox.warning(self, "警告", "请选择分类")
            return
        
        if not self.phrase_library:
            return
            
        if self.phrase_library.add_phrase(phrase_text, category):
            self.new_phrase_input.clear()
            self.populate_tree()
            QMessageBox.information(self, "成功", f"已添加短语到分类 '{category}'")
        else:
            QMessageBox.warning(self, "失败", "该短语已存在")
    
    def save_library(self):
        """保存词库"""
        if not self.phrase_library:
            return
            
        try:
            self.phrase_library.save_library()
            QMessageBox.information(self, "成功", "词库已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存词库失败: {e}") 