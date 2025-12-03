# -*- coding: utf-8 -*-
import os
import sys
from PyQt5.QtGui import QFontDatabase, QFont

class FontHelper:
    """字体帮助类，用于加载和管理字体"""
    
    @staticmethod
    def init_fonts():
        """初始化应用的字体"""
        # 检查字体目录
        fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'fonts')
        if not os.path.exists(fonts_dir):
            os.makedirs(fonts_dir, exist_ok=True)
        
        # 寻找并加载字体
        font_loaded = False
        font_names = []
        
        # 检查字体目录中的字体
        for font_file in os.listdir(fonts_dir):
            if font_file.lower().endswith(('.ttf', '.otf', '.ttc')):
                font_path = os.path.join(fonts_dir, font_file)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    font_names.extend(font_families)
                    font_loaded = True
                    print(f"加载字体: {font_path} (字体名: {', '.join(font_families)})")
        
        if font_loaded:
            print(f"成功加载字体: {', '.join(font_names)}")
        else:
            print("未加载任何字体，将使用系统默认字体")
        
        return font_loaded
    
    @staticmethod
    def get_chinese_font(size=9):
        """获取支持中文的字体"""
        # 尝试使用多种中文友好的字体
        font_families = [
            "WenQuanYi Micro Hei", "文泉驿微米黑", "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", 
            "AR PL UMing CN", "NSimSun", "新宋体", "SimSun", "宋体", "Source Han Sans CN", "思源黑体",
            "Noto Sans CJK SC", "Noto Sans SC", "Droid Sans Fallback"
        ]
        
        db = QFontDatabase()
        all_families = db.families()
        
        # 输出所有可用字体，帮助调试
        print(f"系统可用字体: {', '.join(all_families[:min(len(all_families), 10)])}...")
        
        # 查找可用的中文字体
        for family in font_families:
            if family in all_families:
                print(f"使用中文字体: {family}")
                return QFont(family, size)
        
        # 如果没有找到特定的中文字体，使用系统默认字体
        default_font = QFont()
        default_font.setPointSize(size)
        print(f"未找到中文字体，使用系统默认字体: {default_font.family()}")
        return default_font 