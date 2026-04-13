# -*- coding: utf-8 -*-
import hashlib
import sys
import yaml
import os
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# 与 sentence-transformers 默认小型模型同名；放在项目根目录下（与 phrase_library.yaml 同级）
DEFAULT_SEMANTIC_MODEL_DIR = "all-MiniLM-L6-v2"

# 控制台日志前缀：表示「精确键 + 子串规则均未命中」后再用语义相似度对齐词库英文
SIMILARITY_MATCH_LOG_PREFIX = "[句向量相似度匹配]"

# 进程内复用 SentenceTransformer 与词库键编码，避免每次新建 PhraseMapping（切换文件、加载 JSON）都重新读盘与 encode
_semantic_st_model_cache: Dict[str, Any] = {}
_semantic_emb_cache: Dict[Tuple[str, str], Tuple[Any, List[str]]] = {}
_semantic_encode_failed: Set[Tuple[str, str]] = set()

# 翻译匹配表格列宽（终端显示宽度，东亚宽字符计为 2）
_MATCH_COL_NO = 6
_MATCH_COL_DESC = 32
_MATCH_COL_EN = 32
_MATCH_COL_ZH = 22
_MATCH_COL_KIND = 14
_MATCH_TABLE_WIDTHS = (
    _MATCH_COL_NO,
    _MATCH_COL_DESC,
    _MATCH_COL_EN,
    _MATCH_COL_ZH,
    _MATCH_COL_KIND,
)


def _match_hrule() -> str:
    return "+" + "+".join("-" * w for w in _MATCH_TABLE_WIDTHS) + "+"


def _match_display_width(s: str) -> int:
    w = 0
    for c in s:
        if unicodedata.east_asian_width(c) in ("F", "W"):
            w += 2
        else:
            w += 1
    return w


def _match_sanitize(s: str) -> str:
    return (s or "").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _match_fit_width(s: str, max_w: int) -> str:
    s = _match_sanitize(s)
    if _match_display_width(s) <= max_w:
        return s
    out: List[str] = []
    w = 0
    for c in s:
        cw = 2 if unicodedata.east_asian_width(c) in ("F", "W") else 1
        if w + cw > max_w - 1:
            break
        out.append(c)
        w += cw
    return "".join(out) + "…"


def _match_pad_cell(s: str, width: int) -> str:
    s = _match_fit_width(s, width)
    pad = width - _match_display_width(s)
    return s + (" " * max(0, pad))


def _match_pad_center(s: str, width: int) -> str:
    s = _match_fit_width(s, width)
    sw = _match_display_width(s)
    pad = max(0, width - sw)
    left = pad // 2
    right = pad - left
    return " " * left + s + " " * right


def _match_table_row(cells: List[str]) -> str:
    assert len(cells) == len(_MATCH_TABLE_WIDTHS)
    return "|" + "|".join(cells) + "|"


def _project_root_dir() -> str:
    """本文件位于 src/core/phrase_library.py，项目根为其上两级。"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _default_bundled_semantic_model_path() -> Optional[str]:
    # 打包环境：模型可随资源放在 _MEIPASS 下
    try:
        p = os.path.join(sys._MEIPASS, DEFAULT_SEMANTIC_MODEL_DIR)
        if os.path.isdir(p):
            return p
    except Exception:
        pass
    # 开发环境：必须相对项目根解析，不能依赖进程 cwd（IDE/子目录启动时常不是项目根）
    p = os.path.join(_project_root_dir(), DEFAULT_SEMANTIC_MODEL_DIR)
    return p if os.path.isdir(p) else None


class PhraseMapping:
    """中英文短语映射类

    流程：先完备匹配（反向表精确键、去句点相等、带子串前缀校验的最长匹配）；均失败后再
    **句向量相似度匹配**：在词库全部英文键（含 paraphrases）中按余弦相似度取最近邻，超过阈值则
    采用对应中文（实现上与 check_anno_all_task 的 SentenceTransformer + util.cos_sim 一致）。
    安装 sentence-transformers 且项目根存在 all-MiniLM-L6-v2/ 时自动加载；也可用
    PHRASE_SEMANTIC_MODEL_PATH 覆盖；该环境变量设为空字符串则关闭相似度路径。
    阈值由 PHRASE_SEMANTIC_THRESHOLD 控制（默认 0.9）。
    """

    @staticmethod
    def _resolve_semantic_model_path(
        semantic_model_path: Optional[str],
    ) -> Optional[str]:
        if semantic_model_path is not None:
            s = semantic_model_path.strip()
            return s if s else None
        if "PHRASE_SEMANTIC_MODEL_PATH" in os.environ:
            ev = os.environ["PHRASE_SEMANTIC_MODEL_PATH"].strip()
            return ev if ev else None
        return _default_bundled_semantic_model_path()

    def __init__(
        self,
        mapping_path: str = "phrase_library.yaml",
        semantic_model_path: Optional[str] = None,
        semantic_threshold: Optional[float] = None,
    ):
        """
        初始化短语映射

        Args:
            mapping_path: 映射文件YAML路径（统一使用 phrase_library.yaml）
            semantic_model_path: 句向量模型路径或 HuggingFace 名；None 时先读环境变量，再尝试项目内
                all-MiniLM-L6-v2 目录
            semantic_threshold: 余弦相似度阈值；默认读环境变量 PHRASE_SEMANTIC_THRESHOLD 或 0.9
        """
        self.mapping_path = get_resource_path(mapping_path)
        self.mappings: Dict[str, Dict[str, str]] = {}
        self.reverse_mappings: Dict[str, str] = {}  # 英文到中文的反向映射
        self.semantic_model_path = PhraseMapping._resolve_semantic_model_path(
            semantic_model_path
        )
        if semantic_threshold is not None:
            self.semantic_threshold = float(semantic_threshold)
        else:
            self.semantic_threshold = float(
                os.environ.get("PHRASE_SEMANTIC_THRESHOLD", "0.9")
            )
        self._semantic_model: Any = None
        self._semantic_keys: Optional[List[str]] = None
        self._semantic_emb: Any = None
        self._semantic_init_failed = False
        self._translation_match_header_printed = False
        self._translation_match_row_no = 0
        self._translation_match_table_open = False
        self.load_mappings()
        if self.semantic_model_path is None:
            root = _project_root_dir()
            zip_path = os.path.join(root, f"{DEFAULT_SEMANTIC_MODEL_DIR}.zip")
            if os.path.isfile(zip_path):
                print(
                    f"{SIMILARITY_MATCH_LOG_PREFIX} 未找到模型目录 "
                    f"{os.path.join(root, DEFAULT_SEMANTIC_MODEL_DIR)}/ ，"
                    f"但存在 {zip_path} 。\n"
                    f"  若 unzip 报 “End-of-central-directory signature not found”，"
                    f"多为压缩包不完整，请删除后重下，或改用在线模型名（需联网一次）：\n"
                    f'  export PHRASE_SEMANTIC_MODEL_PATH="sentence-transformers/all-MiniLM-L6-v2"\n'
                    f"  解压示例："
                    f' unzip -o "{zip_path}" -d "{root}"'
                )

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

                self._semantic_keys = None
                self._semantic_emb = None
                self._translation_match_header_printed = False
                self._translation_match_row_no = 0
                self._translation_match_table_open = False
                print(f"成功加载短语映射，共 {len(self.mappings)} 个分类，{len(self.reverse_mappings)} 个反向映射")
            else:
                print(f"短语映射文件不存在: {self.mapping_path}")
                self.mappings = {}
                self.reverse_mappings = {}
                self.paraphrase_mappings = {}
                self._semantic_keys = None
                self._semantic_emb = None
                self._translation_match_header_printed = False
                self._translation_match_row_no = 0
                self._translation_match_table_open = False
        except Exception as e:
            print(f"加载短语映射时出错: {e}")
            self.mappings = {}
            self.reverse_mappings = {}
            self.paraphrase_mappings = {}
            self._semantic_keys = None
            self._semantic_emb = None
            self._translation_match_header_printed = False
            self._translation_match_row_no = 0
            self._translation_match_table_open = False

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

    @staticmethod
    def _normalize_for_semantic(desc: str) -> str:
        """与 check_anno_all_task.normalize_description 一致：小写、去空白、句末英文句号。"""
        if not desc:
            return desc
        desc = desc.strip().lower()
        if desc and not desc.endswith("."):
            desc += "."
        return desc

    def _ensure_semantic_index(self) -> bool:
        """懒加载模型并对 reverse_mappings 全部键编码；失败则本实例不再重试。

        模型与编码矩阵在进程内缓存：相同模型路径且词库英文键集合相同时直接复用，切换 HDF5 / 多次
        构造 PhraseMapping 不会重复加载权重或整表 encode。
        """
        if self._semantic_init_failed:
            return False
        if not self.semantic_model_path:
            return False
        if self._semantic_emb is not None and self._semantic_keys is not None:
            return True

        mp = self.semantic_model_path
        keys = sorted(self.reverse_mappings.keys())
        if not keys:
            return False
        keys_sig = hashlib.md5("\n".join(keys).encode("utf-8")).hexdigest()
        cache_emb_key = (mp, keys_sig)
        if cache_emb_key in _semantic_encode_failed:
            self._semantic_init_failed = True
            return False

        hit = _semantic_emb_cache.get(cache_emb_key)
        if hit is not None:
            self._semantic_emb, self._semantic_keys = hit
            self._semantic_model = _semantic_st_model_cache.get(mp)
            return True

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print(
                f"{SIMILARITY_MATCH_LOG_PREFIX} 未安装 sentence-transformers，"
                f"完备匹配失败后将无法使用相似度路径（可 pip install sentence-transformers）。"
            )
            self._semantic_init_failed = True
            return False

        try:
            if mp not in _semantic_st_model_cache:
                print(f"{SIMILARITY_MATCH_LOG_PREFIX} 正在加载句向量模型 {mp!r} …")
                _semantic_st_model_cache[mp] = SentenceTransformer(mp)
            else:
                print(
                    f"{SIMILARITY_MATCH_LOG_PREFIX} 复用已加载模型 {mp!r} ，"
                    f"为当前词库键集编码 {len(keys)} 条英文键 …"
                )
            model = _semantic_st_model_cache[mp]
            emb = model.encode(keys, convert_to_tensor=True, show_progress_bar=False)
            _semantic_emb_cache[cache_emb_key] = (emb, keys)
            self._semantic_model = model
            self._semantic_emb = emb
            self._semantic_keys = keys
            print(
                f"{SIMILARITY_MATCH_LOG_PREFIX} 索引就绪：已编码 {len(keys)} 条词库英文键，"
                f"相似度采纳阈值 cos_sim >= {self.semantic_threshold}"
            )
        except Exception as e:
            print(f"{SIMILARITY_MATCH_LOG_PREFIX} 模型加载或编码失败: {e}")
            self._semantic_model = None
            _semantic_encode_failed.add(cache_emb_key)
            self._semantic_init_failed = True
            return False
        return True

    def begin_translation_match_table_log(self) -> None:
        """每次批量输出翻译对照表前调用：闭合上一张未结束的表，并将编号从 1 重新开始。"""
        if self._translation_match_table_open:
            print(_match_hrule())
        self._translation_match_header_printed = False
        self._translation_match_row_no = 0
        self._translation_match_table_open = False

    def finalize_translation_match_table_log(self) -> None:
        """批量输出结束后调用，打印表格底边。"""
        if self._translation_match_table_open:
            print(_match_hrule())
            self._translation_match_table_open = False

    def _log_translation_match_row(
        self,
        description: str,
        matched_english: str,
        chinese: str,
        match_kind: str,
    ) -> None:
        """控制台 ASCII 表格：编号（居中）、description、matched_english、中文、匹配方式。"""
        w = _MATCH_TABLE_WIDTHS
        if not self._translation_match_header_printed:
            print(_match_hrule())
            print(
                _match_table_row(
                    [
                        _match_pad_center("编号", w[0]),
                        _match_pad_cell("description", w[1]),
                        _match_pad_cell("matched_english", w[2]),
                        _match_pad_cell("中文翻译", w[3]),
                        _match_pad_cell("匹配方式", w[4]),
                    ]
                )
            )
            print(_match_hrule())
            self._translation_match_header_printed = True
            self._translation_match_table_open = True

        self._translation_match_row_no += 1
        print(
            _match_table_row(
                [
                    _match_pad_center(str(self._translation_match_row_no), w[0]),
                    _match_pad_cell(description, w[1]),
                    _match_pad_cell(matched_english, w[2]),
                    _match_pad_cell(chinese, w[3]),
                    _match_pad_cell(match_kind, w[4]),
                ]
            )
        )

    def _semantic_chinese_translation(
        self, english_phrase: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """完备匹配失败后：句向量余弦最近邻。返回 (中文, 词库英文键)，失败为 (None, None)。"""
        if not self._ensure_semantic_index():
            return None, None
        try:
            from sentence_transformers import util
        except ImportError:
            return None, None
        q = self._normalize_for_semantic(english_phrase)
        if not q:
            return None, None
        q_emb = self._semantic_model.encode(
            q, convert_to_tensor=True, show_progress_bar=False
        )
        cosine_score = util.cos_sim(q_emb, self._semantic_emb)[0]
        best_score = cosine_score.max().item()
        best_idx = int(cosine_score.argmax().item())
        key = self._semantic_keys[best_idx]
        zh = self.reverse_mappings.get(key)
        if best_score < self.semantic_threshold:
            return None, None
        return zh, key

    def get_chinese_translation(
        self, english_phrase: str, *, log_match: bool = True
    ) -> Optional[str]:
        """
        获取英文短语的中文翻译（反向映射）

        Args:
            english_phrase: 英文短语
            log_match: 为 False 时不向控制台输出匹配对照表（供 UI 高频绘制等场景）

        Returns:
            中文翻译，如果找不到则返回None
        """
        # 精确键
        if english_phrase in self.reverse_mappings:
            zh = self.reverse_mappings[english_phrase]
            if log_match:
                self._log_translation_match_row(
                    english_phrase, english_phrase, zh, "完全匹配"
                )
            return zh

        clean_phrase = english_phrase.rstrip('.')
        for mapped_english, chinese in self.reverse_mappings.items():
            clean_mapped = mapped_english.rstrip('.')
            if clean_phrase == clean_mapped:
                if log_match:
                    self._log_translation_match_row(
                        english_phrase, mapped_english, chinese, "完全匹配"
                    )
                return chinese

        # 子串匹配：优先最长 mapped，且拒绝「前缀 + 后续仍有英文」假阳性
        best: Optional[Tuple[int, str, str]] = None
        for mapped_english, chinese in self.reverse_mappings.items():
            clean_mapped = mapped_english.rstrip('.')
            if clean_phrase in clean_mapped:
                if not PhraseMapping._prefix_substring_is_whole_phrase(
                    clean_mapped, clean_phrase
                ):
                    continue
                score = len(clean_mapped)
                if best is None or score > best[0]:
                    best = (score, chinese, mapped_english)
            elif clean_mapped in clean_phrase:
                if not PhraseMapping._prefix_substring_is_whole_phrase(
                    clean_phrase, clean_mapped
                ):
                    continue
                score = len(clean_mapped)
                if best is None or score > best[0]:
                    best = (score, chinese, mapped_english)

        if best:
            _, chinese, matched_key = best
            if log_match:
                self._log_translation_match_row(
                    english_phrase, matched_key, chinese, "完全匹配"
                )
            return chinese

        zh, matched_en = self._semantic_chinese_translation(english_phrase)
        if zh is not None and matched_en is not None and log_match:
            self._log_translation_match_row(
                english_phrase, matched_en, zh, "相似度匹配"
            )
        return zh

    def semantic_status(self) -> Dict[str, Any]:
        """诊断句向量相似度路径（不主动加载）。index_built 为 True 表示已编码过词库英文键。"""
        path = self.semantic_model_path
        return {
            "resolved_model_path": path,
            "path_exists": bool(path and os.path.isdir(path)),
            "index_built": self._semantic_emb is not None,
            "num_keys_encoded": len(self._semantic_keys) if self._semantic_keys else 0,
            "init_failed_do_not_retry": self._semantic_init_failed,
        }

    def load_semantic_model_now(self) -> bool:
        """立即加载句向量模型并编码全部词库英文键；成功返回 True（用于自检）。"""
        return self._ensure_semantic_index()

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
