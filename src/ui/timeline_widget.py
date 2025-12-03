# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QComboBox, QSpinBox, QInputDialog, QMessageBox, QFrame, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QTimer, QPoint, QDateTime
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QMouseEvent
from typing import Dict, List, Tuple, Optional, Set, Any
import random
import hashlib

# Matplotlib for score plotting
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class TimelineSegment:
    """表示时间轴上的一个段"""
    
    def __init__(self, start: int, end: int, color: QColor, key: str, data_value: Any = None):
        """
        初始化时间轴段
        
        Args:
            start: 起始帧索引
            end: 结束帧索引
            color: 段的颜色
            key: 关联的键
            data_value: 段对应的实际数据值
        """
        self.start = start
        self.end = end
        self.color = color
        self.key = key
        self.data_value = data_value  # 存储实际的数据值
        self.completed = False  # 标记是否已完成标注
        self.subtask = ""  # 段的language描述
        self.hovered = False  # 标记是否被鼠标悬停
    
    def get_color(self, highlight: bool = False) -> QColor:
        """根据状态返回合适的颜色"""
        base_color = self.color
        
        # 如果有数据值，基于数据值生成颜色
        if self.data_value is not None:
            base_color = self._generate_color_from_value(self.data_value)
        # 对于所有已完成的段，使用基于描述文本生成的颜色
        elif self.completed and self.subtask:
            # 使用文本的哈希值生成唯一颜色
            hash_val = hash(self.subtask)
            # 生成不同色相的鲜艳颜色
            h = (hash_val % 360) / 360.0  # 0-1范围的色相值
            s = 0.7  # 高饱和度
            v = 0.9  # 高亮度
            
            result_color = QColor()
            result_color.setHsvF(h, s, v, 1.0)
            base_color = result_color
        
        # 如果悬停或高亮，增加亮度和边框效果
        if self.hovered or highlight:
            # 增加亮度，但保持色调
            h, s, v, a = base_color.getHsvF()
            v = min(1.0, v * 1.3)  # 增加30%亮度
            bright_color = QColor()
            bright_color.setHsvF(h, s, v, a)
            return bright_color
            
        return base_color
    
    def _generate_color_from_value(self, value: Any) -> QColor:
        """
        基于数据值生成颜色
        
        Args:
            value: 数据值
            
        Returns:
            生成的颜色
        """
        # 将值转换为字符串用于哈希
        value_str = str(value)
        
        # 使用MD5哈希确保颜色的一致性和分布
        hash_obj = hashlib.md5(value_str.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # 从哈希值中提取RGB分量
        r = int(hash_hex[0:2], 16)
        g = int(hash_hex[2:4], 16) 
        b = int(hash_hex[4:6], 16)
        
        # 调整颜色使其更加鲜艳和可区分
        # 转换到HSV空间进行调整
        color = QColor(r, g, b)
        h, s, v, a = color.getHsvF()
        
        # 确保饱和度和亮度在合适的范围内
        s = max(0.6, min(0.9, s))  # 饱和度在60%-90%之间
        v = max(0.7, min(0.95, v))  # 亮度在70%-95%之间
        
        result_color = QColor()
        result_color.setHsvF(h, s, v, 1.0)
        
        return result_color
    
    def get_display_text(self) -> str:
        """
        获取要在段上显示的文本
        
        Returns:
            显示文本
        """
        if self.data_value is not None:
            # 如果有数据值，显示数据值
            if isinstance(self.data_value, (int, float)):
                # 数值类型，格式化显示
                if isinstance(self.data_value, float):
                    # 浮点数，保留合适的小数位数
                    if abs(self.data_value) >= 1000:
                        return f"{self.data_value:.1e}"  # 科学计数法
                    elif abs(self.data_value) >= 1:
                        return f"{self.data_value:.2f}"  # 保留2位小数
                    else:
                        return f"{self.data_value:.3f}"  # 保留3位小数
                else:
                    # 整数
                    return str(self.data_value)
            else:
                # 字符串或其他类型
                text = str(self.data_value)
                # 限制显示长度
                if len(text) > 20:
                    return text[:17] + "..."
                return text
        elif self.completed and self.subtask:
            # 如果没有数据值但有language描述，显示描述
            return self.subtask
        else:
            # 都没有，显示键名
            return self.key


class RangeSelector:
    """表示时间轴上的范围选择器"""
    
    def __init__(self, min_val: int, max_val: int):
        """
        初始化范围选择器
        
        Args:
            min_val: 最小值
            max_val: 最大值
        """
        self.min_val = min_val
        self.max_val = max_val
        self.start = min_val
        self.end = max_val
        self.dragging_start = False
        self.dragging_end = False
        self.dragging_range = False
        self.drag_offset = 0
        self.handle_size = 10  # 滑块手柄大小
        self.active = False  # 是否激活选择器
        self.color = QColor(0, 120, 215, 150)  # 选择器颜色
        
        # 吸附相关属性
        self.snap_threshold = 3  # 吸附阈值，当距离小于这个值时会吸附
        self.snap_points = []  # 吸附点列表，存储可以吸附的帧索引
        
        # 实时显示相关属性
        self.dragging_handle = None  # 当前正在拖动的滑块（'start'或'end'）
    
    def contains_start_handle(self, pos: int, total_width: int) -> bool:
        """检查位置是否在起始滑块上"""
        handle_pos = int(self.start / self.max_val * total_width)
        return abs(pos - handle_pos) <= self.handle_size // 2
    
    def contains_end_handle(self, pos: int, total_width: int) -> bool:
        """检查位置是否在结束滑块上"""
        handle_pos = int(self.end / self.max_val * total_width)
        return abs(pos - handle_pos) <= self.handle_size // 2
    
    def contains_range(self, pos: int, total_width: int) -> bool:
        """检查位置是否在范围内"""
        start_pos = int(self.start / self.max_val * total_width)
        end_pos = int(self.end / self.max_val * total_width)
        return start_pos + self.handle_size // 2 <= pos <= end_pos - self.handle_size // 2
    
    def set_start(self, val: int):
        """设置起始值，应用吸附逻辑"""
        # 先计算未吸附的值
        raw_val = max(self.min_val, min(val, self.end - 1))
        
        # 应用吸附逻辑
        if self.snap_points:
            # 找到最近的吸附点
            closest_point = None
            min_distance = float('inf')
            
            for point in self.snap_points:
                if point >= self.min_val and point < self.end:  # 确保吸附点在有效范围内
                    distance = abs(raw_val - point)
                    if distance <= self.snap_threshold and distance < min_distance:
                        closest_point = point
                        min_distance = distance
            
            # 如果找到有效的吸附点，使用它
            if closest_point is not None:
                self.start = closest_point
                return
        
        # 如果没有找到吸附点或不需要吸附，使用原始值
        self.start = raw_val
    
    def set_end(self, val: int):
        """设置结束值，应用吸附逻辑"""
        # 先计算未吸附的值
        raw_val = max(self.start + 1, min(val, self.max_val))
        
        # 应用吸附逻辑
        if self.snap_points:
            # 找到最近的吸附点
            closest_point = None
            min_distance = float('inf')
            
            for point in self.snap_points:
                if point > self.start and point <= self.max_val:  # 确保吸附点在有效范围内
                    distance = abs(raw_val - point)
                    if distance <= self.snap_threshold and distance < min_distance:
                        closest_point = point
                        min_distance = distance
            
            # 如果找到有效的吸附点，使用它
            if closest_point is not None:
                self.end = closest_point
                return
        
        # 如果没有找到吸附点或不需要吸附，使用原始值
        self.end = raw_val
    
    def move_range(self, delta: int):
        """移动整个范围"""
        range_size = self.end - self.start
        new_start = max(self.min_val, min(self.start + delta, self.max_val - range_size))
        self.start = new_start
        self.end = new_start + range_size
    
    def set_snap_points(self, points):
        """设置吸附点列表"""
        self.snap_points = sorted(points)
        print(f"设置吸附点: {self.snap_points}")


class TimelineBar(QWidget):
    """自定义时间轴条组件"""
    
    segmentClicked = pyqtSignal(TimelineSegment)  # 段点击信号
    segmentsMultiSelected = pyqtSignal(list, str)  # 多段选择信号，增加参数传递段所属的键
    frameChanged = pyqtSignal(int)  # 帧变化信号
    rangeSelected = pyqtSignal(int, int, str)  # 范围选择信号，增加key参数
    segmentDeleted = pyqtSignal(TimelineSegment)  # 段删除信号
    
    def __init__(self, parent=None, key: str = ""):
        """
        初始化时间轴条
        
        Args:
            parent: 父窗口部件
            key: 时间轴关联的键
        """
        super().__init__(parent)
        self.setMinimumHeight(45)  # 增加最小高度以容纳标注文本
        self.setMaximumHeight(55)  # 增加最大高度
        self.setMinimumWidth(500)  # 设置最小宽度
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 允许水平方向扩展
        self.segments = []  # 时间轴段列表
        self.total_frames = 100  # 总帧数
        self.current_frame = 0  # 当前帧
        self.completed_color = QColor(0, 128, 0)  # 已完成的颜色
        self.key = key  # 关联的键
        self.range_selector = RangeSelector(0, self.total_frames)  # 范围选择器
        self.hovered_segment = None  # 当前鼠标悬停的段
        self.selected_segments = []  # 多选模式下选中的段
        self.is_multi_select_mode = False  # 是否处于多选模式
        self.ctrl_was_pressed = False  # 记录Ctrl键是否被按下

        # 拖拽相关属性
        self.dragging_segment = None  # 当前拖拽的段
        self.drag_mode = None  # 拖拽模式：'move', 'resize_left', 'resize_right'
        self.drag_start_pos = None  # 拖拽开始位置
        self.drag_start_frame = None  # 拖拽开始时的帧位置

        # 启用鼠标跟踪
        self.setMouseTracking(True)

        # 设置焦点策略使组件能接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
    
    def set_key(self, key: str):
        """设置关联的键"""
        self.key = key
        self.update()
    
    def set_total_frames(self, frames: int):
        """设置总帧数"""
        self.total_frames = max(1, frames)
        self.range_selector.max_val = self.total_frames
        self.update()
    
    def set_current_frame(self, frame: int):
        """设置当前帧"""
        prev_frame = self.current_frame
        self.current_frame = max(0, min(frame, self.total_frames - 1))
        
        # 重绘
        self.update()

        # 更新score垂直指示线位置（如果已绘制）
        try:
            self.update_score_vline()
        except Exception:
            pass
        
        # 只有在帧实际变化时才发出信号
        if prev_frame != self.current_frame:
            print(f"发出帧变化信号: {self.current_frame}")
            # 发出帧变化信号
            self.frameChanged.emit(self.current_frame)
        else:
            print(f"帧未变化，不发送信号")
            
        print(f"*** TimelineBar({self.key}).set_current_frame完成 ***\n")
    
    def add_segment(self, segment: TimelineSegment):
        """添加时间轴段"""
        self.segments.append(segment)
        self.update()
    
    def clear_segments(self):
        """清除所有时间轴段"""
        self.segments.clear()
        self.update()
    
    def remove_segments_by_key(self, key: str):
        """移除指定键的所有段"""
        self.segments = [seg for seg in self.segments if seg.key != key]
        self.update()
    
    def set_segment_completed(self, segment: TimelineSegment, completed: bool, subtask: str = ""):
        """设置段的完成状态"""
        segment.completed = completed
        segment.subtask = subtask
        self.update()
    
    def toggle_range_selector(self, active: bool):
        """切换范围选择器的激活状态"""
        self.range_selector.active = active
        if active:
            print(f"TimelineBar({self.key}): 激活范围选择器")
        else:
            print(f"TimelineBar({self.key}): 关闭范围选择器")
        self.update()
    
    def get_selected_range(self) -> Tuple[int, int]:
        """获取选中的范围"""
        return (self.range_selector.start, self.range_selector.end)
    
    def paintEvent(self, event):
        """绘制时间轴"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()

        # 为键名称预留顶部空间
        timeline_top = 15  # 时间轴绘制区域的顶部位置
        timeline_height = height - timeline_top - 5  # 时间轴绘制区域的高度

        # 绘制背景
        painter.fillRect(0, 0, width, height, QColor(240, 240, 240))

        # 绘制时间轴区域背景（稍微深一点的颜色）
        painter.fillRect(0, timeline_top, width, timeline_height, QColor(250, 250, 250))
        
        # 计算时间轴水平位置的帧索引值
        def frame_to_pos(frame):
            return int(frame / self.total_frames * width)
        
        # 绘制所有段
        for segment in self.segments:
            start_pos = frame_to_pos(segment.start)
            end_pos = frame_to_pos(segment.end)
            segment_width = end_pos - start_pos + 1
            
            # 使用段的颜色或已完成的颜色
            if segment.completed:
                color = segment.get_color()  # 使用基于描述的颜色
            else:
                color = segment.get_color()
                
            # 判断是否在多选模式下被选中
            if segment in self.selected_segments:
                # 为被选中的段绘制更明显的高亮效果
                # 使用更亮的颜色填充（在时间轴区域内）
                highlight_color = color.lighter(150)
                painter.fillRect(start_pos, timeline_top, segment_width, timeline_height, highlight_color)

                # 绘制醒目的边框（更粗的边框）
                painter.setPen(QPen(QColor(255, 165, 0), 3, Qt.SolidLine))  # 橙色边框
                painter.drawRect(start_pos + 1, timeline_top + 1, segment_width - 2, timeline_height - 3)

                # 绘制内部边框增强效果
                painter.setPen(QPen(QColor(255, 255, 255, 180), 1, Qt.SolidLine))  # 半透明白色内边框
                painter.drawRect(start_pos + 2, timeline_top + 2, segment_width - 4, timeline_height - 5)

                # 绘制选中标记（更大的标记）
                painter.setPen(QPen(Qt.white, 2))
                painter.setBrush(QBrush(QColor(255, 165, 0)))  # 橙色标记
                marker_size = 10
                marker_y = timeline_top + timeline_height // 2 - marker_size // 2
                painter.drawEllipse(start_pos + segment_width // 2 - marker_size // 2,
                                  marker_y, marker_size, marker_size)

                # 在标记中心绘制白色小点
                painter.setPen(QPen(Qt.white, 1))
                painter.setBrush(QBrush(Qt.white))
                inner_size = 4
                inner_y = timeline_top + timeline_height // 2 - inner_size // 2
                painter.drawEllipse(start_pos + segment_width // 2 - inner_size // 2,
                                  inner_y, inner_size, inner_size)
            else:
                painter.fillRect(start_pos, timeline_top, segment_width, timeline_height, color)
            
            # 如果是悬停的段或已完成的段，绘制边框和标签
            if segment == self.hovered_segment or (segment.completed and segment.subtask) or segment.data_value is not None:
                # 为当前段绘制边框（在时间轴区域内）
                if segment == self.hovered_segment:
                    painter.setPen(QPen(Qt.black, 2))
                    painter.drawRect(start_pos, timeline_top, segment_width, timeline_height - 1)

                # 绘制文本标签（优先显示数据值，其次是language描述）
                display_text = segment.get_display_text()
                if display_text and segment_width > 30:  # 降低最小宽度要求
                    # 绘制文本标签
                    painter.setPen(Qt.black)

                    # 设置字体
                    font = painter.font()
                    font.setBold(True)
                    font.setPointSize(8)
                    painter.setFont(font)

                    # 裁剪文本以适应段宽度
                    text_width = painter.fontMetrics().width(display_text)

                    if text_width > segment_width - 10:
                        # 如果文本太长，截断并添加省略号
                        display_text = painter.fontMetrics().elidedText(display_text, Qt.ElideRight, segment_width - 10)

                    # 在段中居中绘制文本（在时间轴区域内）
                    text_rect = QRect(start_pos + 5, timeline_top, segment_width - 10, timeline_height)
                    painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, display_text)
        
        # 绘制范围选择器（在时间轴区域内）
        if self.range_selector.active:
            start_pos = frame_to_pos(self.range_selector.start)
            end_pos = frame_to_pos(self.range_selector.end)

            # 绘制选择范围
            painter.fillRect(start_pos, timeline_top, end_pos - start_pos, timeline_height, self.range_selector.color)

            # 绘制滑块手柄
            handle_size = self.range_selector.handle_size
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QBrush(Qt.white))

            # 起始手柄
            painter.drawRect(start_pos - handle_size // 2, timeline_top, handle_size, timeline_height)

            # 结束手柄
            painter.drawRect(end_pos - handle_size // 2, timeline_top, handle_size, timeline_height)
            
            # 绘制帧数标签
            # 设置字体
            font = painter.font()
            font.setBold(True)
            font.setPointSize(8)
            painter.setFont(font)
            
            # 起始帧标签
            start_label = f"帧: {self.range_selector.start}"
            painter.setPen(Qt.black)
            painter.drawText(start_pos - 50, height + 15, 100, 20, Qt.AlignCenter, start_label)
            
            # 结束帧标签
            end_label = f"帧: {self.range_selector.end}"
            painter.setPen(Qt.black)
            painter.drawText(end_pos - 50, height + 15, 100, 20, Qt.AlignCenter, end_label)
        
        # 绘制当前帧指示器（跨越整个高度，包括标题区域）
        current_pos = frame_to_pos(self.current_frame)
        painter.setPen(QPen(Qt.red, 2))
        painter.drawLine(current_pos, 0, current_pos, height)
        
        # 绘制键名称在时间轴上方
        if self.key:
            painter.setPen(Qt.black)
            # 设置更小的字体
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            # 将文本绘制在时间轴上方，留出足够空间
            painter.drawText(5, 12, self.key)
    
    def mousePressEvent(self, event: QMouseEvent):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 获取鼠标位置对应的帧
            width = self.width()
            pos = event.x()
            frame = int(pos / width * self.total_frames)

            # 检查是否在范围选择器上
            if self.range_selector.active:
                if self.range_selector.contains_start_handle(pos, width):
                    self.range_selector.dragging_start = True
                    self.range_selector.dragging_handle = 'start'
                    # 发送帧变化信号以显示起始滑块位置的帧
                    self.frameChanged.emit(self.range_selector.start)
                    return
                elif self.range_selector.contains_end_handle(pos, width):
                    self.range_selector.dragging_end = True
                    self.range_selector.dragging_handle = 'end'
                    # 发送帧变化信号以显示结束滑块位置的帧
                    self.frameChanged.emit(self.range_selector.end)
                    return
                elif self.range_selector.contains_range(pos, width):
                    self.range_selector.dragging_range = True
                    # 使用本地的frame_to_pos函数
                    start_pos = int(self.range_selector.start / self.total_frames * width)
                    self.range_selector.drag_offset = pos - start_pos
                    return

            # 判断是否处于多选模式（按住Ctrl键）
            ctrl_pressed = event.modifiers() & Qt.ControlModifier
            self.is_multi_select_mode = ctrl_pressed

            # 记录Ctrl键状态
            self.ctrl_was_pressed = ctrl_pressed

            # 查找是否点击在段上
            clicked_segment = None
            for segment in self.segments:
                if segment.start <= frame <= segment.end:
                    clicked_segment = segment
                    break

            if clicked_segment:
                if self.is_multi_select_mode:
                    # 多选模式：切换段的选中状态
                    if clicked_segment in self.selected_segments:
                        self.selected_segments.remove(clicked_segment)
                        print(f"取消选中段 {clicked_segment.start}-{clicked_segment.end}")
                    else:
                        self.selected_segments.append(clicked_segment)
                        print(f"选中段 {clicked_segment.start}-{clicked_segment.end}")

                    # 更新UI
                    self.update()
                else:
                    # 非多选模式：检查是否开始拖拽
                    segment_start_pos = int(clicked_segment.start / self.total_frames * width)
                    segment_end_pos = int(clicked_segment.end / self.total_frames * width)

                    # 检查点击位置，确定拖拽模式
                    if abs(pos - segment_start_pos) <= 5:  # 点击左边缘
                        self.dragging_segment = clicked_segment
                        self.drag_mode = 'resize_left'
                        self.drag_start_pos = pos
                        self.drag_start_frame = frame
                        self.setCursor(Qt.SizeHorCursor)
                        print(f"开始调整段左边界: {clicked_segment.start}-{clicked_segment.end}")
                    elif abs(pos - segment_end_pos) <= 5:  # 点击右边缘
                        self.dragging_segment = clicked_segment
                        self.drag_mode = 'resize_right'
                        self.drag_start_pos = pos
                        self.drag_start_frame = frame
                        self.setCursor(Qt.SizeHorCursor)
                        print(f"开始调整段右边界: {clicked_segment.start}-{clicked_segment.end}")
                    else:  # 点击段的中间部分
                        # 选中段
                        self.selected_segments.clear()
                        self.selected_segments.append(clicked_segment)

                        # 开始移动拖拽
                        self.dragging_segment = clicked_segment
                        self.drag_mode = 'move'
                        self.drag_start_pos = pos
                        self.drag_start_frame = frame
                        self.setCursor(Qt.ClosedHandCursor)

                        # 发送段点击信号
                        self.segmentClicked.emit(clicked_segment)
                        print(f"选中并开始移动段: {clicked_segment.start}-{clicked_segment.end}")

                    self.update()
            else:
                # 未点击在段上
                if not self.is_multi_select_mode:
                    # 非多选模式，清除已选择的段
                    self.selected_segments.clear()
                    # 更新当前帧
                    self.current_frame = min(max(0, frame), self.total_frames - 1)
                    self.update()
                    # 发出当前帧变化信号
                    self.frameChanged.emit(self.current_frame)
        elif event.button() == Qt.RightButton:
            if self.selected_segments:
                self.selected_segments.clear()
                self.update()
                print("清除所有选中的段")

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """处理鼠标双击事件 - 用于编辑段的标注"""
        if event.button() == Qt.LeftButton:
            # 获取鼠标位置对应的帧
            width = self.width()
            pos = event.x()
            frame = int(pos / width * self.total_frames)

            # 查找是否双击在段上
            clicked_segment = None
            for segment in self.segments:
                if segment.start <= frame <= segment.end:
                    clicked_segment = segment
                    break

            if clicked_segment:
                # 弹出编辑对话框
                self.edit_segment_annotation(clicked_segment)

    def edit_segment_annotation(self, segment):
        """编辑段的标注"""
        from src.ui.phrase_selection_dialog import PhraseSelectionDialog
        from src.core.phrase_library import PhraseLibrary

        current_text = segment.subtask if segment.subtask else ""
        phrase_library = PhraseLibrary()
        dialog = PhraseSelectionDialog(
            self,
            phrase_library,
            current_text,
            segment.start,
            segment.end
        )

        if dialog.exec_() == dialog.Accepted:
            text = dialog.get_description()
            new_start, new_end = dialog.get_time_interval()
            time_changed = dialog.has_time_changed()

            # 更新时间窗口数据
            parent_widget = self.parent()
            if hasattr(parent_widget, 'time_windows'):
                for i, window in enumerate(parent_widget.time_windows):
                    if window[0] == segment.start and window[1] == segment.end:
                        if time_changed:
                            # 检查新的时间区间是否与其他窗口重合（排除当前窗口）
                            conflict = False
                            for j, other_window in enumerate(parent_widget.time_windows):
                                if i != j:  # 排除当前窗口
                                    other_start, other_end = other_window[0], other_window[1]
                                    if not (new_end < other_start or new_start > other_end):
                                        conflict = True
                                        break

                            if conflict:
                                from PyQt5.QtWidgets import QMessageBox
                                QMessageBox.warning(self, "时间区间冲突",
                                                  f"新的时间区间 {new_start}-{new_end} 与现有窗口重合")
                                return

                            # 更新时间窗口数据
                            parent_widget.time_windows[i] = [new_start, new_end, text.strip()]

                            # 更新段的时间和描述
                            segment.start = new_start
                            segment.end = new_end
                            segment.subtask = text.strip()
                            segment.completed = bool(segment.subtask)

                            # 更新颜色
                            if text.strip():
                                segment.color = QColor(50, 150, 50)
                            else:
                                segment.color = QColor(100, 150, 200)

                            print(f"更新段时间和标注: {segment.start}-{segment.end}, 标注: '{segment.subtask}'")
                        else:
                            # 只更新描述
                            parent_widget.time_windows[i] = [window[0], window[1], text.strip()]
                            segment.subtask = text.strip()
                            segment.completed = bool(segment.subtask)

                            # 更新颜色
                            if text.strip():
                                segment.color = QColor(50, 150, 50)
                            else:
                                segment.color = QColor(100, 150, 200)

                            print(f"更新段标注: {segment.start}-{segment.end}, 标注: '{segment.subtask}'")
                        break

            self.update()

            # 通知主窗口更新subtask信息显示
            if hasattr(parent_widget, 'update_subtask_info_display'):
                current_frame = parent_widget.timeline_widget.get_current_frame()
                parent_widget.update_subtask_info_display(current_frame)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """处理鼠标移动事件"""
        pos = event.pos()
        x = pos.x()
        width = self.width()

        # 如果范围选择器激活，处理拖动
        if self.range_selector.active:
            if self.range_selector.dragging_start:
                # 拖动起始滑块
                frame_idx = int(x / width * self.total_frames)
                self.range_selector.set_start(frame_idx)
                # 发送帧变化信号以显示起始滑块位置的帧
                self.frameChanged.emit(self.range_selector.start)
                self.update()
            elif self.range_selector.dragging_end:
                # 拖动结束滑块
                frame_idx = int(x / width * self.total_frames)
                self.range_selector.set_end(frame_idx)
                # 发送帧变化信号以显示结束滑块位置的帧
                self.frameChanged.emit(self.range_selector.end)
                self.update()
            elif self.range_selector.dragging_range:
                # 拖动整个范围
                frame_idx = int(x / width * self.total_frames)
                delta = frame_idx - self.range_selector.drag_offset
                self.range_selector.move_range(delta)
                self.range_selector.drag_offset = frame_idx
                self.update()
        elif self.dragging_segment:
            # 处理段的拖拽 - 使用智能边界调整
            current_frame = int(x / width * self.total_frames)

            if self.drag_mode == 'move':
                # 移动整个段 - 使用智能边界调整
                delta = current_frame - self.drag_start_frame
                new_start = max(0, self.dragging_segment.start + delta)
                new_end = min(self.total_frames - 1, self.dragging_segment.end + delta)

                # 确保段不会超出边界
                if new_end - new_start == self.dragging_segment.end - self.dragging_segment.start:
                    # 使用智能边界调整
                    adjusted_start, adjusted_end = self.adjust_window_boundaries_smart(
                        self.dragging_segment, new_start, new_end, 'move'
                    )
                    self.dragging_segment.start = adjusted_start
                    self.dragging_segment.end = adjusted_end
                    self.update()

            elif self.drag_mode == 'resize_left':
                # 调整段的左边界 - 使用智能边界调整
                new_start = max(0, min(current_frame, self.dragging_segment.end - 1))
                adjusted_start, adjusted_end = self.adjust_window_boundaries_smart(
                    self.dragging_segment, new_start, self.dragging_segment.end, 'resize_left'
                )
                self.dragging_segment.start = adjusted_start
                self.dragging_segment.end = adjusted_end
                self.update()

            elif self.drag_mode == 'resize_right':
                # 调整段的右边界 - 使用智能边界调整
                new_end = min(self.total_frames - 1, max(current_frame, self.dragging_segment.start + 1))
                adjusted_start, adjusted_end = self.adjust_window_boundaries_smart(
                    self.dragging_segment, self.dragging_segment.start, new_end, 'resize_right'
                )
                self.dragging_segment.start = adjusted_start
                self.dragging_segment.end = adjusted_end
                self.update()
        else:
            # 检查鼠标是否悬停在某个段上，并设置合适的光标
            frame_idx = int(x / width * self.total_frames)

            old_hovered = self.hovered_segment
            self.hovered_segment = None
            cursor_set = False

            for segment in self.segments:
                if segment.start <= frame_idx <= segment.end:
                    self.hovered_segment = segment
                    segment.hovered = True

                    # 检查是否在段的边缘，设置合适的光标
                    segment_start_pos = int(segment.start / self.total_frames * width)
                    segment_end_pos = int(segment.end / self.total_frames * width)

                    if abs(x - segment_start_pos) <= 5:  # 左边缘
                        self.setCursor(Qt.SizeHorCursor)
                        cursor_set = True
                    elif abs(x - segment_end_pos) <= 5:  # 右边缘
                        self.setCursor(Qt.SizeHorCursor)
                        cursor_set = True
                    else:  # 段的中间部分
                        self.setCursor(Qt.OpenHandCursor)
                        cursor_set = True

                    # 设置工具提示
                    if segment.data_value is not None:
                        # 优先显示数据值
                        self.setToolTip(f"{segment.key}: {segment.data_value} (帧: {segment.start}-{segment.end})")
                    elif segment.subtask:
                        self.setToolTip(f"{segment.subtask} (帧: {segment.start}-{segment.end})")
                    else:
                        self.setToolTip(f"{segment.key}: 帧 {segment.start}-{segment.end}")

                    break
                else:
                    segment.hovered = False

            if not cursor_set:
                # 没有悬停在段上，恢复默认光标并清除工具提示
                self.setCursor(Qt.ArrowCursor)
                self.setToolTip("")

            # 如果悬停状态发生变化，重绘
            if old_hovered != self.hovered_segment:
                if old_hovered:
                    old_hovered.hovered = False
                self.update()
    
    def leaveEvent(self, event):
        """处理鼠标离开事件"""
        # 清除悬停状态
        if self.hovered_segment:
            self.hovered_segment.hovered = False
            self.hovered_segment = None
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """处理鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            # 处理范围选择器的拖拽结束
            if self.range_selector.dragging_start or self.range_selector.dragging_end or self.range_selector.dragging_range:
                self.range_selector.dragging_start = False
                self.range_selector.dragging_end = False
                self.range_selector.dragging_range = False
                self.range_selector.dragging_handle = None

                # 设置焦点，以便能够接收键盘事件
                self.setFocus()

            # 处理段拖拽结束
            elif self.dragging_segment:
                print(f"结束拖拽段: {self.dragging_segment.start}-{self.dragging_segment.end}")

                # 如果是annotation键的段，需要同步所有时间窗口数据
                if self.dragging_segment.key == "annotation":
                    timeline_widget = self.parent()
                    if timeline_widget and hasattr(timeline_widget, 'time_windows'):
                        # 同步所有段到time_windows数据
                        self.sync_segments_to_time_windows(timeline_widget)
                        
                        # 打印同步后的数据用于调试
                        print("同步后的time_windows数据:")
                        for i, window in enumerate(timeline_widget.time_windows):
                            print(f"  [{i}]: {window}")

                        # 更新主窗口的subtask信息显示
                        if hasattr(timeline_widget, 'parent') and timeline_widget.parent() and \
                           hasattr(timeline_widget.parent(), 'update_subtask_info_display'):
                            current_frame = timeline_widget.get_current_frame()
                            timeline_widget.parent().update_subtask_info_display(current_frame)

                # 重置拖拽状态
                self.dragging_segment = None
                self.drag_mode = None
                self.drag_start_pos = 0
                self.drag_start_frame = 0

                # 恢复默认光标
                self.setCursor(Qt.ArrowCursor)

                # 设置焦点，以便能够接收键盘事件
                self.setFocus()

                # 重绘
                self.update()

    def sync_segments_to_time_windows(self, timeline_widget):
        """
        将所有段数据同步到time_windows
        
        Args:
            timeline_widget: 时间轴组件
        """
        # 获取所有annotation段的当前状态
        current_segments = []
        for segment in self.segments:
            if segment.key == "annotation":
                current_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'subtask': getattr(segment, 'subtask', ''),
                    'segment': segment
                })
        
        # 按起始帧排序
        current_segments.sort(key=lambda x: x['start'])
        
        # 清空并重新构建time_windows
        timeline_widget.time_windows.clear()
        for seg_data in current_segments:
            timeline_widget.time_windows.append([
                seg_data['start'],
                seg_data['end'],
                seg_data['subtask']
            ])
        
        print(f"同步了 {len(current_segments)} 个段到time_windows")
    
    def keyReleaseEvent(self, event):
        """处理键盘释放事件"""
        # 检测Ctrl键松开
        if event.key() == Qt.Key_Control and self.ctrl_was_pressed:
            print("检测到Ctrl键松开")
            self.ctrl_was_pressed = False
            
            # 如果有选中的段，发送多选信号
            if self.selected_segments:
                print(f"Ctrl松开后发送多选信号，选中 {len(self.selected_segments)} 个段")
                self.segmentsMultiSelected.emit(self.selected_segments, self.key)
        
        super().keyReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 处理Enter键
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            print(f"TimelineBar({self.key}): 检测到Enter键")
            if self.range_selector.active:
                print(f"TimelineBar({self.key}): 范围选择模式下确认选择")
                # 获取当前选择的范围
                start, end = self.range_selector.start, self.range_selector.end
                print(f"TimelineBar({self.key}): 发送范围选择信号 {start}-{end}")
                # 发送范围选择信号
                self.rangeSelected.emit(start, end, self.key)
            else:
                print(f"TimelineBar({self.key}): 不在范围选择模式下，传递给父类")
                super().keyPressEvent(event)
        # 处理ESC键，退出范围选择模式
        elif event.key() == Qt.Key_Escape and self.range_selector.active:
            print(f"TimelineBar({self.key}): ESC键，取消范围选择")
            self.toggle_range_selector(False)
        # 处理方向键，用于调整滑块位置
        elif self.range_selector.active and (event.key() == Qt.Key_Left or event.key() == Qt.Key_Right):
            step = 1 if event.key() == Qt.Key_Right else -1
            
            # 判断当前是否有正在拖动的滑块
            if self.range_selector.dragging_handle == 'start':
                # 调整起始滑块
                self.range_selector.set_start(self.range_selector.start + step)
                # 更新显示的帧
                self.frameChanged.emit(self.range_selector.start)
                self.update()
            elif self.range_selector.dragging_handle == 'end':
                # 调整结束滑块
                self.range_selector.set_end(self.range_selector.end + step)
                # 更新显示的帧
                self.frameChanged.emit(self.range_selector.end)
                self.update()
            else:
                # 如果没有正在拖动的滑块，默认调整起始滑块
                self.range_selector.dragging_handle = 'start'
                self.range_selector.set_start(self.range_selector.start + step)
                # 更新显示的帧
                self.frameChanged.emit(self.range_selector.start)
                self.update()
            print(f"TimelineBar({self.key}): 调整滑块位置，当前控制: {self.range_selector.dragging_handle}")
        # 处理上下方向键，用于切换控制的滑块
        elif self.range_selector.active and (event.key() == Qt.Key_Up or event.key() == Qt.Key_Down):
            # 切换控制的滑块
            if self.range_selector.dragging_handle == 'start':
                self.range_selector.dragging_handle = 'end'
                # 更新显示的帧
                self.frameChanged.emit(self.range_selector.end)
                print(f"TimelineBar({self.key}): 切换到控制结束滑块")
            else:
                self.range_selector.dragging_handle = 'start'
                # 更新显示的帧
                self.frameChanged.emit(self.range_selector.start)
                print(f"TimelineBar({self.key}): 切换到控制起始滑块")
            self.update()
        # 处理Backspace键，删除选中的段
        elif event.key() == Qt.Key_Backspace and self.selected_segments:
            print(f"TimelineBar({self.key}): 检测到Backspace键，删除选中的段")
            # 删除所有选中的段
            for segment in self.selected_segments[:]:  # 使用切片复制避免修改列表时的问题
                print(f"删除段: {segment.start}-{segment.end}")
                # 从segments列表中移除
                if segment in self.segments:
                    self.segments.remove(segment)
                # 发送删除信号
                self.segmentDeleted.emit(segment)

            # 清空选中列表
            self.selected_segments.clear()
            self.update()
        else:
            super().keyPressEvent(event)

    def adjust_window_boundaries_smart(self, current_segment, new_start, new_end, operation_type):
        """
        智能调整时间窗口边界，自动调整前后窗口以避免重叠
        
        Args:
            current_segment: 当前正在操作的段
            new_start: 新的起始帧
            new_end: 新的结束帧
            operation_type: 操作类型 ('move', 'resize_left', 'resize_right')
        
        Returns:
            (adjusted_start, adjusted_end): 调整后的起始和结束帧
        """
        # 获取父组件的时间窗口数据
        parent_widget = self.parent()
        if not parent_widget or not hasattr(parent_widget, 'time_windows'):
            return new_start, new_end
        
        # 找到当前段对应的时间窗口索引
        # 使用subtask来匹配，这是最可靠的方式
        current_segment_subtask = getattr(current_segment, 'subtask', '')
        current_window_index = None
        
        for i, (start, end, description) in enumerate(parent_widget.time_windows):
            if description == current_segment_subtask:
                current_window_index = i
                break
        
        if current_window_index is None:
            print(f"警告: 未找到段对应的时间窗口，subtask: '{current_segment_subtask}'")
            return new_start, new_end
        
        print(f"智能边界调整: 当前段 {current_segment.start}-{current_segment.end}, 目标: {new_start}-{new_end}, 操作: {operation_type}")
        
        # 按起始帧排序时间窗口
        sorted_windows = sorted(enumerate(parent_widget.time_windows), key=lambda x: x[1][0])
        
        # 找到当前窗口在排序后的位置
        current_sorted_index = None
        for i, (orig_index, window) in enumerate(sorted_windows):
            if orig_index == current_window_index:
                current_sorted_index = i
                break
        
        if current_sorted_index is None:
            return new_start, new_end
        
        # 获取前后窗口
        prev_window = None
        next_window = None
        prev_orig_index = None
        next_orig_index = None
        
        if current_sorted_index > 0:
            prev_orig_index, prev_window = sorted_windows[current_sorted_index - 1]
        
        if current_sorted_index < len(sorted_windows) - 1:
            next_orig_index, next_window = sorted_windows[current_sorted_index + 1]
        
        # 根据操作类型进行智能调整
        if operation_type == 'move':
            # 移动操作：保持窗口大小不变，调整位置
            window_width = new_end - new_start + 1
            
            # 检查与前一个窗口的重叠
            if prev_window:
                prev_start, prev_end, _ = prev_window
                if new_start <= prev_end:
                    # 有重叠，调整到前一个窗口之后
                    new_start = prev_end + 1
                    new_end = new_start + window_width - 1
                    print(f"智能边界调整: 检测到与前一个窗口重叠，调整到 {new_start}-{new_end}")
            
            # 检查与后一个窗口的重叠
            if next_window:
                next_start, next_end, _ = next_window
                if new_end >= next_start:
                    # 有重叠，调整到后一个窗口之前
                    new_end = next_start - 1
                    new_start = new_end - window_width + 1
                    print(f"智能边界调整: 检测到与后一个窗口重叠，调整到 {new_start}-{new_end}")
            
            # 确保不超出总帧数范围
            if new_start < 0:
                new_start = 0
                new_end = window_width - 1
            if new_end >= self.total_frames:
                new_end = self.total_frames - 1
                new_start = new_end - window_width + 1
        
        elif operation_type == 'resize_left':
            # 左边界调整：可能影响前一个窗口
            if prev_window:
                prev_start, prev_end, _ = prev_window
                if new_start <= prev_end:
                    # 与前一窗口重叠，调整前一窗口的结束位置
                    new_start = prev_end + 1
                    # 更新前一窗口的结束位置
                    parent_widget.time_windows[prev_orig_index] = [prev_start, new_start - 1, prev_window[2]]
                    print(f"智能边界调整: 调整前一个窗口结束位置: {prev_end} -> {new_start - 1}")
                    
                    # 更新前一窗口对应的段
                    self.update_segment_boundaries(prev_orig_index, prev_start, new_start - 1)
        
        elif operation_type == 'resize_right':
            # 右边界调整：可能影响后一个窗口
            if next_window:
                next_start, next_end, _ = next_window
                if new_end >= next_start:
                    # 与后一窗口重叠，调整后一窗口的起始位置
                    new_end = next_start - 1
                    # 更新后一窗口的起始位置
                    parent_widget.time_windows[next_orig_index] = [new_end + 1, next_end, next_window[2]]
                    print(f"智能边界调整: 调整后一个窗口起始位置: {next_start} -> {new_end + 1}")
                    
                    # 更新后一窗口对应的段
                    self.update_segment_boundaries(next_orig_index, new_end + 1, next_end)
        
        print(f"智能边界调整: 最终结果 {new_start}-{new_end}")
        return new_start, new_end

    def update_segment_boundaries(self, window_index, new_start, new_end):
        """
        更新时间窗口对应的段边界
        
        Args:
            window_index: 时间窗口索引
            new_start: 新的起始帧
            new_end: 新的结束帧
        """
        parent_widget = self.parent()
        if not parent_widget or not hasattr(parent_widget, 'time_windows'):
            return
        
        # 获取窗口信息
        if window_index >= len(parent_widget.time_windows):
            return
        
        # 获取更新后的窗口信息
        start, end, description = parent_widget.time_windows[window_index]
        
        # 查找对应的段并更新
        # 注意：这里我们需要更灵活的匹配方式，因为段可能已经被调整过了
        for segment in self.segments:
            if segment.key == "annotation":
                # 通过subtask匹配，这是最可靠的方式
                segment_subtask = getattr(segment, 'subtask', '')
                if segment_subtask == description:
                    # 找到匹配的段，更新其边界
                    old_start, old_end = segment.start, segment.end
                    segment.start = new_start
                    segment.end = new_end
                    print(f"更新段边界: {old_start}-{old_end} -> {new_start}-{new_end}, 描述: '{description}'")
                    break


class TimelineWidget(QWidget):
    """时间轴窗口部件，包含多个时间轴条和控制按钮"""

    frameChanged = pyqtSignal(int)  # 帧变化信号
    rangeSelected = pyqtSignal(int, int, str)  # 范围选择信号，包含起始、结束帧和键名
    segmentsMultiSelected = pyqtSignal(list, str)  # 多段选择信号，包含段列表和键名
    windowAdded = pyqtSignal(int, int)  # 新增时间窗口信号，包含起始和结束帧

    def __init__(self, parent=None):
        """
        初始化时间轴窗口部件

        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)

        self.total_frames = 100  # 总帧数
        self.current_frame = 0  # 当前帧
        self.fps = 10  # 播放速率，帧/秒
        self.playing = False  # 是否正在播放
        self.timelines = []  # 时间轴条列表
        self.key_colors = {}  # 键到颜色的映射
        self.key_to_timeline = {}  # 键到时间轴条的映射
        self.range_selection_active = False  # 是否激活范围选择
        self.active_timeline = None  # 当前激活的时间轴（用于范围选择）

        # 时间窗口管理相关属性
        self.time_windows = []  # 时间窗口列表，每个元素为(start, end, description)
        self.selected_window = None  # 当前选中的时间窗口
        self.default_window_width = 50  # 默认时间窗口宽度（帧数）
        self.max_windows = 20  # 最大时间窗口数量
        
        # 添加时间窗口创建模式
        self.creating_window_mode = False  # 是否处于创建时间窗口模式
        self.creating_window_start = None  # 正在创建的时间窗口的起始帧

        # 创建定时器
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self.next_frame)
        
        # 创建布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5) # 减少边距
        self.layout.setSpacing(5) # 减少间距
        
        # 添加得分曲线画布（显示在进度条上方）
        # 增加初始 figure 宽度并略微增高，以便线条显示更醒目
        self.score_canvas = FigureCanvas(Figure(figsize=(8, 1.0)))
        # 让画布横向扩展，与进度条同宽；高度固定为较短的条
        self.score_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.score_canvas.setFixedHeight(110)
        self.score_ax = self.score_canvas.figure.subplots()
        # 简化坐标轴样式
        self.score_ax.set_facecolor((1, 1, 1, 0))
        # 给子图增加底部边距，防止 x 轴标签被裁切；左右略微收紧以便利用空间
        try:
            # 增加底部边距，避免 x 轴标签被裁切
            self.score_canvas.figure.subplots_adjust(bottom=0.25, left=0.07, right=0.98, top=0.95)
        except Exception:
            pass
        # x 轴与总帧数对齐（0..total_frames-1）
        self.score_ax.set_xlim(0, max(0, self.total_frames - 1))
        self.score_ax.set_ylim(0, 1)
        self.score_ax.tick_params(axis='both', which='both', length=0)
        self.score_ax.set_yticks([])
        self.score_ax.set_xticks([])
        self.score_line = None
        self.score_vline = None
        self.score_frames = []
        self.score_values = []
        # 将画布添加到主布局（在控制条之上）
        self.layout.addWidget(self.score_canvas)
        
        # 创建控制布局
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8) # 减少控件间距
        
        # 创建帧滑块
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(self.total_frames - 1)
        self.frame_slider.setValue(0)
        self.frame_slider.valueChanged.connect(self.on_slider_value_changed)
        self.frame_slider.setFixedHeight(25)  # 固定滑块高度
        self.frame_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2a82da;
                border: 1px solid #5c5c5c;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #5c9ced;
                border-radius: 3px;
            }
        """)
        
        # 创建帧标签
        self.frame_label = QLabel("帧: 0 / 0")
        self.frame_label.setStyleSheet("font-weight: bold; min-width: 100px; font-size: 11px;")
        self.frame_label.setFixedHeight(25)
        
        # 创建播放/暂停按钮（合并为一个按钮）
        self.play_button = QPushButton("播放")
        self.play_button.setFixedSize(60, 25)  # 减小按钮尺寸
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)

        # 创建FPS控制
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(60)
        self.fps_spinbox.setValue(self.fps)
        self.fps_spinbox.valueChanged.connect(self.on_fps_changed)
        self.fps_spinbox.setFixedSize(50, 25)  # 固定尺寸
        self.fps_spinbox.setStyleSheet("""
            QSpinBox {
                border: 1px solid #bbb;
                border-radius: 3px;
                padding: 2px;
                background: white;
                font-size: 11px;
            }
        """)

        # 创建FPS标签
        fps_label = QLabel("FPS:")
        fps_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        fps_label.setFixedHeight(25)

        # 创建添加时间窗口按钮
        self.add_window_button = QPushButton("添加时间窗口")
        self.add_window_button.setFixedSize(100, 25)
        self.add_window_button.clicked.connect(self.add_time_window)
        self.add_window_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0a5a9c;
            }
        """)

        # 添加清除时间轴按钮
        self.clear_timeline_button = QPushButton("清除时间轴")
        self.clear_timeline_button.setEnabled(False)
        self.clear_timeline_button.clicked.connect(self.clear_timeline_annotations)
        self.clear_timeline_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        # 将控件添加到控制布局
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(fps_label)
        control_layout.addWidget(self.fps_spinbox)
        control_layout.addWidget(self.add_window_button)
        control_layout.addWidget(self.clear_timeline_button)
        control_layout.addWidget(self.frame_slider, 1) # 1是拉伸因子
        control_layout.addWidget(self.frame_label)
        
        # 将控制布局添加到主布局
        self.layout.addLayout(control_layout)
        
        # 时间轴区域（移除分隔线以节省空间）
        self.timelines_layout = QVBoxLayout()
        self.timelines_layout.setSpacing(3) # 减少间距
        self.timelines_layout.setContentsMargins(0, 5, 0, 0) # 减少边距
        self.layout.addLayout(self.timelines_layout, 1) # 添加1的拉伸因子，使所有时间轴填充可用空间
        
        # 设置焦点策略，使组件可以接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
    
    def set_total_frames(self, frames: int):
        """设置总帧数"""
        self.total_frames = max(1, frames)
        self.frame_slider.setMaximum(self.total_frames - 1)
        
        for timeline in self.timelines:
            timeline.set_total_frames(self.total_frames)
            
        self.update_frame_label()
        # 保证得分图的 x 轴与总帧数对齐
        try:
            if getattr(self, 'score_ax', None) is not None:
                self.score_ax.set_xlim(0, max(0, self.total_frames - 1))
                if getattr(self, 'score_canvas', None) is not None:
                    self.score_canvas.draw_idle()
        except Exception:
            pass
    
    def set_current_frame(self, frame: int):
        """设置当前帧"""
        prev_frame = self.current_frame
        self.current_frame = max(0, min(frame, self.total_frames - 1))
        
        # 更新帧滑块的值（避免循环触发）
        if self.frame_slider.value() != self.current_frame:
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(self.current_frame)
            self.frame_slider.blockSignals(False)
        
        # 更新帧标签
        self.update_frame_label()
        
        # 更新所有时间轴的当前帧
        for timeline in self.timelines:
            if timeline.current_frame != self.current_frame:
                # 阻止循环调用
                timeline.blockSignals(True)
                timeline.set_current_frame(self.current_frame)
                timeline.blockSignals(False)
        
        # 重绘
        self.update()

        # 更新score垂直指示线位置（如果已绘制）
        try:
            self.update_score_vline()
        except Exception:
            pass
        
        # 只有在帧实际变化时才发出信号
        if prev_frame != self.current_frame:
            print(f"发出帧变化信号: {self.current_frame}")
            # 发出帧变化信号
            self.frameChanged.emit(self.current_frame)
        else:
            print(f"帧未变化，不发送信号")
        
        print(f"*** TimelineWidget.set_current_frame完成 ***\n")
    
    def update_frame_label(self):
        """更新帧标签"""
        self.frame_label.setText(f"帧: {self.current_frame} / {self.total_frames - 1}")
    
    def on_slider_value_changed(self, value: int):
        """处理滑块值变化"""
        print(f"\n@@@ 滑块值变化: {value} @@@")
        
        # 保存当前帧用于对比
        old_frame = self.current_frame
        
        # 设置当前帧
        self.set_current_frame(value)
        
        # 检查帧是否实际更新
        if old_frame != self.current_frame:
            print(f"帧已更新: {old_frame} -> {self.current_frame}")
        else:
            print(f"帧未变化: 仍为 {self.current_frame}")
        
        # 无论是否帧已经变化，都强制发送信号
        print(f"强制发送帧变化信号: {value}")
        self.frameChanged.emit(value)
        print(f"@@@ 滑块值变化处理完成 @@@\n")
    
    def toggle_play(self):
        """切换播放状态"""
        self.playing = not self.playing
        
        if self.playing:
            self.play_button.setText("暂停")
            # 启动定时器
            interval = 1000 // self.fps  # 计算毫秒间隔
            self.play_timer.start(interval)
        else:
            self.play_button.setText("播放")
            # 停止定时器
            self.play_timer.stop()
    
    def on_fps_changed(self, value: int):
        """处理FPS变化"""
        self.fps = value
        if self.playing:
            # 更新定时器间隔
            interval = 1000 // self.fps
            self.play_timer.setInterval(interval)
    
    def next_frame(self):
        """前进到下一帧"""
        next_frame = (self.current_frame + 1) % self.total_frames
        self.set_current_frame(next_frame)
    
    def toggle_range_selection(self, checked: bool):
        """切换范围选择模式"""
        self.range_selection_active = checked
        
        if checked:
            print("进入范围选择模式")
            # 设置初始选择范围为当前帧附近
            start = max(0, self.current_frame - 10)
            end = min(self.current_frame + 10, self.total_frames - 1)
            
            # 检测language段的边界作为吸附点
            snap_points = self.detect_language_boundaries()
            print(f"检测到的language边界吸附点: {snap_points}")
            
            # 如果指定了活动时间轴，只在该时间轴上激活范围选择器
            if self.active_timeline:
                self.active_timeline.range_selector.start = start
                self.active_timeline.range_selector.end = end
                self.active_timeline.range_selector.set_snap_points(snap_points)
                self.active_timeline.toggle_range_selector(True)
                # 调整时间轴区域大小，确保可以显示帧数标签
                self.active_timeline.setMinimumHeight(65)
                print(f"在时间轴 {self.active_timeline.key} 上激活范围选择器")
            else:
                # 否则在所有时间轴上激活
                for timeline in self.timelines:
                    timeline.range_selector.start = start
                    timeline.range_selector.end = end
                    timeline.range_selector.set_snap_points(snap_points)
                    timeline.toggle_range_selector(True)
                    # 调整时间轴区域大小，确保可以显示帧数标签
                    timeline.setMinimumHeight(65)
                print("在所有时间轴上激活范围选择器")
        else:
            print("退出范围选择模式")
            self.active_timeline = None
            # 在所有时间轴上关闭范围选择器
            for timeline in self.timelines:
                timeline.toggle_range_selector(False)
                # 恢复时间轴高度
                timeline.setMinimumHeight(45)
            print("在所有时间轴上关闭范围选择器")
        
        # 禁用播放按钮，防止在选择范围时播放
        self.play_button.setEnabled(not checked)
    
    def add_timeline(self, key: str = "") -> TimelineBar:
        """
        添加一个新的时间轴条
        
        Args:
            key: 关联的键
            
        Returns:
            创建的时间轴条
        """
        timeline = TimelineBar(self, key)
        timeline.set_total_frames(self.total_frames)
        timeline.set_current_frame(self.current_frame)
        # 将 TimelineBar 的 frameChanged 信号连接到 TimelineWidget 的 set_current_frame 方法
        # 这样当用户点击任何一个时间轴时，所有时间轴都会同步更新
        timeline.frameChanged.connect(self.set_current_frame)
        
        # 连接rangeSelected信号，包含键名
        timeline.rangeSelected.connect(self.on_range_selected)
        
        # 连接多选信号
        timeline.segmentsMultiSelected.connect(self.on_segments_multi_selected)

        # 连接段删除信号
        timeline.segmentDeleted.connect(self.on_segment_deleted)

        # 连接段点击信号到父窗口（如果存在）
        if self.parent() and hasattr(self.parent(), 'on_segment_clicked'):
            timeline.segmentClicked.connect(self.parent().on_segment_clicked)

        self.timelines_layout.addWidget(timeline)
        self.timelines.append(timeline)
        
        if key:
            self.key_to_timeline[key] = timeline
        
        return timeline
    
    def on_range_selected(self, start: int, end: int, key: str):
        """
        处理范围选择
        
        Args:
            start: 起始帧
            end: 结束帧
            key: 关联的键
        """
        print(f"TimelineWidget: 接收到范围选择信号，键 '{key}'，范围 {start}-{end}")
        
        # 关闭范围选择模式
        self.toggle_range_selection(False)
        
        # 发出范围选择信号
        self.rangeSelected.emit(start, end, key)
    
    def on_segments_multi_selected(self, segments, key):
        """
        处理多段选择

        Args:
            segments: 选中的段列表
            key: 段所属的键
        """
        # 不需要查找发送信号的时间轴，因为key已经传递过来了
        # 发出多段选择信号，包含键名
        self.segmentsMultiSelected.emit(segments, key)
        print(f"TimelineWidget: 发送多选信号，键 '{key}'，选中 {len(segments)} 个段")

    def on_segment_deleted(self, segment):
        """
        处理段删除

        Args:
            segment: 被删除的段
        """
        print(f"TimelineWidget: 处理段删除，段 {segment.start}-{segment.end}")

        # 如果是annotation键的段，需要从time_windows列表中移除对应的窗口
        if segment.key == "annotation":
            # 查找并移除对应的时间窗口
            for i, (start, end, description) in enumerate(self.time_windows):
                if start == segment.start and end == segment.end:
                    removed_window = self.time_windows.pop(i)
                    print(f"从time_windows中移除窗口: {removed_window}")
                    break

            # 更新清除按钮状态
            self.update_clear_button_state()

            # 更新主窗口的subtask信息显示
            if self.parent() and hasattr(self.parent(), 'update_subtask_info_display'):
                current_frame = self.get_current_frame()
                self.parent().update_subtask_info_display(current_frame)
    
    def clear_segments(self):
        """清除所有时间轴上的所有段"""
        for timeline in self.timelines:
            timeline.clear_segments()
        
        # 清空时间轴映射并移除所有时间轴
        for timeline in list(self.timelines):
            self.timelines_layout.removeWidget(timeline)
            timeline.hide()
            timeline.deleteLater()
        
        self.timelines.clear()
        self.key_to_timeline.clear()
    
    def add_timeline_for_language(self) -> TimelineBar:
        """
        专门为language创建时间轴
        
        Returns:
            创建的时间轴条
        """
        return self.add_timeline_for_key("language")
    
    def add_timeline_for_key(self, key: str) -> TimelineBar:
        """
        为指定键创建时间轴
        
        Args:
            key: 键名
            
        Returns:
            创建的时间轴条
        """
        # 如果已经存在该键的时间轴，直接返回
        if key in self.key_to_timeline:
            return self.key_to_timeline[key]
        
        # 为该键设置特殊的颜色
        if key not in self.key_colors:
            if key == "language":
                self.key_colors[key] = QColor(60, 180, 75)  # 醒目的绿色
            else:
                # 为其他键生成基于键名的固定颜色
                hash_val = int(hashlib.md5(key.encode()).hexdigest()[:6], 16)
                r = 100 + (hash_val & 0x7F)  # 100-227
                g = 100 + ((hash_val >> 8) & 0x7F)  # 100-227
                b = 100 + ((hash_val >> 16) & 0x7F)  # 100-227
                self.key_colors[key] = QColor(r, g, b)
        
        # 先检查是否已经存在标签，避免重复创建
        existing_label = None
        label_text = f"{key}标签轨道:"
        for i in range(self.timelines_layout.count()):
            item = self.timelines_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QLabel) and label_text in widget.text():
                    existing_label = widget
                    break
        
        # 创建特殊的键时间轴
        timeline = self.add_timeline(key)
        
        # 将该键时间轴移到合适的位置
        self.timelines_layout.removeWidget(timeline)
        
        # 如果是language键，放在最上方；否则按字母顺序排列
        if key == "language":
            insert_index = 0 if not existing_label else 1
        else:
            # 找到合适的插入位置（按字母顺序）
            insert_index = self.timelines_layout.count()
            for i in range(self.timelines_layout.count()):
                item = self.timelines_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'key') and widget.key > key:
                        insert_index = i
                        break
        
        self.timelines_layout.insertWidget(insert_index, timeline)
        
        # 只有在没有已存在的标签时才创建新标签
        if not existing_label:
            # 为该键时间轴添加标题标签
            key_label = QLabel(f"{key}标签轨道:")
            key_label.setStyleSheet(f"""
                font-weight: bold; 
                color: #{self.key_colors[key].red():02x}{self.key_colors[key].green():02x}{self.key_colors[key].blue():02x}; 
                font-size: 13px; 
                padding: 5px; 
                background-color: #f0f8ff;
                border-radius: 4px;
                margin-top: 10px;
            """)
            key_label.setAlignment(Qt.AlignCenter)
            
            # 插入标签到时间轴上方
            label_insert_index = insert_index if insert_index > 0 else 0
            self.timelines_layout.insertWidget(label_insert_index, key_label)
        
        # 设置timeline的最小高度，使其更加明显
        timeline.setMinimumHeight(50)
        
        return timeline
    
    def add_segment(self, key: str, start: int, end: int) -> TimelineSegment:
        """
        添加一个段到对应键的时间轴
        
        Args:
            key: 关联的键
            start: 起始帧
            end: 结束帧
            
        Returns:
            创建的段对象
        """
        # 确保键有一个固定的颜色
        if key not in self.key_colors:
            if key == "language":
                # 为language使用特殊的颜色
                self.key_colors[key] = QColor(60, 180, 75)  # 醒目的绿色
            else:
                # 随机生成一个颜色，但避免太亮或太暗
                r = random.randint(50, 200)
                g = random.randint(50, 200)
                b = random.randint(50, 200)
                self.key_colors[key] = QColor(r, g, b)
        
        # 如果是language键，确保它总是显示在最上方
        if key == "language":
            # 使用专门的方法创建language时间轴
            if key not in self.key_to_timeline:
                self.add_timeline_for_language()
        else:
            # 如果键没有对应的时间轴，创建一个
            if key not in self.key_to_timeline:
                timeline = self.add_timeline(key)
                self.key_to_timeline[key] = timeline
        
        # 获取对应的时间轴
        timeline = self.key_to_timeline[key]
        
        # 创建段
        segment = TimelineSegment(start, end, self.key_colors[key], key)
        timeline.add_segment(segment)
        
        return segment
    
    def add_segment_with_value(self, key: str, start: int, end: int, value: Any) -> TimelineSegment:
        """
        添加一个带有数据值的段到对应键的时间轴
        
        Args:
            key: 关联的键
            start: 起始帧
            end: 结束帧
            value: 数据值
            
        Returns:
            创建的段对象
        """
        # 确保键有一个固定的颜色（作为备用颜色）
        if key not in self.key_colors:
            if key == "language":
                # 为language使用特殊的颜色
                self.key_colors[key] = QColor(60, 180, 75)  # 醒目的绿色
            else:
                # 随机生成一个颜色，但避免太亮或太暗
                r = random.randint(50, 200)
                g = random.randint(50, 200)
                b = random.randint(50, 200)
                self.key_colors[key] = QColor(r, g, b)
        
        # 如果是language键，确保它总是显示在最上方
        if key == "language":
            # 使用专门的方法创建language时间轴
            if key not in self.key_to_timeline:
                self.add_timeline_for_language()
        else:
            # 如果键没有对应的时间轴，创建一个
            if key not in self.key_to_timeline:
                timeline = self.add_timeline(key)
                self.key_to_timeline[key] = timeline
        
        # 获取对应的时间轴
        timeline = self.key_to_timeline[key]
        
        # 创建带有数据值的段
        segment = TimelineSegment(start, end, self.key_colors[key], key, value)
        timeline.add_segment(segment)
        
        return segment
    
    def set_segment_completed(self, segment: TimelineSegment, completed: bool, subtask: str = ""):
        """设置段的完成状态"""
        if segment.key in self.key_to_timeline:
            timeline = self.key_to_timeline[segment.key]
            for seg in timeline.segments:
                if seg is segment:
                    timeline.set_segment_completed(seg, completed, subtask)
                    return
    
    def remove_segments_by_key(self, key: str):
        """移除指定键的所有段"""
        if key in self.key_to_timeline:
            timeline = self.key_to_timeline[key]
            timeline.clear_segments()
            
            # 隐藏并移除对应的时间轴
            index = self.timelines.index(timeline)
            self.timelines.remove(timeline)
            timeline.hide()
            self.timelines_layout.removeWidget(timeline)
            
            # 如果是language键，还需要移除上方的标签
            if key == "language":
                # 查找language标签并移除
                for i in range(self.timelines_layout.count()):
                    item = self.timelines_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, QLabel) and "Language标签轨道" in widget.text():
                            widget.hide()
                            self.timelines_layout.removeWidget(widget)
                            widget.deleteLater()
                            break
            
            del self.key_to_timeline[key]
    
    def get_current_frame(self) -> int:
        """获取当前帧索引"""
        return self.current_frame
    
    def set_frame_count(self, frames: int):
        """设置总帧数（兼容接口）"""
        self.set_total_frames(frames)

    def plot_scores(self, frame_scores: Dict[int, float]):
        """绘制每帧得分曲线。frame_scores 为 {frame: score} 映射。"""
        try:
            # 将字典转换为排序的数组
            items = sorted(frame_scores.items())
            if not items:
                # 清除现有图
                self.score_frames = []
                self.score_values = []
                self.score_ax.clear()
                self.score_canvas.draw_idle()
                return

            frames, values = zip(*items)
            self.score_frames = list(frames)
            self.score_values = list(values)

            # 更新坐标轴范围
            self.score_ax.clear()
            # 绘制更粗的折线以提高可见性，并稍微增强填充透明度
            self.score_ax.plot(self.score_frames, self.score_values, color='#2a82da', linewidth=2.2)
            self.score_ax.fill_between(self.score_frames, self.score_values, color='#2a82da', alpha=0.18)
            # 保证 x 轴与时间轴宽度一致
            self.score_ax.set_xlim(0, max(0, self.total_frames - 1))
            # 自动计算y范围但限制在0-1若多数数据在0-1
            ymin = min(self.score_values)
            ymax = max(self.score_values)
            if ymin >= 0 and ymax <= 1:
                self.score_ax.set_ylim(0, 1)
            else:
                self.score_ax.set_ylim(min(0, ymin), max(1, ymax))

            # 设置刻度和标签（保持紧凑）
            # X 轴刻度：最多显示 6 个均匀分布的刻度
            try:
                # 使用 MaxNLocator 限制 x 轴主刻度数量，优雅应对大帧数
                from matplotlib.ticker import MaxNLocator
                locator = MaxNLocator(nbins=5, integer=True)
                self.score_ax.xaxis.set_major_locator(locator)
                xticks = self.score_ax.get_xticks()
                # 使用默认字体大小显示刻度标签（取消强制缩小和旋转）
                self.score_ax.set_xticklabels([str(int(x)) for x in xticks], fontsize=6)
                # 让 Figure 自动调整布局以容纳标签
                try:
                    self.score_canvas.figure.tight_layout()
                except Exception:
                    pass
            except Exception:
                # 回退：使用稀疏的手动刻度
                try:
                    import numpy as _np
                    xtick_count = min(4, max(2, int(self.total_frames)))
                    xticks = _np.linspace(0, max(0, self.total_frames - 1), num=xtick_count, dtype=int)
                    self.score_ax.set_xticks(xticks.tolist())
                    # 取消对 x 轴刻度字体大小和旋转的强制设置，使用默认显示
                    self.score_ax.set_xticklabels([str(int(x)) for x in xticks], fontsize=6)
                except Exception:
                    self.score_ax.set_xticks([])

            # Y 轴刻度：如果分数在 [0,1] 内，使用固定刻度；否则使用三个刻度（min, mid, max）
            try:
                if ymin >= 0 and ymax <= 1:
                    yticks = [0.0, 0.25, 0.5, 0.75, 1.0]
                else:
                    mid = (ymin + ymax) / 2.0
                    yticks = [ymin, mid, ymax]
                self.score_ax.set_yticks(yticks)
                self.score_ax.set_yticklabels([f"{y:.2f}" for y in yticks], fontsize=6)
            except Exception:
                self.score_ax.set_yticks([])

            # 添加轴标签（小字体，节省空间）
            try:
                self.score_ax.set_xlabel('Frame', fontsize=8)
                self.score_ax.set_ylabel('Score', fontsize=8)
            except Exception:
                pass

            # 添加当前帧垂直线
            # 添加/更新当前帧的红色垂直线
            if self.score_vline is not None:
                try:
                    self.score_vline.remove()
                except Exception:
                    pass
            self.score_vline = self.score_ax.axvline(self.current_frame, color='r', linewidth=1)

            self.score_canvas.draw_idle()
        except Exception as e:
            print(f"plot_scores error: {e}")

    def update_score_vline(self):
        """更新垂直指示线到当前帧位置"""
        if not hasattr(self, 'score_ax') or self.score_ax is None:
            return
        if getattr(self, 'score_vline', None) is None:
            return
        try:
            # vline is a Line2D; set_xdata for vertical line needs updating of segments
            # remove and redraw for simplicity
            self.score_vline.remove()
            self.score_vline = self.score_ax.axvline(self.current_frame, color='r', linewidth=1)
            self.score_canvas.draw_idle()
        except Exception:
            pass
    
    def reset_segments(self, keys_to_preserve=None):
        """
        重置所有段
        
        Args:
            keys_to_preserve: 要保留的键列表，不会被重置
        """
        if keys_to_preserve is None:
            keys_to_preserve = []
            
        print(f"重置时间轴段，保留键: {keys_to_preserve}")
        
        # 保存要保留的时间轴
        preserved_timelines = {}
        for key in keys_to_preserve:
            if key in self.key_to_timeline:
                preserved_timelines[key] = self.key_to_timeline[key]
                # 从时间轴列表中移除，以避免被清除
                if self.key_to_timeline[key] in self.timelines:
                    self.timelines.remove(self.key_to_timeline[key])
        
        # 清除其他所有时间轴
        self.clear_segments()
        
        # 恢复保留的时间轴
        for key, timeline in preserved_timelines.items():
            self.key_to_timeline[key] = timeline
            self.timelines.append(timeline)
        
        # 如果没有时间轴，则添加一个默认的
        if not self.timelines:
            timeline = self.add_timeline_for_language()
            
            # 连接segmentClicked信号到父窗口（如果存在）
            if self.parent() and hasattr(self.parent(), 'on_segment_clicked'):
                timeline.segmentClicked.connect(self.parent().on_segment_clicked)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 处理Enter键
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            print(f"TimelineWidget: 检测到Enter键")
            if self.range_selection_active:
                # 已经在范围选择模式，但这里不需要处理，因为各个TimelineBar会自己处理
                print("TimelineWidget: 已在范围选择模式，交给活动的时间轴处理")
                super().keyPressEvent(event)
            else:
                # 进入范围选择模式
                print("TimelineWidget: 进入范围选择模式")
                
                # 优先寻找当前编辑键的时间轴
                target_timeline = None
                
                # 从父窗口获取当前编辑键
                if self.parent() and hasattr(self.parent(), 'current_editing_key'):
                    current_editing_key = self.parent().current_editing_key
                    print(f"TimelineWidget: 当前编辑键为 {current_editing_key}")
                    
                    # 查找当前编辑键的时间轴
                    if current_editing_key in self.key_to_timeline:
                        timeline = self.key_to_timeline[current_editing_key]
                        if timeline.isVisible():
                            target_timeline = timeline
                            print(f"TimelineWidget: 找到当前编辑键 {current_editing_key} 的可见时间轴")
                        else:
                            print(f"TimelineWidget: 当前编辑键 {current_editing_key} 的时间轴不可见")
                
                # 如果没有找到当前编辑键的时间轴，寻找任何可见的时间轴
                if not target_timeline:
                    for timeline in self.timelines:
                        if timeline.isVisible():
                            target_timeline = timeline
                            print(f"TimelineWidget: 使用可见的时间轴 {timeline.key}")
                            break
                
                if target_timeline:
                    self.active_timeline = target_timeline
                    print(f"TimelineWidget: 设置活动时间轴为 {self.active_timeline.key}")
                else:
                    print("TimelineWidget: 没有找到可用的时间轴")
                    return
                
                # 激活范围选择模式
                self.toggle_range_selection(True)
                
                # 设置初始范围在当前帧附近
                start = max(0, self.current_frame - 5)
                end = min(self.total_frames - 1, self.current_frame + 5)
                self.active_timeline.range_selector.start = start
                self.active_timeline.range_selector.end = end
                self.active_timeline.update()
                
                # 设置焦点到活动时间轴
                self.active_timeline.setFocus()
        
        # 处理ESC键，退出范围选择模式
        elif event.key() == Qt.Key_Escape and self.range_selection_active:
            print("TimelineWidget: ESC键，退出范围选择模式")
            self.toggle_range_selection(False)
        else:
            # 其他键传递给父类
            super().keyPressEvent(event)

    def detect_language_boundaries(self):
        """
        检测当前编辑键时间轴段的边界作为吸附点
        
        Returns:
            段边界帧索引列表
        """
        snap_points = []
        
        # 优先检测当前编辑键的时间轴
        target_timeline = None
        
        # 从父窗口获取当前编辑键
        if self.parent() and hasattr(self.parent(), 'current_editing_key'):
            current_editing_key = self.parent().current_editing_key
            print(f"detect_language_boundaries: 当前编辑键为 {current_editing_key}")
            
            # 查找当前编辑键的时间轴
            if current_editing_key in self.key_to_timeline:
                timeline = self.key_to_timeline[current_editing_key]
                if timeline.isVisible():
                    target_timeline = timeline
                    print(f"detect_language_boundaries: 使用当前编辑键 {current_editing_key} 的时间轴")
        
        # 如果没有找到当前编辑键的时间轴，使用第一个可见的时间轴
        if not target_timeline:
            for timeline in self.timelines:
                if timeline.isVisible():
                    target_timeline = timeline
                    print(f"detect_language_boundaries: 使用可见的时间轴 {timeline.key}")
                    break
        
        # 收集目标时间轴所有段的边界
        if target_timeline:
            for segment in target_timeline.segments:
                snap_points.append(segment.start)
                snap_points.append(segment.end)
            print(f"detect_language_boundaries: 从 {target_timeline.key} 收集到 {len(snap_points)} 个边界点")
        else:
            print("detect_language_boundaries: 没有找到可用的时间轴")
        
        # 去重并排序
        return sorted(list(set(snap_points)))

    def add_time_window(self):
        """添加新的时间窗口"""
        if len(self.time_windows) >= self.max_windows:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", f"最多只能添加{self.max_windows}个时间窗口")
            return

        # 获取当前帧位置（红色线位置）
        current_frame = self.current_frame
        
        # 检查当前帧位置是否已经在某个时间窗口内
        current_frame_in_window = False
        for start, end, _ in self.time_windows:
            if start <= current_frame <= end:
                current_frame_in_window = True
                break
        
        if current_frame_in_window:
            # 如果当前帧已经在某个时间窗口内，使用原来的逻辑
            start_frame = self.find_next_available_start()
            
            # 检查是否还有足够空间添加新窗口
            if start_frame >= self.total_frames - 1:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "警告", "已到达视频结尾，无法添加更多时间窗口")
                return

            # 计算结束帧，确保不与现有窗口重合
            end_frame = self.calculate_optimal_end_frame(start_frame)
        else:
            # 如果当前帧不在任何时间窗口内，创建以当前帧为结束点的窗口
            # 找到当前帧之前的最后一个时间窗口的结束位置
            last_end = -1  # 如果没有时间窗口，从-1开始
            for start, end, _ in self.time_windows:
                if end < current_frame and end > last_end:
                    last_end = end
            
            # 新窗口从最后一个窗口结束后的下一帧开始，到当前帧结束
            start_frame = last_end + 1
            end_frame = current_frame
            
            # 确保窗口至少有1帧的长度
            if start_frame > end_frame:
                start_frame = end_frame
        
        # 最终检查窗口大小是否合理
        if end_frame < start_frame:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "无法找到合适的位置添加新时间窗口")
            return

        # 双重检查：确保新窗口不与现有窗口重合
        if self.check_window_overlap(start_frame, end_frame):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "新窗口与现有窗口重合，无法添加")
            return

        # 创建新的时间窗口
        new_window = [start_frame, end_frame, ""]  # [start, end, description]
        self.time_windows.append(new_window)

        # 在时间轴上创建对应的段
        self.create_window_segment(new_window)

        # 发出信号通知主窗口
        self.windowAdded.emit(start_frame, end_frame)

        # 确保红色线移动到新创建的时间窗口的结尾位置
        self.set_current_frame(end_frame)

        print(f"添加新时间窗口: {start_frame}-{end_frame} (当前帧: {self.current_frame})")

    def find_next_available_start(self):
        """找到下一个可用的起始位置，确保无缝衔接且不重合"""
        if not self.time_windows:
            # 如果没有时间窗口，从帧0开始
            return 0

        # 按结束帧排序，找到最后一个窗口
        sorted_windows = sorted(self.time_windows, key=lambda w: w[1])
        last_window = sorted_windows[-1]

        # 新窗口从最后一个窗口的结束帧的下一帧开始（无缝衔接）
        next_start = last_window[1] + 1

        # 确保起始位置不超出总帧数
        if next_start >= self.total_frames:
            return self.total_frames - 1

        return next_start

    def calculate_optimal_end_frame(self, start_frame):
        """计算最优的结束帧位置，确保无缝衔接且不重合"""
        # 默认结束位置
        default_end = start_frame + self.default_window_width - 1

        # 确保不超出总帧数
        max_possible_end = self.total_frames - 1

        # 找到所有在start_frame之后开始的窗口，按起始帧排序
        future_windows = [w for w in self.time_windows if w[0] > start_frame]
        future_windows.sort(key=lambda w: w[0])

        # 如果有后续窗口，确保新窗口不与它们重合
        if future_windows:
            next_window_start = future_windows[0][0]
            # 新窗口的结束帧必须在下一个窗口开始前一帧
            max_end_before_next = next_window_start - 1
            default_end = min(default_end, max_end_before_next)

        # 返回最小的合理结束位置
        final_end = min(default_end, max_possible_end)

        # 确保窗口至少有1帧的长度
        if final_end < start_frame:
            final_end = start_frame

        return final_end

    def check_window_overlap(self, start, end):
        """检查新窗口是否与现有窗口重合"""
        for window_start, window_end, _ in self.time_windows:
            # 检查是否有重合
            if not (end < window_start or start > window_end):
                return True
        return False

    def create_window_segment(self, window):
        """为时间窗口创建时间轴段"""
        start, end, description = window

        # 确保有一个时间轴来显示窗口
        if not self.timelines:
            timeline = self.add_timeline("annotation")
        else:
            timeline = self.timelines[0]  # 使用第一个时间轴

        # 创建段
        color = QColor(100, 150, 200) if not description else QColor(50, 150, 50)
        segment = TimelineSegment(start, end, color, "annotation")
        segment.subtask = description
        segment.completed = bool(description)

        timeline.add_segment(segment)

        # 更新清除按钮状态
        self.update_clear_button_state()

        return segment

    def update_window_segment(self, window_index, new_description):
        """更新时间窗口段的描述"""
        if window_index < 0 or window_index >= len(self.time_windows):
            return

        # 更新时间窗口数据
        start, end, old_description = self.time_windows[window_index]
        self.time_windows[window_index] = [start, end, new_description]

        # 查找并更新对应的时间轴段
        for timeline in self.timelines:
            for segment in timeline.segments:
                if (segment.key == "annotation" and
                    segment.start == start and segment.end == end):
                    segment.subtask = new_description
                    segment.completed = bool(new_description)
                    # 更新颜色
                    if new_description:
                        segment.color = QColor(50, 150, 50)
                    else:
                        segment.color = QColor(100, 150, 200)
                    break

        # 重绘时间轴
        self.update()

    def update_window_segment_with_time(self, window_index, old_start, old_end, new_start, new_end, new_description):
        """更新时间窗口段的时间区间和描述"""
        if window_index < 0 or window_index >= len(self.time_windows):
            return

        # 查找并删除旧的时间轴段
        for timeline in self.timelines:
            segments_to_remove = []
            for i, segment in enumerate(timeline.segments):
                if (segment.key == "annotation" and
                    segment.start == old_start and segment.end == old_end):
                    segments_to_remove.append(i)

            # 从后往前删除，避免索引问题
            for i in reversed(segments_to_remove):
                timeline.segments.pop(i)

        # 创建新的时间轴段
        if self.timelines:
            timeline = self.timelines[0]  # 使用第一个时间轴
            color = QColor(50, 150, 50) if new_description else QColor(100, 150, 200)
            segment = TimelineSegment(new_start, new_end, color, "annotation")
            segment.subtask = new_description
            segment.completed = bool(new_description)
            timeline.add_segment(segment)

        # 重绘时间轴
        self.update()

    def save_annotations(self, hdf5_model=None, annotation_field=None):
        """保存标注数据到HDF5文件"""
        # 首先验证时间窗口
        is_valid, error_message = self.validate_time_windows()
        if not is_valid:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "保存验证失败", f"无法保存：{error_message}\n\n请确保所有时间窗口相连且覆盖整个时间范围。")
            return False

        from PyQt5.QtWidgets import QMessageBox
        from src.core.phrase_library import PhraseMapping

        # 如果提供了HDF5模型，直接保存到HDF5文件
        if hdf5_model:
            try:
                # 初始化短语映射
                phrase_mapping = PhraseMapping()

                # 使用提供的字段名，如果没有提供则使用默认的"annotations"
                annotation_key = annotation_field if annotation_field else "annotations"
                success_count = 0

                print(f"保存标注到字段: {annotation_key}")

                # 为每个时间窗口设置标注（只保存英文）
                for start, end, description in self.time_windows:
                    if description:  # 只保存有描述的窗口
                        # 获取英文翻译
                        english_translation = phrase_mapping.get_english_translation(description)

                        # 保存英文标注（如果有映射）或原始中文（如果没有映射）
                        save_text = english_translation if english_translation else description
                        print(f"save text: {save_text}")

                        success = hdf5_model.set_language_for_key(
                            annotation_key, start, end, save_text
                        )
                        if success:
                            success_count += 1
                            if english_translation:
                                print(f"保存英文标注: {description} -> {english_translation}")
                            else:
                                print(f"未找到英文映射，保存原文: {description}")

                if success_count > 0:
                    QMessageBox.information(
                        self, "成功",
                        f"成功保存 {success_count} 个标注到HDF5文件字段 '{annotation_key}' 中"
                    )
                    return True
                else:
                    QMessageBox.warning(self, "警告", "没有有效的标注数据被保存")
                    return False

            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存到HDF5失败: {str(e)}")
                return False

        return False

    def clear_timeline_annotations(self):
        """清除时间轴上的标注"""
        if not self.time_windows:
            return

        # 确认清除
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认清除",
            f"确定要清除时间轴上的 {len(self.time_windows)} 个标注吗？\n\n"
            f"此操作不会影响HDF5文件中已保存的数据。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # 清除时间窗口
        self.time_windows.clear()

        # 清除时间轴上的annotation段
        for timeline in self.timelines:
            timeline.segments = [seg for seg in timeline.segments if seg.key != "annotation"]

        # 禁用清除按钮
        self.clear_timeline_button.setEnabled(False)

        # 更新时间轴显示
        self.update()

        # 通知父窗口更新subtask信息显示
        if self.parent() and hasattr(self.parent(), 'update_subtask_info_display'):
            current_frame = self.get_current_frame()
            self.parent().update_subtask_info_display(current_frame)

        print("已清除时间轴标注")

    def update_clear_button_state(self):
        """更新清除按钮的状态"""
        has_annotations = len(self.time_windows) > 0
        self.clear_timeline_button.setEnabled(has_annotations)

    def load_annotations(self, file_path):
        """加载标注数据"""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 清除现有时间窗口
            self.time_windows.clear()

            # 加载时间窗口
            for annotation in data.get("annotations", []):
                window = [
                    annotation["start_frame"],
                    annotation["end_frame"],
                    annotation.get("description", "")
                ]
                self.time_windows.append(window)
                self.create_window_segment(window)

            print(f"从 {file_path} 加载了 {len(self.time_windows)} 个时间窗口")
            return True

        except Exception as e:
            print(f"加载标注数据失败: {e}")
            return False

    def validate_time_windows(self) -> tuple[bool, str]:
        """
        验证时间窗口是否满足保存条件：
        1. 所有时间窗口相连（无间隙）
        2. 没有重合
        3. 覆盖整个时间范围（从0到total_frames-1）
        
        Returns:
            (is_valid, error_message): 是否有效和错误信息
        """
        if not self.time_windows:
            return False, "没有时间窗口需要保存"
        
        # 按开始帧排序
        sorted_windows = sorted(self.time_windows, key=lambda x: x[0])
        
        # 检查是否从0开始
        if sorted_windows[0][0] != 0:
            return False, f"时间窗口必须从第0帧开始，当前从第{sorted_windows[0][0]}帧开始"
        
        # 检查是否覆盖到最后一帧
        if sorted_windows[-1][1] != self.total_frames - 1:
            return False, f"时间窗口必须覆盖到最后一帧({self.total_frames - 1})，当前到第{sorted_windows[-1][1]}帧"
        
        # 检查相连性和重合性
        for i in range(len(sorted_windows)):
            current_start, current_end, _ = sorted_windows[i]
            
            # 检查当前窗口的有效性
            if current_start > current_end:
                return False, f"时间窗口{i+1}的起始帧({current_start})大于结束帧({current_end})"
            
            # 检查与下一个窗口的连接
            if i < len(sorted_windows) - 1:
                next_start, next_end, _ = sorted_windows[i + 1]
                # 检查是否重合（虽然按开始帧排序后理论上不会重合，但还是要检查）
                if current_end >= next_start:
                    return False, f"时间窗口{i+1}({current_start}-{current_end})与时间窗口{i+2}({next_start}-{next_end})重合"
                
                # 检查是否相连（当前窗口结束帧+1应该等于下一个窗口开始帧）
                if current_end + 1 != next_start:
                    return False, f"时间窗口{i+1}({current_start}-{current_end})与时间窗口{i+2}({next_start}-{next_end})不相连，中间有间隙"
        
        # 检查是否有重复的时间窗口
        window_ranges = [(w[0], w[1]) for w in self.time_windows]
        if len(window_ranges) != len(set(window_ranges)):
            return False, "存在重复的时间窗口"
        
        return True, "验证通过"

    def get_time_coverage_info(self) -> dict:
        """
        获取时间覆盖信息，用于显示当前状态
        
        Returns:
            包含覆盖信息的字典
        """
        if not self.time_windows:
            return {
                "total_frames": self.total_frames,
                "covered_frames": 0,
                "coverage_percentage": 0.0,
                "window_count": 0,
                "gaps": [],
                "overlaps": []
            }
        
        # 按开始帧排序
        sorted_windows = sorted(self.time_windows, key=lambda x: x[0])
        
        # 计算覆盖的帧数
        covered_frames = 0
        gaps = []
        overlaps = []
        
        # 检查从0开始的间隙
        if sorted_windows[0][0] > 0:
            gaps.append(f"0-{sorted_windows[0][0]-1}")
        
        # 检查窗口之间的间隙和重合
        for i in range(len(sorted_windows)):
            current_start, current_end, _ = sorted_windows[i]
            covered_frames += (current_end - current_start + 1)
            
            if i < len(sorted_windows) - 1:
                next_start, next_end, _ = sorted_windows[i + 1]
                
                # 检查间隙
                if current_end + 1 < next_start:
                    gaps.append(f"{current_end+1}-{next_start-1}")
                
                # 检查重合
                if current_end >= next_start:
                    overlaps.append(f"窗口{i+1}({current_start}-{current_end})与窗口{i+2}({next_start}-{next_end})")
        
        # 检查到最后一帧的间隙
        if sorted_windows[-1][1] < self.total_frames - 1:
            gaps.append(f"{sorted_windows[-1][1]+1}-{self.total_frames-1}")
        
        coverage_percentage = (covered_frames / self.total_frames) * 100
        
        return {
            "total_frames": self.total_frames,
            "covered_frames": covered_frames,
            "coverage_percentage": coverage_percentage,
            "window_count": len(self.time_windows),
            "gaps": gaps,
            "overlaps": overlaps
        }