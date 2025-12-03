#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import QTextCodec, QLocale, QCoreApplication, QTranslator

from src.ui.main_window import MainWindow

def setup_font():
    """设置应用程序字体"""
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    font_path = os.path.join(font_dir, "wqy-microhei.ttc")
    
    if os.path.exists(font_path):
        print(f"加载字体: {font_path}")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                app_font = QFont(font_families[0], 9)
                QApplication.setFont(app_font)

def setup_locale():
    """设置应用程序语言环境"""
    # 设置应用程序为中文
    locale = QLocale(QLocale.Chinese, QLocale.China)
    QLocale.setDefault(locale)
    
    # 设置文本编码为UTF-8
    QTextCodec.setCodecForLocale(QTextCodec.codecForName("UTF-8"))
    
    # 安装翻译器
    translator = QTranslator()
    QCoreApplication.installTranslator(translator)

def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置字体和语言
    setup_font()
    setup_locale()
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 