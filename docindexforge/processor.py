"""
DocIndexForge - 文本处理器模块

提供文本预处理功能：文本清洗、中英文分词、停用词过滤、
英文词干提取、基于TF-IDF的关键词提取。
纯Python标准库实现，零外部依赖。
"""

import math
import re
import string
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter

from .utils import logger


# ============================================================
# 中英文停用词表
# ============================================================

ENGLISH_STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been", "be",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "shall", "can", "need", "dare", "ought", "used", "it", "its",
    "this", "that", "these", "those", "i", "me", "my", "myself", "we", "our",
    "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he",
    "him", "his", "himself", "she", "her", "hers", "herself", "itself", "they",
    "them", "their", "theirs", "themselves", "what", "which", "who", "whom",
    "when", "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "because", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "any", "up", "down", "also", "while", "until", "since", "being", "having",
    "doing", "am", "get", "got", "much", "many", "well", "still", "even",
    "back", "way", "make", "made", "like", "long", "look", "come", "say",
    "said", "new", "one", "two", "first", "last", "know", "take", "people",
    "time", "year", "good", "work", "use", "no", "find", "give", "tell",
}

CHINESE_STOP_WORDS: Set[str] = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "什么", "怎么", "如何", "为什么", "可以", "能", "吗", "呢", "吧", "啊",
    "哦", "嗯", "哈", "呀", "嘛", "啦", "哇", "么", "把", "被", "让", "给",
    "从", "向", "对", "与", "及", "等", "或", "但", "而", "且", "所", "以",
    "之", "其", "此", "该", "每", "各", "个", "中", "里", "后", "前", "时",
    "间", "大", "小", "多", "少", "来", "过", "下", "出", "又", "还", "已",
    "已经", "正在", "将", "会", "应该", "可能", "必须", "需要", "不是",
    "没", "无", "非", "未", "别", "莫", "勿", "仅", "只", "才", "更",
    "最", "比", "同", "当", "为", "因为", "所以", "如果", "虽然", "但是",
    "然而", "不过", "因此", "于是", "然后", "接着", "首先", "其次", "最后",
    "总之", "另外", "此外", "同时", "并且", "或者", "以及", "关于", "通过",
    "根据", "按照", "随着", "除了", "包括", "其中", "进行", "使用", "利用",
    "采用", "实现", "完成", "达到", "成为", "作为", "具有", "存在", "属于",
    "处于", "位于", "涉及", "相关", "基于", "用于", "适用于", "支持",
}


# ============================================================
# 英文词干提取（Porter Stemmer简化版）
# ============================================================

class SimpleStemmer:
    """简化的英文词干提取器，基于Porter算法的常见规则子集。"""

    # 常见后缀及其替换规则
    SUFFIX_RULES = [
        # (后缀模式, 替换后缀, 最小词干长度)
        (r"ational$", "ate", 5),
        (r"tional$", "tion", 5),
        (r"ization$", "ize", 5),
        (r"fulness$", "ful", 5),
        (r"ousness$", "ous", 5),
        (r"iveness$", "ive", 5),
        (r"ment$", "", 4),
        (r"ness$", "", 4),
        (r"tion$", "tion", 4),
        (r"sion$", "sion", 4),
        (r"ally$", "al", 4),
        (r"ency$", "ence", 4),
        (r"ancy$", "ance", 4),
        (r"able$", "able", 4),
        (r"ible$", "ible", 4),
        (r"edly$", "ed", 4),
        (r"ingly$", "ing", 4),
        (r"ing$", "", 4),
        (r"ied$", "i", 3),
        (r"ies$", "i", 3),
        (r"ed$", "", 3),
        (r"ly$", "", 3),
        (r"er$", "", 3),
        (r"es$", "", 3),
        (r"est$", "", 4),
        (r"ful$", "", 4),
        (r"ous$", "", 4),
        (r"ive$", "", 4),
        (r"ize$", "", 4),
        (r"ise$", "", 4),
        (r"ism$", "", 4),
        (r"ist$", "", 4),
        (r"al$", "", 3),
        (r"ic$", "", 3),
    ]

    def stem(self, word: str) -> str:
        """提取英文单词的词干。

        Args:
            word: 英文单词

        Returns:
            词干
        """
        if len(word) <= 2:
            return word

        word_lower = word.lower()

        for pattern, replacement, min_stem in self.SUFFIX_RULES:
            match = re.search(pattern, word_lower)
            if match:
                stem = word_lower[:match.start()] + replacement
                if len(stem) >= min_stem:
                    return stem

        return word_lower


# ============================================================
# 文本处理器
# ============================================================

class TextProcessor:
    """文本预处理器，提供清洗、分词、停用词过滤、词干提取和关键词提取功能。"""

    def __init__(
        self,
        use_stemmer: bool = True,
        use_stopwords: bool = True,
        min_token_length: int = 1,
        custom_stopwords: Optional[Set[str]] = None,
    ):
        """初始化文本处理器。

        Args:
            use_stemmer: 是否启用英文词干提取
            use_stopwords: 是否启用停用词过滤
            min_token_length: 最小词元长度
            custom_stopwords: 自定义停用词集合
        """
        self.use_stemmer = use_stemmer
        self.use_stopwords = use_stopwords
        self.min_token_length = min_token_length
        self.stemmer = SimpleStemmer() if use_stemmer else None

        # 合并停用词
        self.stop_words: Set[str] = ENGLISH_STOP_WORDS | CHINESE_STOP_WORDS
        if custom_stopwords:
            self.stop_words |= custom_stopwords

        # 中文字符范围
        self._chinese_pattern = re.compile(
            r"[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df]"
        )
        # 英文单词模式
        self._english_pattern = re.compile(r"[a-zA-Z]+")
        # 数字模式
        self._number_pattern = re.compile(r"\d+")

    def clean(self, text: str) -> str:
        """清洗文本：去除特殊字符、多余空白。

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 去除控制字符（保留换行和制表符）
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # 去除多余空白行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行首行尾空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # 去除首尾空白
        text = text.strip()
        return text

    def tokenize(self, text: str) -> List[str]:
        """分词：支持中英文混合文本。

        中文按字符切分（单字），英文按空格和标点切分。

        Args:
            text: 输入文本

        Returns:
            词元列表
        """
        tokens: List[str] = []

        # 提取英文单词
        for match in self._english_pattern.finditer(text):
            word = match.group().lower()
            if len(word) >= self.min_token_length:
                tokens.append(word)

        # 提取中文字符（单字）
        for match in self._chinese_pattern.finditer(text):
            char = match.group()
            tokens.append(char)

        # 提取数字
        for match in self._number_pattern.finditer(text):
            num = match.group()
            if len(num) >= self.min_token_length:
                tokens.append(num)

        return tokens

    def filter_stopwords(self, tokens: List[str]) -> List[str]:
        """过滤停用词。

        Args:
            tokens: 词元列表

        Returns:
            过滤后的词元列表
        """
        if not self.use_stopwords:
            return tokens
        return [t for t in tokens if t.lower() not in self.stop_words]

    def stem_tokens(self, tokens: List[str]) -> List[str]:
        """对英文词元进行词干提取。

        Args:
            tokens: 词元列表

        Returns:
            词干提取后的词元列表
        """
        if not self.use_stemmer or self.stemmer is None:
            return tokens

        result = []
        for token in tokens:
            # 只对英文词元进行词干提取
            if re.match(r"^[a-zA-Z]+$", token):
                result.append(self.stemmer.stem(token))
            else:
                result.append(token)
        return result

    def process(self, text: str) -> List[str]:
        """完整的文本处理流程：清洗 -> 分词 -> 停用词过滤 -> 词干提取。

        Args:
            text: 输入文本

        Returns:
            处理后的词元列表
        """
        cleaned = self.clean(text)
        tokens = self.tokenize(cleaned)
        tokens = self.filter_stopwords(tokens)
        tokens = self.stem_tokens(tokens)
        return tokens

    def extract_keywords_tfidf(
        self,
        documents: List[str],
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """基于TF-IDF提取关键词。

        Args:
            documents: 文档文本列表
            top_n: 返回前N个关键词

        Returns:
            (关键词, TF-IDF分数) 列表，按分数降序排列
        """
        if not documents:
            return []

        # 对所有文档进行分词处理
        doc_tokens: List[List[str]] = []
        for doc in documents:
            tokens = self.process(doc)
            doc_tokens.append(tokens)

        # 计算文档频率
        n_docs = len(doc_tokens)
        doc_freq: Counter = Counter()
        for tokens in doc_tokens:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1

        # 计算IDF
        idf: Dict[str, float] = {}
        for token, df in doc_freq.items():
            idf[token] = math.log((n_docs + 1) / (df + 1)) + 1

        # 计算所有文档的TF
        all_tf: Counter = Counter()
        for tokens in doc_tokens:
            tf = Counter(tokens)
            for token, count in tf.items():
                all_tf[token] += count

        # 计算TF-IDF
        tfidf_scores: Dict[str, float] = {}
        for token, tf in all_tf.items():
            tfidf_scores[token] = tf * idf.get(token, 0)

        # 排序并返回前N个
        sorted_keywords = sorted(
            tfidf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_keywords[:top_n]

    def compute_tfidf_vector(
        self,
        text: str,
        idf: Dict[str, float]
    ) -> Dict[str, float]:
        """计算单个文档的TF-IDF向量。

        Args:
            text: 文档文本
            idf: 预计算的IDF字典

        Returns:
            TF-IDF向量（词 -> 权重）
        """
        tokens = self.process(text)
        tf = Counter(tokens)
        total = sum(tf.values()) if tf else 1

        tfidf: Dict[str, float] = {}
        for token, count in tf.items():
            normalized_tf = count / total
            tfidf[token] = normalized_tf * idf.get(token, 0)

        return tfidf

    def compute_idf(self, documents: List[str]) -> Dict[str, float]:
        """计算文档集合的IDF值。

        Args:
            documents: 文档文本列表

        Returns:
            IDF字典（词 -> IDF值）
        """
        n_docs = len(documents)
        if n_docs == 0:
            return {}

        doc_freq: Counter = Counter()
        for doc in documents:
            tokens = set(self.process(doc))
            for token in tokens:
                doc_freq[token] += 1

        idf: Dict[str, float] = {}
        for token, df in doc_freq.items():
            idf[token] = math.log((n_docs + 1) / (df + 1)) + 1

        return idf
