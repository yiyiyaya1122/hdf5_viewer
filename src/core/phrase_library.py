# -*- coding: utf-8 -*-
import yaml
import os
from typing import Dict, List, Optional


class PhraseMapping:
    """中英文短语映射管理类"""

    def __init__(self, mapping_path: str = "phrase_mapping.yaml"):
        """
        初始化短语映射

        Args:
            mapping_path: 映射文件YAML路径
        """
        self.mapping_path = mapping_path
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.reverse_mappings: Dict[str, str] = {}  # 英文到中文的反向映射
        self.load_mappings()

    def load_mappings(self):
        """从YAML文件加载短语映射"""
        try:
            if os.path.exists(self.mapping_path):
                with open(self.mapping_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                # 解析映射数据结构
                if 'actions' in data:
                    self.mappings = {}
                    self.reverse_mappings = {}  # 重置反向映射
                    for category, phrases in data['actions'].items():
                        category_mappings = {}
                        for phrase_mapping in phrases:
                            if isinstance(phrase_mapping, dict):
                                for chinese, english in phrase_mapping.items():
                                    category_mappings[chinese] = english
                                    # 构建反向映射（英文到中文）
                                    self.reverse_mappings[english] = chinese
                        self.mappings[category] = category_mappings

                print(f"成功加载短语映射，共 {len(self.mappings)} 个分类，{len(self.reverse_mappings)} 个反向映射")
            else:
                print(f"短语映射文件不存在: {self.mapping_path}")
                self.mappings = {}
                self.reverse_mappings = {}
            # print(f"[DEBUG] 短语映射: {self.mappings}")
        except Exception as e:
            print(f"加载短语映射时出错: {e}")
            self.mappings = {}
            self.reverse_mappings = {}

    def get_english_translation(self, chinese_phrase: str, category: str = None) -> Optional[str]:
        """
        获取中文短语的英文翻译，支持分类
        """
        if category and category in self.mappings:
            if chinese_phrase in self.mappings[category]:
                return self.mappings[category][chinese_phrase]
        # 否则全局查找
        for cat, mappings in self.mappings.items():
            if chinese_phrase in mappings:
                return mappings[chinese_phrase]
        return None

    def get_chinese_translation(self, english_phrase: str) -> Optional[str]:
        """
        获取英文短语的中文翻译（反向映射）

        Args:
            english_phrase: 英文短语

        Returns:
            中文翻译，如果找不到则返回None
        """
        return self.reverse_mappings.get(english_phrase)

    def get_category_mappings(self, category: str) -> Dict[str, str]:
        """
        获取指定分类的所有映射

        Args:
            category: 分类名称

        Returns:
            该分类的中英文映射字典
        """
        return self.mappings.get(category, {})

    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        """获取所有映射"""
        return self.mappings.copy()

    def get_categories(self) -> List[str]:
        """获取所有分类名称"""
        return list(self.mappings.keys())


class PhraseLibrary:
    """短语库管理类，用于加载和管理预定义的标注短语"""
    
    def __init__(self, library_path: str = "phrase_library.yaml"):
        """
        初始化短语库
        
        Args:
            library_path: 短语库YAML文件路径
        """
        self.library_path = library_path
        self.phrases: Dict[str, List[str]] = {}
        self.all_phrases: List[str] = []
        self.load_phrases()
    
    def load_phrases(self):
        """从YAML文件加载短语库"""
        try:
            if os.path.exists(self.library_path):
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    self.phrases = yaml.safe_load(f) or {}
                
                # 创建所有短语的扁平列表
                self.all_phrases = []
                for category, phrase_list in self.phrases.items():
                    if isinstance(phrase_list, list):
                        self.all_phrases.extend(phrase_list)
                
                print(f"成功加载短语库，共 {len(self.phrases)} 个分类，{len(self.all_phrases)} 个短语")
            else:
                print(f"短语库文件不存在: {self.library_path}")
                self.create_default_library()
        except Exception as e:
            print(f"加载短语库时出错: {e}")
            self.phrases = {}
            self.all_phrases = []
    
    def create_default_library(self):
        """创建默认的短语库文件"""
        default_phrases = {
            "动作指令": [
                "向前移动", "向后移动", "向左转", "向右转", "停止",
                "加速", "减速", "抓取物体", "放下物体", "观察环境"
            ],
            "状态描述": [
                "任务开始", "任务进行中", "任务完成", "等待指令",
                "发生错误", "系统正常", "需要人工干预"
            ],
            "场景描述": [
                "室内环境", "室外环境", "光线充足", "光线不足",
                "障碍物较多", "路径清晰", "复杂地形", "平坦地面"
            ]
        }
        
        try:
            with open(self.library_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_phrases, f, allow_unicode=True, default_flow_style=False)
            print(f"已创建默认短语库文件: {self.library_path}")
            self.phrases = default_phrases
            self.all_phrases = []
            for phrase_list in default_phrases.values():
                self.all_phrases.extend(phrase_list)
        except Exception as e:
            print(f"创建默认短语库文件时出错: {e}")
    
    def get_categories(self) -> List[str]:
        """获取所有分类名称"""
        return list(self.phrases.keys())
    
    def get_phrases_by_category(self, category: str) -> List[str]:
        """根据分类获取短语列表"""
        return self.phrases.get(category, [])
    
    def get_all_phrases(self) -> List[str]:
        """获取所有短语的扁平列表"""
        return self.all_phrases.copy()
    
    def search_phrases(self, keyword: str) -> List[str]:
        """搜索包含关键词的短语"""
        if not keyword:
            return self.all_phrases.copy()
        
        keyword = keyword.lower()
        matching_phrases = []
        for phrase in self.all_phrases:
            if keyword in phrase.lower():
                matching_phrases.append(phrase)
        return matching_phrases
    
    def add_phrase(self, category: str, phrase: str):
        """添加新短语到指定分类"""
        if category not in self.phrases:
            self.phrases[category] = []
        
        if phrase not in self.phrases[category]:
            self.phrases[category].append(phrase)
            if phrase not in self.all_phrases:
                self.all_phrases.append(phrase)
    
    def save_phrases(self):
        """保存短语库到文件"""
        try:
            with open(self.library_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.phrases, f, allow_unicode=True, default_flow_style=False)
            print(f"短语库已保存到: {self.library_path}")
            return True
        except Exception as e:
            print(f"保存短语库时出错: {e}")
            return False
    
    def reload(self):
        """重新加载短语库"""
        self.load_phrases()
