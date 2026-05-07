"""
DocIndexForge - 分析引擎模块

提供文档分析功能：文档统计、词频分析、文档相似度计算、
相似文档发现、索引健康报告。
纯Python标准库实现，零外部依赖。
"""

import math
import re
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter

from .indexer import IndexEngine, IndexedDocument
from .processor import TextProcessor
from .utils import Color, colored, format_table, logger


# ============================================================
# 文档统计
# ============================================================

class DocumentStats:
    """单个文档的统计信息。"""

    def __init__(self, doc: IndexedDocument):
        """根据索引文档计算统计信息。

        Args:
            doc: 索引文档
        """
        self.doc_id = doc.doc_id
        self.filepath = doc.filepath
        self.title = doc.title
        self.doc_type = doc.doc_type

        content = doc.content

        # 基本统计
        self.char_count = len(content)
        self.char_count_no_spaces = len(content.replace(" ", "").replace("\n", "").replace("\t", ""))

        # 段落统计
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        self.paragraph_count = len(paragraphs)

        # 句子统计（简单按句号、问号、感叹号分割）
        sentences = re.split(r'[.!?。！？]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        self.sentence_count = len(sentences)

        # 词/字统计
        self.word_count = doc.token_count
        self.unique_word_count = len(set(doc.tokens))

        # 平均词长
        if doc.tokens:
            self.avg_word_length = sum(len(t) for t in doc.tokens) / len(doc.tokens)
        else:
            self.avg_word_length = 0

        # 行数
        self.line_count = content.count("\n") + 1

        # 文件大小
        self.file_size = doc.metadata.get("size_bytes", 0)
        self.file_size_human = doc.metadata.get("size_human", "0 B")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "doc_id": self.doc_id,
            "filepath": self.filepath,
            "title": self.title,
            "doc_type": self.doc_type,
            "char_count": self.char_count,
            "char_count_no_spaces": self.char_count_no_spaces,
            "paragraph_count": self.paragraph_count,
            "sentence_count": self.sentence_count,
            "word_count": self.word_count,
            "unique_word_count": self.unique_word_count,
            "avg_word_length": round(self.avg_word_length, 2),
            "line_count": self.line_count,
            "file_size": self.file_size,
            "file_size_human": self.file_size_human,
        }

    def format_report(self) -> str:
        """格式化统计报告。"""
        lines = [
            colored(f"文档统计: {self.title}", Color.CYAN, bold=True),
            f"  文件路径: {self.filepath}",
            f"  文档类型: {self.doc_type}",
            f"  字符数: {self.char_count} (不含空白: {self.char_count_no_spaces})",
            f"  词/字数: {self.word_count} (唯一: {self.unique_word_count})",
            f"  段落数: {self.paragraph_count}",
            f"  句子数: {self.sentence_count}",
            f"  行数: {self.line_count}",
            f"  平均词长: {self.avg_word_length:.2f}",
            f"  文件大小: {self.file_size_human}",
        ]
        return "\n".join(lines)


# ============================================================
# 词频分析
# ============================================================

class WordFrequency:
    """词频分析结果。"""

    def __init__(self, frequencies: Counter, total: int):
        """初始化词频分析。

        Args:
            frequencies: 词频计数器
            total: 总词数
        """
        self.frequencies = frequencies
        self.total = total
        self.vocabulary_size = len(frequencies)

    def top(self, n: int = 20) -> List[Tuple[str, int]]:
        """获取前N个高频词。

        Args:
            n: 返回数量

        Returns:
            [(词, 频次)] 列表
        """
        return self.frequencies.most_common(n)

    def top_with_ratio(self, n: int = 20) -> List[Tuple[str, int, float]]:
        """获取前N个高频词及其占比。

        Args:
            n: 返回数量

        Returns:
            [(词, 频次, 占比)] 列表
        """
        result = []
        for word, count in self.frequencies.most_common(n):
            ratio = count / self.total if self.total > 0 else 0
            result.append((word, count, ratio))
        return result

    def format_report(self, n: int = 20) -> str:
        """格式化词频报告。"""
        lines = [
            colored("词频分析报告", Color.CYAN, bold=True),
            f"  总词数: {self.total}",
            f"  词汇量: {self.vocabulary_size}",
            "",
            colored(f"  高频词 TOP-{n}:", Color.YELLOW),
        ]

        for word, count, ratio in self.top_with_ratio(n):
            bar_len = int(ratio * 40)
            bar = "█" * bar_len
            lines.append(f"    {word:<15} {count:>6}  {ratio:>6.2%}  {bar}")

        return "\n".join(lines)


# ============================================================
# 分析引擎
# ============================================================

class AnalysisEngine:
    """文档分析引擎。"""

    def __init__(self, index_engine: IndexEngine):
        """初始化分析引擎。

        Args:
            index_engine: 索引引擎实例
        """
        self.index = index_engine
        self.processor = TextProcessor()

    def analyze_document(self, doc_id: str) -> Optional[DocumentStats]:
        """分析单个文档。

        Args:
            doc_id: 文档ID

        Returns:
            DocumentStats实例或None
        """
        doc = self.index.get_document(doc_id)
        if doc is None:
            logger.warning(f"文档不存在: {doc_id}")
            return None
        return DocumentStats(doc)

    def word_frequency(
        self,
        doc_id: Optional[str] = None,
        top_n: int = 20,
    ) -> WordFrequency:
        """分析词频。

        Args:
            doc_id: 文档ID，为None则分析全部文档
            top_n: 返回前N个高频词

        Returns:
            WordFrequency实例
        """
        frequencies: Counter = Counter()
        total = 0

        if doc_id:
            doc = self.index.get_document(doc_id)
            if doc is None:
                return WordFrequency(frequencies, total)
            frequencies = Counter(doc.tokens)
            total = doc.token_count
        else:
            for doc in self.index.documents.values():
                frequencies.update(doc.tokens)
                total += doc.token_count

        return WordFrequency(frequencies, total)

    # ============================================================
    # 文档相似度
    # ============================================================

    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算两个向量的余弦相似度。

        Args:
            vec1: 向量1（词 -> 权重）
            vec2: 向量2（词 -> 权重）

        Returns:
            余弦相似度 [0, 1]
        """
        # 计算点积
        common_keys = set(vec1.keys()) & set(vec2.keys())
        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)

        # 计算模
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def document_similarity(self, doc_id1: str, doc_id2: str) -> float:
        """计算两个文档的相似度。

        Args:
            doc_id1: 文档1的ID
            doc_id2: 文档2的ID

        Returns:
            相似度分数 [0, 1]
        """
        vec1 = self.index.tfidf_vectors.get(doc_id1, {})
        vec2 = self.index.tfidf_vectors.get(doc_id2, {})

        if not vec1 or not vec2:
            # TF-IDF向量未构建，使用简单的词频向量
            doc1 = self.index.get_document(doc_id1)
            doc2 = self.index.get_document(doc_id2)
            if doc1 is None or doc2 is None:
                return 0.0

            tf1 = Counter(doc1.tokens)
            tf2 = Counter(doc2.tokens)
            return self.cosine_similarity(
                {k: float(v) for k, v in tf1.items()},
                {k: float(v) for k, v in tf2.items()},
            )

        return self.cosine_similarity(vec1, vec2)

    def find_similar_documents(
        self,
        doc_id: str,
        top_n: int = 10,
        threshold: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """发现与指定文档相似的文档。

        Args:
            doc_id: 目标文档ID
            top_n: 返回前N个相似文档
            threshold: 最低相似度阈值

        Returns:
            [(doc_id, similarity)] 列表，按相似度降序
        """
        doc = self.index.get_document(doc_id)
        if doc is None:
            logger.warning(f"文档不存在: {doc_id}")
            return []

        # 获取目标文档的TF-IDF向量
        target_vec = self.index.tfidf_vectors.get(doc_id, {})
        if not target_vec:
            tf = Counter(doc.tokens)
            target_vec = {k: float(v) for k, v in tf.items()}

        similarities: List[Tuple[str, float]] = []

        for other_id, other_doc in self.index.documents.items():
            if other_id == doc_id:
                continue

            other_vec = self.index.tfidf_vectors.get(other_id, {})
            if not other_vec:
                tf = Counter(other_doc.tokens)
                other_vec = {k: float(v) for k, v in tf.items()}

            sim = self.cosine_similarity(target_vec, other_vec)
            if sim >= threshold:
                similarities.append((other_id, sim))

        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]

    # ============================================================
    # 索引健康报告
    # ============================================================

    def health_report(self) -> Dict[str, Any]:
        """生成索引健康报告。

        Returns:
            健康报告字典
        """
        stats = self.index.get_stats()
        doc_count = stats["total_documents"]

        if doc_count == 0:
            return {
                "status": "empty",
                "message": "索引为空，没有文档",
                "stats": stats,
            }

        # 文档类型分布
        type_dist: Counter = Counter()
        for doc in self.index.documents.values():
            type_dist[doc.doc_type] += 1

        # 文档大小分布
        sizes = [doc.metadata.get("size_bytes", 0) for doc in self.index.documents.values()]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        max_size = max(sizes) if sizes else 0
        min_size = min(sizes) if sizes else 0

        # 词元统计
        token_counts = [doc.token_count for doc in self.index.documents.values()]
        avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0

        # 空文档检测
        empty_docs = sum(1 for doc in self.index.documents.values() if doc.token_count == 0)

        # 索引覆盖率
        unique_tokens = stats.get("unique_tokens", 0)

        # 健康状态评估
        issues = []
        if empty_docs > 0:
            issues.append(f"{empty_docs} 个文档内容为空")
        if avg_tokens < 10:
            issues.append("平均文档词数过少，可能解析有问题")
        if unique_tokens == 0:
            issues.append("索引中没有词元")

        status = "healthy"
        if issues:
            status = "warning"
        if empty_docs == doc_count:
            status = "critical"

        return {
            "status": status,
            "stats": stats,
            "type_distribution": dict(type_dist),
            "size_stats": {
                "avg": avg_size,
                "max": max_size,
                "min": min_size,
            },
            "token_stats": {
                "avg_per_doc": round(avg_tokens, 1),
                "total_unique": unique_tokens,
            },
            "empty_documents": empty_docs,
            "issues": issues,
        }

    def format_health_report(self) -> str:
        """格式化索引健康报告。"""
        report = self.health_report()

        status_colors = {
            "healthy": Color.GREEN,
            "warning": Color.YELLOW,
            "critical": Color.RED,
            "empty": Color.DIM,
        }

        status_text = {
            "healthy": "健康",
            "warning": "警告",
            "critical": "严重",
            "empty": "空",
        }

        color = status_colors.get(report["status"], Color.WHITE)
        status = status_text.get(report["status"], report["status"])

        lines = [
            colored("索引健康报告", Color.CYAN, bold=True),
            "",
            f"  状态: {colored(status, color, bold=True)}",
            "",
        ]

        # 基本统计
        stats = report["stats"]
        lines.extend([
            colored("  基本统计:", Color.YELLOW),
            f"    文档总数: {stats.get('total_documents', 0)}",
            f"    总词元数: {stats.get('total_tokens', 0)}",
            f"    唯一词元数: {stats.get('unique_tokens', 0)}",
            f"    平均文档长度: {stats.get('avg_doc_length', 0):.1f}",
            f"    索引大小: {stats.get('index_size_bytes', 0) / 1024:.1f} KB",
            "",
        ])

        # 文档类型分布
        type_dist = report.get("type_distribution", {})
        if type_dist:
            lines.append(colored("  文档类型分布:", Color.YELLOW))
            for doc_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
                ratio = count / stats.get("total_documents", 1) * 100
                bar_len = int(ratio / 5)
                bar = "█" * bar_len
                lines.append(f"    {doc_type:<12} {count:>4}  {ratio:>5.1f}%  {bar}")
            lines.append("")

        # 大小统计
        size_stats = report.get("size_stats", {})
        if size_stats:
            lines.append(colored("  文档大小统计:", Color.YELLOW))
            lines.append(f"    平均: {size_stats['avg'] / 1024:.1f} KB")
            lines.append(f"    最大: {size_stats['max'] / 1024:.1f} KB")
            lines.append(f"    最小: {size_stats['min'] / 1024:.1f} KB")
            lines.append("")

        # 问题
        issues = report.get("issues", [])
        if issues:
            lines.append(colored("  发现的问题:", Color.RED))
            for issue in issues:
                lines.append(f"    - {colored(issue, Color.RED)}")
        else:
            lines.append(colored("  未发现问题", Color.GREEN))

        return "\n".join(lines)

    # ============================================================
    # 全局统计
    # ============================================================

    def global_stats(self) -> str:
        """生成全局统计报告。

        Returns:
            格式化的统计报告字符串
        """
        doc_count = len(self.index.documents)

        if doc_count == 0:
            return colored("索引为空，没有文档", Color.YELLOW)

        # 收集所有文档的统计信息
        all_stats = []
        for doc_id in self.index.documents:
            ds = self.analyze_document(doc_id)
            if ds:
                all_stats.append(ds)

        if not all_stats:
            return "无法计算统计信息"

        # 总计
        total_chars = sum(s.char_count for s in all_stats)
        total_words = sum(s.word_count for s in all_stats)
        total_unique = sum(s.unique_word_count for s in all_stats)
        total_paragraphs = sum(s.paragraph_count for s in all_stats)
        total_sentences = sum(s.sentence_count for s in all_stats)
        total_lines = sum(s.line_count for s in all_stats)

        lines = [
            colored("全局统计报告", Color.CYAN, bold=True),
            "",
            f"  文档数量: {doc_count}",
            f"  总字符数: {total_chars:,}",
            f"  总词/字数: {total_words:,}",
            f"  总唯一词数: {total_unique:,}",
            f"  总段落数: {total_paragraphs:,}",
            f"  总句子数: {total_sentences:,}",
            f"  总行数: {total_lines:,}",
            "",
        ]

        # 文档类型表格
        type_rows = []
        type_counter: Counter = Counter()
        for ds in all_stats:
            type_counter[ds.doc_type] += 1

        for doc_type, count in type_counter.most_common():
            type_rows.append([doc_type, str(count), f"{count / doc_count * 100:.1f}%"])

        lines.append(colored("  文档类型分布:", Color.YELLOW))
        lines.append(format_table(["类型", "数量", "占比"], type_rows, padding=2))

        return "\n".join(lines)
