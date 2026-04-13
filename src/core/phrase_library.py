# -*- coding: utf-8 -*-
import sys
import yaml
import os
from typing import Dict, List, Optional, Tuple

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class PhraseMapping:
    """中英文短语映射管理类"""

    def __init__(self, mapping_path: str = "phrase_library.yaml"):
        """
        初始化短语映射

        Args:
            mapping_path: 映射文件YAML路径（统一使用 phrase_library.yaml）
        """
        self.mapping_path = get_resource_path(mapping_path)
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.reverse_mappings: Dict[str, str] = {}  # 英文到中文的反向映射
        self.load_mappings()

    def load_mappings(self):
        """
        从YAML文件加载短语映射，支持paraphrases
        """
        try:
            if os.path.exists(self.mapping_path):
                with open(self.mapping_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                # 解析映射数据结构（支持合并后的文件格式）
                if 'actions' in data:
                    self.mappings = {}
                    self.reverse_mappings = {}
                    self.paraphrase_mappings = {}  # 新增：存储paraphrases
                    for category, phrases in data['actions'].items():
                        category_mappings = {}
                        category_paraphrases = {}
                        for phrase_mapping in phrases:
                            if isinstance(phrase_mapping, dict):
                                for chinese, value in phrase_mapping.items():
                                    if isinstance(value, dict):
                                        english = value.get('english', '')
                                        paraphrases = value.get('paraphrases', [])
                                        category_mappings[chinese] = english
                                        category_paraphrases[chinese] = paraphrases
                                        if english:
                                            self.reverse_mappings[english] = chinese
                                        for p in paraphrases:
                                            if isinstance(p, str) and p.strip():
                                                self.reverse_mappings[p.strip()] = chinese
                                    else:
                                        # 兼容旧格式
                                        category_mappings[chinese] = value
                                        category_paraphrases[chinese] = []
                                        self.reverse_mappings[value] = chinese
                        self.mappings[category] = category_mappings
                        if not hasattr(self, 'paraphrase_mappings'):
                            self.paraphrase_mappings = {}
                        self.paraphrase_mappings[category] = category_paraphrases

                print(f"成功加载短语映射，共 {len(self.mappings)} 个分类，{len(self.reverse_mappings)} 个反向映射")
            else:
                print(f"短语映射文件不存在: {self.mapping_path}")
                self.mappings = {}
                self.reverse_mappings = {}
                self.paraphrase_mappings = {}
        except Exception as e:
            print(f"加载短语映射时出错: {e}")
            self.mappings = {}
            self.reverse_mappings = {}
            self.paraphrase_mappings = {}

    def get_english_translation(self, chinese_phrase: str, category: str = None):
        """
        获取中文短语的英文翻译和一个相似英文句子（paraphrase），支持分类
        返回: (main_english, similar_english) 或 None
        """
        # 优先在指定分类下查找
        if category and category in self.mappings:
            if chinese_phrase in self.mappings[category]:
                english = self.mappings[category][chinese_phrase]
                paraphrases = self.paraphrase_mappings.get(category, {}).get(chinese_phrase, [])
                similar = paraphrases[0] if paraphrases else None
                return english, similar
        # 否则全局查找
        for cat, mappings in self.mappings.items():
            if chinese_phrase in mappings:
                english = mappings[chinese_phrase]
                paraphrases = self.paraphrase_mappings.get(cat, {}).get(chinese_phrase, [])
                similar = paraphrases[0] if paraphrases else None
                return english, similar
        return None, None

    def get_synonym_for_english(self, english_phrase: str) -> Optional[str]:
        """
        根据英文短语查找同义词
        
        Args:
            english_phrase: 英文短语
            
        Returns:
            同义词，如果找不到则返回None
        """
        import random  # 在方法开始处导入一次
        
        print(f"DEBUG: get_synonym_for_english 输入: '{english_phrase}'")
        
        # 在所有分类中查找
        for category, mappings in self.mappings.items():
            for chinese, english in mappings.items():
                if english == english_phrase:
                    # 找到匹配的英文，获取其同义词
                    paraphrases = self.paraphrase_mappings.get(category, {}).get(chinese, [])
                    # 构建选择池：原始英文 + 所有同义词
                    choice_pool = [english] + paraphrases
                    if choice_pool:
                        selected_paraphrase = random.choice(choice_pool)  # 随机选择原始英文或同义词
                        print(f"DEBUG: 找到精确匹配 - 分类: {category}, 中文: {chinese}, 英文: {english}, 选择池: {choice_pool}, 选中: {selected_paraphrase}")
                        return selected_paraphrase  # 返回随机选择的结果
                    else:
                        print(f"DEBUG: 找到英文匹配但没有同义词 - 分类: {category}, 中文: {chinese}, 英文: {english}")
                    break
        
        # 如果没有找到，尝试模糊匹配（移除句号等标点）
        clean_phrase = english_phrase.rstrip('.')
        print(f"DEBUG: 尝试模糊匹配，清理后的短语: '{clean_phrase}'")
        
        for category, mappings in self.mappings.items():
            for chinese, english in mappings.items():
                clean_english = english.rstrip('.')
                if clean_english == clean_phrase:
                    # 找到匹配的英文，获取其同义词
                    paraphrases = self.paraphrase_mappings.get(category, {}).get(chinese, [])
                    # 构建选择池：原始英文 + 所有同义词
                    choice_pool = [english] + paraphrases
                    if choice_pool:
                        selected_paraphrase = random.choice(choice_pool)  # 随机选择原始英文或同义词
                        print(f"DEBUG: 找到模糊匹配 - 分类: {category}, 中文: {chinese}, 英文: {english}, 选择池: {choice_pool}, 选中: {selected_paraphrase}")
                        return selected_paraphrase  # 返回随机选择的结果
                    else:
                        print(f"DEBUG: 找到模糊英文匹配但没有同义词 - 分类: {category}, 中文: {chinese}, 英文: {english}")
                    break
        
        print(f"DEBUG: 没有找到任何匹配")
        return None

    @staticmethod
    def _prefix_substring_is_whole_phrase(clean_phrase: str, clean_mapped: str) -> bool:
        """若 clean_mapped 出现在 clean_phrase 开头，要求后面不能接更多英文步骤用语（避免
        'fold shirt' 误匹配 'fold shirt into thirds.'）。"""
        if not clean_phrase.startswith(clean_mapped):
            return True
        rest = clean_phrase[len(clean_mapped) :].lstrip()
        if not rest:
            return True
        if rest[0] in ".,;:!?":
            return True
        # 仍以字母继续，说明 mapped 只是更长句子的前缀，不算同一步骤
        return not rest[0].isalpha()

    def get_chinese_translation(self, english_phrase: str) -> Optional[str]:
        """
        获取英文短语的中文翻译（反向映射）

        Args:
            english_phrase: 英文短语

        Returns:
            中文翻译，如果找不到则返回None
        """
        # 首先尝试精确匹配
        if english_phrase in self.reverse_mappings:
            return self.reverse_mappings[english_phrase]

        clean_phrase = english_phrase.rstrip('.')
        for mapped_english, chinese in self.reverse_mappings.items():
            clean_mapped = mapped_english.rstrip('.')
            if clean_phrase == clean_mapped:
                return chinese

        # 部分匹配：优先最长 mapped（更具体），且拒绝「短语前缀 + 后续仍有英文」的假阳性
        best: Optional[Tuple[int, str]] = None
        for mapped_english, chinese in self.reverse_mappings.items():
            clean_mapped = mapped_english.rstrip('.')
            if clean_phrase in clean_mapped:
                if not PhraseMapping._prefix_substring_is_whole_phrase(
                    clean_mapped, clean_phrase
                ):
                    continue
                score = len(clean_mapped)
                if best is None or score > best[0]:
                    best = (score, chinese)
            elif clean_mapped in clean_phrase:
                if not PhraseMapping._prefix_substring_is_whole_phrase(
                    clean_phrase, clean_mapped
                ):
                    continue
                score = len(clean_mapped)
                if best is None or score > best[0]:
                    best = (score, chinese)

        return best[1] if best else None

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
        self.library_path = get_resource_path(library_path)
        self.phrases: Dict[str, List[str]] = {}
        self.all_phrases: List[str] = []
        self.load_phrases()
    
    def load_phrases(self):
        """从YAML文件加载短语库"""
        try:
            if os.path.exists(self.library_path):
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # 支持合并后的文件格式（包含 phrases 键）和旧格式（直接是分类字典）
                if 'phrases' in data:
                    # 新格式：从 phrases 键读取
                    self.phrases = data.get('phrases', {})
                else:
                    # 旧格式：直接是分类字典
                    self.phrases = data
                
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
            # 如果文件是合并格式，需要保留其他部分
            if os.path.exists(self.library_path):
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    existing_data = yaml.safe_load(f) or {}
                
                # 如果是合并格式，更新 phrases 部分
                if 'phrases' in existing_data or 'actions' in existing_data or 'system_keys' in existing_data:
                    existing_data['phrases'] = self.phrases
                    with open(self.library_path, 'w', encoding='utf-8') as f:
                        yaml.dump(existing_data, f, allow_unicode=True, default_flow_style=False)
                else:
                    # 旧格式，直接保存 phrases
                    with open(self.library_path, 'w', encoding='utf-8') as f:
                        yaml.dump(self.phrases, f, allow_unicode=True, default_flow_style=False)
            else:
                # 文件不存在，直接保存 phrases
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
