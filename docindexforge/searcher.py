"""
DocIndexForge - 检索引擎模块

提供智能检索功能：多字段搜索、相关度评分排序、
关键词高亮、上下文摘要、模糊匹配、布尔查询。
纯Python标准库实现，零外部依赖。
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter

from .indexer import IndexEngine, IndexedDocument
from .processor import TextProcessor
from .utils import Color, colored, truncate, logger


# ============================================================
# 搜索结果
# ============================================================

class SearchResult:
    """单个搜索结果。"""

    def __init__(
        self,
        doc_id: str,
        score: float,
        title: str,
        filepath: str,
        snippet: str = "",
        highlights: Optional[List[str]] = None,
        matched_terms: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """初始化搜索结果。

        Args:
            doc_id: 文档ID
            score: 相关度分数
            title: 文档标题
            filepath: 文件路径
            snippet: 匹配摘要
            highlights: 高亮片段列表
            matched_terms: 匹配的查询词
            metadata: 文档元数据
        """
        self.doc_id = doc_id
        self.score = score
        self.title = title
        self.filepath = filepath
        self.snippet = snippet
        self.highlights = highlights or []
        self.matched_terms = matched_terms or set()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "doc_id": self.doc_id,
            "score": round(self.score, 4),
            "title": self.title,
            "filepath": self.filepath,
            "snippet": self.snippet,
            "matched_terms": list(self.matched_terms),
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"SearchResult(score={self.score:.4f}, title={self.title!r})"


# ============================================================
# 检索引擎
# ============================================================

class SearchEngine:
    """智能检索引擎，支持多种搜索策略。"""

    def __init__(
        self,
        index_engine: IndexEngine,
        snippet_length: int = 200,
        context_lines: int = 2,
        fuzzy_threshold: int = 2,
    ):
        """初始化检索引擎。

        Args:
            index_engine: 索引引擎实例
            snippet_length: 摘要最大长度
            context_lines: 上下文行数
            fuzzy_threshold: 模糊匹配最大编辑距离
        """
        self.index = index_engine
        self.processor = TextProcessor()
        self.snippet_length = snippet_length
        self.context_lines = context_lines
        self.fuzzy_threshold = fuzzy_threshold

    def search(
        self,
        query: str,
        max_results: int = 20,
        strategy: str = "bm25",
        fields: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """执行搜索。

        Args:
            query: 搜索查询
            max_results: 最大结果数
            strategy: 搜索策略 (bm25, tfidf, boolean)
            fields: 搜索字段 (content, title, all)

        Returns:
            搜索结果列表，按相关度降序排列
        """
        if not query.strip():
            return []

        # 检查是否为布尔查询
        if self._is_boolean_query(query):
            return self._boolean_search(query, max_results)

        # 处理查询
        query_tokens = self.processor.process(query)

        if not query_tokens:
            return []

        # 扩展模糊匹配词
        expanded_tokens = self._expand_fuzzy_tokens(query_tokens)

        # 根据策略搜索
        if strategy == "bm25":
            scored = self._search_bm25(expanded_tokens)
        elif strategy == "tfidf":
            scored = self._search_tfidf(expanded_tokens)
        elif strategy == "boolean":
            scored = self._search_boolean_default(expanded_tokens)
        else:
            logger.warning(f"未知搜索策略: {strategy}，使用BM25")
            scored = self._search_bm25(expanded_tokens)

        # 字段过滤
        if fields:
            scored = self._filter_by_fields(scored, fields)

        # 排序并截取
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []

        for doc_id, score in scored[:max_results]:
            doc = self.index.get_document(doc_id)
            if doc is None:
                continue

            # 生成摘要和高亮
            snippet = self._generate_snippet(doc, expanded_tokens)
            highlights = self._generate_highlights(doc, expanded_tokens)

            result = SearchResult(
                doc_id=doc_id,
                score=score,
                title=doc.title,
                filepath=doc.filepath,
                snippet=snippet,
                highlights=highlights,
                matched_terms=set(expanded_tokens) & set(doc.tokens),
                metadata=doc.metadata,
            )
            results.append(result)

        return results

    # ============================================================
    # BM25 搜索
    # ============================================================

    def _search_bm25(self, query_tokens: List[str]) -> List[Tuple[str, float]]:
        """使用BM25算法搜索。

        Args:
            query_tokens: 查询词元列表

        Returns:
            [(doc_id, score)] 列表
        """
        results: Dict[str, float] = {}

        for token in query_tokens:
            # 模糊匹配扩展
            matching_tokens = self._find_similar_tokens(token)
            for mt in matching_tokens:
                postings = self.index.search_inverted(mt)
                idf_val = self.index.idf.get(mt, 0)

                for doc_id, positions in postings.items():
                    doc = self.index.get_document(doc_id)
                    if doc is None:
                        continue

                    tf = len(positions)
                    doc_len = doc.token_count
                    avg_len = self.index.avg_doc_length if self.index.avg_doc_length > 0 else 1

                    k1 = self.index.k1
                    b = self.index.b

                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_len / avg_len))
                    score = idf_val * numerator / denominator

                    results[doc_id] = results.get(doc_id, 0) + score

        return list(results.items())

    # ============================================================
    # TF-IDF 搜索
    # ============================================================

    def _search_tfidf(self, query_tokens: List[str]) -> List[Tuple[str, float]]:
        """使用TF-IDF余弦相似度搜索。

        Args:
            query_tokens: 查询词元列表

        Returns:
            [(doc_id, score)] 列表
        """
        # 构建查询向量
        query_tf = Counter(query_tokens)
        query_total = sum(query_tf.values()) if query_tf else 1
        query_vector: Dict[str, float] = {}

        for token, count in query_tf.items():
            normalized_tf = count / query_total
            idf_val = self.index.idf.get(token, 0)
            query_vector[token] = normalized_tf * idf_val

        # 计算查询向量模
        query_norm = math.sqrt(sum(v ** 2 for v in query_vector.values()))
        if query_norm == 0:
            return []

        results: Dict[str, float] = {}

        for doc_id, doc in self.index.documents.items():
            doc_vector = self.index.tfidf_vectors.get(doc_id, {})

            # 扩展模糊匹配
            expanded_query = {}
            for token, weight in query_vector.items():
                similar = self._find_similar_tokens(token)
                for st in similar:
                    if st in doc_vector:
                        expanded_query[st] = max(expanded_query.get(st, 0), weight)

            # 计算余弦相似度
            dot_product = sum(
                expanded_query.get(token, 0) * weight
                for token, weight in doc_vector.items()
                if token in expanded_query
            )

            doc_norm = math.sqrt(sum(v ** 2 for v in doc_vector.values()))
            if doc_norm > 0 and query_norm > 0:
                similarity = dot_product / (query_norm * doc_norm)
                results[doc_id] = similarity

        return list(results.items())

    # ============================================================
    # 布尔查询
    # ============================================================

    def _is_boolean_query(self, query: str) -> bool:
        """检测是否为布尔查询。

        Args:
            query: 查询字符串

        Returns:
            是否包含布尔操作符
        """
        return bool(re.search(r"\b(AND|OR|NOT)\b", query, re.IGNORECASE))

    def _parse_boolean_query(self, query: str) -> List[Tuple[str, str]]:
        """解析布尔查询。

        Args:
            query: 布尔查询字符串

        Returns:
            [(操作符, 词项)] 列表
        """
        # 将布尔操作符替换为标准格式
        query = re.sub(r"\band\b", " AND ", query, flags=re.IGNORECASE)
        query = re.sub(r"\bor\b", " OR ", query, flags=re.IGNORECASE)
        query = re.sub(r"\bnot\b", " NOT ", query, flags=re.IGNORECASE)

        parts: List[Tuple[str, str]] = []
        tokens = re.split(r"\s+(AND|OR|NOT)\s+", query)

        if not tokens:
            return parts

        # 第一个词项默认用AND
        if tokens[0].strip():
            first_tokens = self.processor.process(tokens[0].strip())
            for t in first_tokens:
                parts.append(("AND", t))

        # 后续词项带操作符
        i = 1
        while i < len(tokens) - 1:
            op = tokens[i].upper()
            term_tokens = self.processor.process(tokens[i + 1].strip())
            for t in term_tokens:
                parts.append((op, t))
            i += 2

        return parts

    def _boolean_search(self, query: str, max_results: int) -> List[SearchResult]:
        """执行布尔查询。

        Args:
            query: 布尔查询字符串
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        parts = self._parse_boolean_query(query)
        if not parts:
            return []

        # 收集文档集合
        must_have: Set[str] = set()  # AND
        should_have: Set[str] = set()  # OR
        must_not_have: Set[str] = set()  # NOT

        for op, token in parts:
            # 模糊匹配扩展
            similar_tokens = self._find_similar_tokens(token)
            doc_ids = set()
            for st in similar_tokens:
                postings = self.index.search_inverted(st)
                doc_ids.update(postings.keys())

            if op == "AND":
                if must_have:
                    must_have &= doc_ids
                else:
                    must_have = doc_ids
                should_have |= doc_ids
            elif op == "OR":
                should_have |= doc_ids
            elif op == "NOT":
                must_not_have |= doc_ids

        # 合并结果
        if must_have:
            result_ids = must_have
        elif should_have:
            result_ids = should_have
        else:
            return []

        result_ids -= must_not_have

        # 生成结果
        results = []
        for doc_id in list(result_ids)[:max_results]:
            doc = self.index.get_document(doc_id)
            if doc is None:
                continue

            matched = set()
            for _, token in parts:
                similar = self._find_similar_tokens(token)
                for st in similar:
                    if st in set(doc.tokens):
                        matched.add(st)

            snippet = self._generate_snippet(doc, list(matched))
            highlights = self._generate_highlights(doc, list(matched))

            results.append(SearchResult(
                doc_id=doc_id,
                score=1.0,
                title=doc.title,
                filepath=doc.filepath,
                snippet=snippet,
                highlights=highlights,
                matched_terms=matched,
                metadata=doc.metadata,
            ))

        return results

    def _search_boolean_default(self, query_tokens: List[str]) -> List[Tuple[str, float]]:
        """默认布尔搜索（AND逻辑）。

        Args:
            query_tokens: 查询词元列表

        Returns:
            [(doc_id, score)] 列表
        """
        if not query_tokens:
            return []

        # 获取每个词元的文档集合
        doc_sets = []
        for token in query_tokens:
            similar = self._find_similar_tokens(token)
            doc_ids = set()
            for st in similar:
                postings = self.index.search_inverted(st)
                doc_ids.update(postings.keys())
            if doc_ids:
                doc_sets.append(doc_ids)

        if not doc_sets:
            return []

        # AND操作：取交集
        result_ids = doc_sets[0]
        for s in doc_sets[1:]:
            result_ids &= s

        # 计算分数
        results = []
        for doc_id in result_ids:
            doc = self.index.get_document(doc_id)
            if doc is None:
                continue
            # 分数 = 匹配词元数 / 总查询词元数
            matched = sum(1 for t in query_tokens if t in set(doc.tokens))
            score = matched / len(query_tokens)
            results.append((doc_id, score))

        return results

    # ============================================================
    # 模糊匹配
    # ============================================================

    def _edit_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离（Levenshtein距离）。

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            编辑距离
        """
        m, n = len(s1), len(s2)
        if m == 0:
            return n
        if n == 0:
            return m

        # 使用动态规划
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],      # 删除
                        dp[i][j - 1],      # 插入
                        dp[i - 1][j - 1],  # 替换
                    )

        return dp[m][n]

    def _find_similar_tokens(self, token: str) -> List[str]:
        """查找与给定词元相似的索引词元。

        Args:
            token: 查询词元

        Returns:
            相似词元列表（包含自身）
        """
        result = [token]

        if token in self.index.inverted_index:
            return result

        # 在索引中查找相似的词元
        for indexed_token in self.index.inverted_index.keys():
            dist = self._edit_distance(token, indexed_token)
            if dist <= self.fuzzy_threshold and dist > 0:
                result.append(indexed_token)

        return result

    def _expand_fuzzy_tokens(self, tokens: List[str]) -> List[str]:
        """扩展查询词元，添加模糊匹配词。

        Args:
            tokens: 原始词元列表

        Returns:
            扩展后的词元列表
        """
        expanded = []
        for token in tokens:
            similar = self._find_similar_tokens(token)
            expanded.extend(similar)
        return list(dict.fromkeys(expanded))  # 去重保序

    # ============================================================
    # 摘要和高亮
    # ============================================================

    def _generate_snippet(
        self,
        doc: IndexedDocument,
        query_tokens: List[str],
    ) -> str:
        """生成匹配摘要。

        从文档中提取包含查询词的段落，前后各取若干行。

        Args:
            doc: 索引文档
            query_tokens: 查询词元

        Returns:
            摘要文本
        """
        if not doc.content:
            return ""

        lines = doc.content.split("\n")
        query_set = set(query_tokens)

        # 找到匹配的行
        matched_lines = []
        for i, line in enumerate(lines):
            line_tokens = set(self.processor.tokenize(line))
            if query_set & line_tokens:
                matched_lines.append(i)

        if not matched_lines:
            # 没有匹配，返回开头
            return truncate(doc.content, self.snippet_length)

        # 提取上下文
        snippet_parts = []
        added_ranges: List[Tuple[int, int]] = []

        for line_idx in matched_lines:
            start = max(0, line_idx - self.context_lines)
            end = min(len(lines), line_idx + self.context_lines + 1)

            # 检查是否与已添加的范围重叠
            overlap = False
            for s, e in added_ranges:
                if start <= e and end >= s:
                    overlap = True
                    # 合并范围
                    new_start = min(s, start)
                    new_end = max(e, end)
                    added_ranges.remove((s, e))
                    added_ranges.append((new_start, new_end))
                    break

            if not overlap:
                added_ranges.append((start, end))

        # 按行号排序
        added_ranges.sort()

        for start, end in added_ranges:
            snippet_parts.append("\n".join(lines[start:end]))

        snippet = "\n...\n".join(snippet_parts)
        return truncate(snippet, self.snippet_length * 2)

    def _generate_highlights(
        self,
        doc: IndexedDocument,
        query_tokens: List[str],
    ) -> List[str]:
        """生成高亮片段。

        Args:
            doc: 索引文档
            query_tokens: 查询词元

        Returns:
            高亮片段列表
        """
        if not doc.content:
            return []

        lines = doc.content.split("\n")
        query_set = set(query_tokens)
        highlights = []

        for line in lines:
            line_tokens = set(self.processor.tokenize(line))
            if query_set & line_tokens:
                highlighted = self._highlight_text(line, query_tokens)
                highlights.append(highlighted)

        return highlights[:5]  # 最多返回5个高亮片段

    def _highlight_text(self, text: str, query_tokens: List[str]) -> str:
        """在文本中高亮查询词。

        Args:
            text: 原始文本
            query_tokens: 查询词元列表

        Returns:
            带ANSI颜色高亮的文本
        """
        result = text
        for token in query_tokens:
            # 对英文词元进行大小写不敏感匹配
            if re.match(r"^[a-zA-Z]+$", token):
                pattern = re.compile(
                    re.escape(token),
                    re.IGNORECASE
                )
                result = pattern.sub(
                    lambda m: colored(m.group(), Color.YELLOW, bold=True),
                    result
                )
            else:
                # 中文直接匹配
                if token in result:
                    result = result.replace(
                        token,
                        colored(token, Color.YELLOW, bold=True)
                    )

        return result

    # ============================================================
    # 字段过滤
    # ============================================================

    def _filter_by_fields(
        self,
        scored: List[Tuple[str, float]],
        fields: List[str],
    ) -> List[Tuple[str, float]]:
        """按字段过滤搜索结果。

        Args:
            scored: 原始评分结果
            fields: 字段列表

        Returns:
            过滤后的结果
        """
        if "all" in fields or not fields:
            return scored

        filtered = []
        for doc_id, score in scored:
            doc = self.index.get_document(doc_id)
            if doc is None:
                continue

            match = False
            if "title" in fields and doc.title:
                match = True
            if "content" in fields and doc.content:
                match = True

            if match:
                filtered.append((doc_id, score))

        return filtered
