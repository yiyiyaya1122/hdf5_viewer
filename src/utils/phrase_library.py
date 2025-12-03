#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
from typing import List, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

class PhraseLibrary(QObject):
    """语言短语库管理类"""
    
    # 信号：当词库更新时发出
    library_updated = pyqtSignal()
    
    def __init__(self, library_file: str = "phrase_library.yaml"):
        """
        初始化短语库
        
        Args:
            library_file: 词库文件路径
        """
        super().__init__()
        self.library_file = library_file
        self.phrases = []
        self.categories = {}
        self.load_library()
    
    def load_library(self):
        """加载词库文件"""
        try:
            if os.path.exists(self.library_file):
                with open(self.library_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    
                if data:
                    # 支持简单列表格式
                    if isinstance(data, list):
                        self.phrases = data
                        self.categories = {"默认": data}
                    # 支持分类格式
                    elif isinstance(data, dict):
                        self.categories = data
                        # 合并所有分类的短语
                        self.phrases = []
                        for category, phrases in data.items():
                            if isinstance(phrases, list):
                                self.phrases.extend(phrases)
                    
                    print(f"成功加载词库，共 {len(self.phrases)} 个短语，{len(self.categories)} 个分类")
                else:
                    print("词库文件为空，使用默认配置")
                    self._create_default_library()
            else:
                print(f"词库文件 {self.library_file} 不存在，创建默认词库")
                self._create_default_library()
                
        except Exception as e:
            print(f"加载词库文件时出错: {e}")
            self._create_default_library()
    
    def _create_default_library(self):
        """创建默认词库"""
        default_phrases = {
            "动作指令": [
                "向前移动",
                "向后移动", 
                "向左转",
                "向右转",
                "停止",
                "加速",
                "减速",
                "抓取物体",
                "放下物体",
                "观察环境"
            ],
            "状态描述": [
                "任务开始",
                "任务进行中",
                "任务完成",
                "等待指令",
                "发生错误",
                "系统正常",
                "需要人工干预",
                "数据收集中",
                "环境检测",
                "位置校准"
            ],
            "场景描述": [
                "室内环境",
                "室外环境",
                "光线充足",
                "光线不足",
                "障碍物较多",
                "路径清晰",
                "复杂地形",
                "平坦地面",
                "目标可见",
                "目标遮挡"
            ],
            "交互行为": [
                "与人交互",
                "避开障碍",
                "跟随目标",
                "搜索物体",
                "导航路径",
                "学习行为",
                "重复操作",
                "调整策略",
                "记录数据",
                "发送反馈"
            ]
        }
        
        self.categories = default_phrases
        self.phrases = []
        for category, phrases in default_phrases.items():
            self.phrases.extend(phrases)
        
        # 保存默认词库到文件
        try:
            with open(self.library_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_phrases, f, ensure_ascii=False, default_flow_style=False, 
                         indent=2, allow_unicode=True)
            print(f"已创建默认词库文件: {self.library_file}")
        except Exception as e:
            print(f"保存默认词库时出错: {e}")
    
    def get_all_phrases(self) -> List[str]:
        """获取所有短语"""
        return self.phrases.copy()
    
    def get_categories(self) -> Dict[str, List[str]]:
        """获取分类词库"""
        return self.categories.copy()
    
    def get_phrases_by_category(self, category: str) -> List[str]:
        """获取指定分类的短语"""
        return self.categories.get(category, []).copy()
    
    def add_phrase(self, phrase: str, category: str = "自定义"):
        """
        添加新短语
        
        Args:
            phrase: 短语内容
            category: 分类名称
        """
        if phrase and phrase not in self.phrases:
            self.phrases.append(phrase)
            
            if category not in self.categories:
                self.categories[category] = []
            
            if phrase not in self.categories[category]:
                self.categories[category].append(phrase)
                self.save_library()
                self.library_updated.emit()
                return True
        return False
    
    def remove_phrase(self, phrase: str):
        """
        删除短语
        
        Args:
            phrase: 要删除的短语
        """
        if phrase in self.phrases:
            self.phrases.remove(phrase)
            
            # 从所有分类中删除
            for category in self.categories:
                if phrase in self.categories[category]:
                    self.categories[category].remove(phrase)
            
            self.save_library()
            self.library_updated.emit()
            return True
        return False
    
    def save_library(self):
        """保存词库到文件"""
        try:
            with open(self.library_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.categories, f, ensure_ascii=False, default_flow_style=False,
                         indent=2, allow_unicode=True)
            print("词库已保存")
        except Exception as e:
            print(f"保存词库时出错: {e}")
    
    def search_phrases(self, keyword: str) -> List[str]:
        """
        搜索包含关键词的短语
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的短语列表
        """
        if not keyword:
            return self.phrases.copy()
        
        keyword = keyword.lower()
        return [phrase for phrase in self.phrases if keyword in phrase.lower()]
    
    def reload_library(self):
        """重新加载词库文件"""
        self.load_library()
        self.library_updated.emit() 