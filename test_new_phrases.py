#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新添加的短语库和映射是否正确加载
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.phrase_library import PhraseLibrary, PhraseMapping

def test_new_phrases():
    """测试新添加的短语"""
    print("=== 测试新添加的短语库和映射 ===\n")
    
    # 测试短语库
    print("1. 测试短语库加载:")
    phrase_library = PhraseLibrary()
    categories = phrase_library.get_categories()
    print(f"   分类数量: {len(categories)}")
    print(f"   所有分类: {categories}")
    
    # 检查新添加的分类
    new_categories = ["冰箱项目流程", "洗衣机项目流程"]
    for category in new_categories:
        if category in categories:
            phrases = phrase_library.get_phrases_by_category(category)
            print(f"   {category}: {len(phrases)} 个短语")
            for phrase in phrases:
                print(f"     - {phrase}")
        else:
            print(f"   ❌ {category}: 未找到")
    
    print(f"\n   总短语数量: {len(phrase_library.get_all_phrases())}")
    
    # 测试短语映射
    print("\n2. 测试短语映射加载:")
    phrase_mapping = PhraseMapping()
    mapping_categories = phrase_mapping.get_categories()
    print(f"   映射分类数量: {len(mapping_categories)}")
    print(f"   映射分类: {mapping_categories}")
    
    # 测试新分类的映射
    for category in new_categories:
        if category in mapping_categories:
            mappings = phrase_mapping.get_category_mappings(category)
            print(f"   {category}: {len(mappings)} 个映射")
            for chinese, english in list(mappings.items())[:3]:  # 只显示前3个
                print(f"     - {chinese} -> {english}")
        else:
            print(f"   ❌ {category}: 映射未找到")
    
    # 测试具体的英文翻译
    print("\n3. 测试具体短语的英文翻译:")
    test_phrases = [
        ("冰箱项目流程", "将桌上食物放入筐中"),
        ("洗衣机项目流程", "移动到洗衣机前"),
        ("冰箱项目流程", "拉开右抽屉"),
        ("洗衣机项目流程", "叠衣服")
    ]
    
    for category, phrase in test_phrases:
        result = phrase_mapping.get_english_translation(phrase, category)
        if result and result[0]:
            english, similar = result
            print(f"   {category} - {phrase}: {english}")
            if similar:
                print(f"     相似表达: {similar}")
        else:
            print(f"   ❌ {category} - {phrase}: 未找到翻译")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_new_phrases() 