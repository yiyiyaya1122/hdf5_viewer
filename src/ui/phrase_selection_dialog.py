# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QTabWidget,
    QLineEdit, QSplitter, QWidget, QMessageBox, QSpinBox,
    QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from src.core.phrase_library import PhraseLibrary, PhraseMapping


class PhraseSelectionDialog(QDialog):
    """短语选择和编辑对话框"""
    
    def __init__(self, parent=None, phrase_library=None, existing_text="", start_frame=0, end_frame=0):
        super().__init__(parent)
        self.original_start_frame = start_frame
        self.original_end_frame = end_frame
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.existing_text = existing_text
        self.phrase_library = phrase_library if phrase_library else PhraseLibrary()
        self.phrase_mapping = PhraseMapping()  # 初始化短语映射

        # 获取父窗口的总帧数用于验证
        self.max_frames = 999999  # 设置一个很大的默认值，不限制帧数
        if hasattr(parent, 'timeline_widget') and hasattr(parent.timeline_widget, 'total_frames'):
            self.max_frames = max(parent.timeline_widget.total_frames, 999999)  # 确保至少有足够大的范围

        if start_frame != 0 or end_frame != 0:
            self.setWindowTitle(f"编辑时间窗口标注 ({start_frame}-{end_frame} 帧)")
        else:
            self.setWindowTitle("编辑标注")
        self.setModal(True)
        self.resize(900, 700)  # 增加窗口大小以容纳时间编辑控件

        self.setup_ui()
        self.load_phrases()

        # 如果有现有文本，设置到编辑框中
        if existing_text:
            self.text_edit.setPlainText(existing_text)
            # 更新英文翻译显示
            self.update_english_translation()
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)

        # 时间区间编辑区域（仅在有时间信息时显示）
        if self.start_frame != 0 or self.end_frame != 0:
            self.setup_time_editing_section(layout)

        # 标题信息
        if self.start_frame != 0 or self.end_frame != 0:
            self.info_label = QLabel()
            self.update_info_label()
        else:
            self.info_label = QLabel("编辑标注内容")
        self.info_label.setStyleSheet("font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(self.info_label)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：短语库选择
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 搜索框
        search_label = QLabel("搜索短语:")
        search_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词搜索...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        left_layout.addWidget(self.search_edit)
        
        # 短语分类标签页
        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)
        
        # 添加选中短语按钮
        add_phrase_btn = QPushButton("添加选中短语")
        add_phrase_btn.clicked.connect(self.add_selected_phrase)
        add_phrase_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        left_layout.addWidget(add_phrase_btn)
        
        splitter.addWidget(left_widget)
        
        # 右侧：文本编辑
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        edit_label = QLabel("标注内容:")
        edit_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(edit_label)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("请输入或选择标注内容...")
        font = QFont()
        font.setPointSize(12)
        self.text_edit.setFont(font)
        # 连接文本变化事件，用于实时更新英文翻译
        self.text_edit.textChanged.connect(self.on_text_changed)
        right_layout.addWidget(self.text_edit)

        # 添加英文翻译显示区域
        english_label = QLabel("英文翻译:")
        english_label.setStyleSheet("font-weight: bold; color: #2E8B57; margin-top: 10px;")
        right_layout.addWidget(english_label)

        self.english_display = QTextEdit()
        self.english_display.setPlaceholderText("英文翻译将在这里显示...")
        self.english_display.setReadOnly(True)
        self.english_display.setMaximumHeight(100)  # 限制高度
        self.english_display.setStyleSheet("""
            QTextEdit {
                background-color: #f0f8ff;
                border: 1px solid #d0e0f0;
                border-radius: 4px;
                padding: 4px;
                color: #2E8B57;
            }
        """)
        english_font = QFont()
        english_font.setPointSize(11)
        self.english_display.setFont(english_font)
        right_layout.addWidget(self.english_display)
        
        # 快速操作按钮
        quick_buttons_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.text_edit.clear)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        quick_buttons_layout.addWidget(clear_btn)
        
        quick_buttons_layout.addStretch()
        right_layout.addLayout(quick_buttons_layout)
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 400])
        
        # 底部按钮
        buttons_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(self.ok_button)
        
        layout.addLayout(buttons_layout)

    def setup_time_editing_section(self, layout):
        """设置时间区间编辑区域"""
        time_group = QGroupBox("时间区间设置")
        time_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        time_layout = QFormLayout(time_group)

        # 开始帧输入
        self.start_frame_spinbox = QSpinBox()
        self.start_frame_spinbox.setRange(0, self.max_frames)  # 移除-1，允许更大的范围
        self.start_frame_spinbox.setValue(self.start_frame)
        self.start_frame_spinbox.valueChanged.connect(self.on_start_frame_changed)
        self.start_frame_spinbox.setStyleSheet("QSpinBox { padding: 5px; }")

        # 结束帧输入
        self.end_frame_spinbox = QSpinBox()
        self.end_frame_spinbox.setRange(0, self.max_frames)  # 移除-1，允许更大的范围
        self.end_frame_spinbox.setValue(self.end_frame)
        self.end_frame_spinbox.valueChanged.connect(self.on_end_frame_changed)
        self.end_frame_spinbox.setStyleSheet("QSpinBox { padding: 5px; }")

        # 持续时间显示
        self.duration_label = QLabel()
        self.update_duration_label()
        self.duration_label.setStyleSheet("color: #666; font-style: italic;")

        time_layout.addRow("开始帧:", self.start_frame_spinbox)
        time_layout.addRow("结束帧:", self.end_frame_spinbox)
        time_layout.addRow("持续时间:", self.duration_label)

        # 重置按钮
        reset_btn = QPushButton("重置为原始值")
        reset_btn.clicked.connect(self.reset_time_values)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        time_layout.addRow("", reset_btn)

        layout.addWidget(time_group)

    def update_info_label(self):
        """更新信息标签"""
        duration = self.end_frame - self.start_frame + 1
        self.info_label.setText(f"时间窗口: {self.start_frame}-{self.end_frame} 帧 (共 {duration} 帧)")

    def update_duration_label(self):
        """更新持续时间标签"""
        duration = self.end_frame - self.start_frame + 1
        self.duration_label.setText(f"{duration} 帧")

    def on_start_frame_changed(self, value):
        """开始帧变化处理"""
        self.start_frame = value
        # 如果开始帧大于等于结束帧，自动调整结束帧
        if value >= self.end_frame:
            self.end_frame_spinbox.setValue(value + 1)
        else:
            self.update_info_label()
            self.update_duration_label()

    def on_end_frame_changed(self, value):
        """结束帧变化处理"""
        self.end_frame = value
        # 只更新显示，不自动调整开始帧
        self.update_info_label()
        self.update_duration_label()

    def reset_time_values(self):
        """重置时间值为原始值"""
        self.start_frame_spinbox.setValue(self.original_start_frame)
        self.end_frame_spinbox.setValue(self.original_end_frame)

    def load_phrases(self):
        """加载短语库到标签页"""
        categories = self.phrase_library.get_categories()
        
        # 添加"所有短语"标签页
        all_phrases_list = QListWidget()
        for phrase in self.phrase_library.get_all_phrases():
            item = QListWidgetItem(phrase)
            all_phrases_list.addItem(item)
        all_phrases_list.itemDoubleClicked.connect(self.on_phrase_double_clicked)
        self.tab_widget.addTab(all_phrases_list, "所有短语")
        
        # 添加分类标签页
        for category in categories:
            phrase_list = QListWidget()
            phrases = self.phrase_library.get_phrases_by_category(category)
            for phrase in phrases:
                item = QListWidgetItem(phrase)
                phrase_list.addItem(item)
            phrase_list.itemDoubleClicked.connect(self.on_phrase_double_clicked)
            self.tab_widget.addTab(phrase_list, category)
    
    def on_search_changed(self, text):
        """搜索文本变化时的处理"""
        # 更新"所有短语"标签页的内容
        all_phrases_widget = self.tab_widget.widget(0)
        if isinstance(all_phrases_widget, QListWidget):
            all_phrases_widget.clear()
            matching_phrases = self.phrase_library.search_phrases(text)
            for phrase in matching_phrases:
                item = QListWidgetItem(phrase)
                all_phrases_widget.addItem(item)
        
        # 切换到"所有短语"标签页显示搜索结果
        if text.strip():
            self.tab_widget.setCurrentIndex(0)
    
    def on_phrase_double_clicked(self, item):
        """双击短语时添加到编辑框"""
        phrase = item.text()
        self.add_phrase_to_text(phrase)
    
    def add_selected_phrase(self):
        """添加当前选中的短语"""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QListWidget):
            current_item = current_widget.currentItem()
            if current_item:
                phrase = current_item.text()
                self.add_phrase_to_text(phrase)
            else:
                QMessageBox.information(self, "提示", "请先选择一个短语")
    
    def add_phrase_to_text(self, phrase):
        """将短语添加到文本编辑框"""
        current_text = self.text_edit.toPlainText()
        if current_text:
            # 如果已有文本，添加分隔符
            if not current_text.endswith(('\n', ' ', '，', '。', '；')):
                current_text += "，"
            new_text = current_text + phrase
        else:
            new_text = phrase

        self.text_edit.setPlainText(new_text)
        # 将光标移到末尾
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()

        # 更新英文翻译显示
        self.update_english_translation()

    def on_text_changed(self):
        """处理文本变化事件"""
        self.update_english_translation()

    def update_english_translation(self):
        """更新英文翻译显示"""
        chinese_text = self.text_edit.toPlainText().strip()
        if not chinese_text:
            self.english_display.setPlainText("")
            return

        # 获取当前tab的分类
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index == 0:
            category = None  # "所有短语"标签
        else:
            category = self.tab_widget.tabText(current_tab_index)
        # print(f"[DEBUG] 当前tab index: {current_tab_index}, 当前分类: {category}")

        # 优先在当前分类下查找
        complete_translation = self.phrase_mapping.get_english_translation(chinese_text, category)
        # print(f"[DEBUG] 查找短语: {chinese_text}, 分类: {category}, 翻译结果: {complete_translation}")
        if complete_translation:
            self.english_display.setPlainText(complete_translation)
            return

        # 如果完整文本没有匹配，则分割文本进行智能翻译
        import re
        phrases = re.split(r'[，。；、]+', chinese_text)
        phrases = [phrase.strip() for phrase in phrases if phrase.strip()]

        english_translations = []
        i = 0
        while i < len(phrases):
            found_translation = False
            for length in range(min(3, len(phrases) - i), 0, -1):
                combined_phrase = "，".join(phrases[i:i+length])
                english = self.phrase_mapping.get_english_translation(combined_phrase, category)
                if english:
                    english_translations.append(english)
                    i += length
                    found_translation = True
                    break
            if not found_translation:
                english_translations.append(f"[{phrases[i]}]")
                i += 1

        if english_translations:
            english_text = ", ".join(english_translations)
            self.english_display.setPlainText(english_text)
        else:
            self.english_display.setPlainText("")

    def get_description(self):
        """获取编辑的描述文本"""
        return self.text_edit.toPlainText().strip()

    def get_selected_phrase(self):
        """获取选中的短语（与get_description相同）"""
        return self.get_description()

    def get_time_interval(self):
        """获取编辑后的时间区间"""
        if hasattr(self, 'start_frame_spinbox') and hasattr(self, 'end_frame_spinbox'):
            return self.start_frame_spinbox.value(), self.end_frame_spinbox.value()
        return self.start_frame, self.end_frame

    def has_time_changed(self):
        """检查时间区间是否发生了变化"""
        if hasattr(self, 'start_frame_spinbox') and hasattr(self, 'end_frame_spinbox'):
            current_start = self.start_frame_spinbox.value()
            current_end = self.end_frame_spinbox.value()
            return (current_start != self.original_start_frame or
                    current_end != self.original_end_frame)
        return False

    def validate_time_interval(self):
        """验证时间区间的有效性"""
        if hasattr(self, 'start_frame_spinbox') and hasattr(self, 'end_frame_spinbox'):
            start = self.start_frame_spinbox.value()
            end = self.end_frame_spinbox.value()

            if start >= end:
                QMessageBox.warning(self, "时间区间错误", "开始帧必须小于结束帧")
                return False

            if start < 0:
                QMessageBox.warning(self, "时间区间错误", "开始帧不能小于0")
                return False

        return True

    def accept(self):
        """重写accept方法，添加时间区间验证"""
        if not self.validate_time_interval():
            return

        # 更新内部的时间值
        if hasattr(self, 'start_frame_spinbox') and hasattr(self, 'end_frame_spinbox'):
            self.start_frame = self.start_frame_spinbox.value()
            self.end_frame = self.end_frame_spinbox.value()

        super().accept()
