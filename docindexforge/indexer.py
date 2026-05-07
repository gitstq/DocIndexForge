"""
DocIndexForge - 索引引擎模块

提供多策略索引功能：TF-IDF索引、BM25索引、倒排索引、
文档元数据索引、增量索引更新、索引持久化。
纯Python标准库实现，零外部依赖。
"""

import json
import math
import os
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import Counter, defaultdict

from .parser import DocumentParser, ParsedDocument
from .processor import TextProcessor
from .utils import (
    walk_files, get_file_metadata, ProgressBar,
    logger, ensure_dir, safe_read, safe_write
)


# ============================================================
# 索引文档数据结构
# ============================================================

class IndexedDocument:
    """索引中的文档条目。"""

    def __init__(
        self,
        doc_id: str,
        filepath: str,
        title: str,
        content: str,
        doc_type: str,
        tokens: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
    ):
        """初始化索引文档。

        Args:
            doc_id: 文档唯一标识
            filepath: 文件路径
            title: 文档标题
            content: 文档内容
            doc_type: 文档类型
            tokens: 分词结果
            metadata: 文件元数据
            sections: 文档章节
        """
        self.doc_id = doc_id
        self.filepath = filepath
        self.title = title
        self.content = content
        self.doc_type = doc_type
        self.tokens = tokens
        self.metadata = metadata or {}
        self.sections = sections or []
        self.token_count = len(tokens)
        self.indexed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典。"""
        return {
            "doc_id": self.doc_id,
            "filepath": self.filepath,
            "title": self.title,
            "content": self.content,
            "doc_type": self.doc_type,
            "tokens": self.tokens,
            "metadata": self.metadata,
            "sections": self.sections,
            "token_count": self.token_count,
            "indexed_at": self.indexed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexedDocument":
        """从字典创建IndexedDocument实例。"""
        doc = cls(
            doc_id=data["doc_id"],
            filepath=data["filepath"],
            title=data["title"],
            content=data["content"],
            doc_type=data["doc_type"],
            tokens=data.get("tokens", []),
            metadata=data.get("metadata", {}),
            sections=data.get("sections", []),
        )
        doc.token_count = data.get("token_count", len(doc.tokens))
        doc.indexed_at = data.get("indexed_at", time.time())
        return doc


# ============================================================
# 索引引擎
# ============================================================

class IndexEngine:
    """多策略索引引擎，支持TF-IDF、BM25和倒排索引。"""

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """初始化索引引擎。

        Args:
            k1: BM25参数k1，控制词频饱和度
            b: BM25参数b，控制文档长度归一化
        """
        self.k1 = k1
        self.b = b

        self.parser = DocumentParser()
        self.processor = TextProcessor()

        # 文档存储
        self.documents: Dict[str, IndexedDocument] = {}

        # 倒排索引: token -> {doc_id: [positions]}
        self.inverted_index: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))

        # TF-IDF相关数据
        self.idf: Dict[str, float] = {}
        self.tfidf_vectors: Dict[str, Dict[str, float]] = {}

        # BM25相关数据
        self.bm25_scores: Dict[str, Dict[str, float]] = {}
        self.avg_doc_length: float = 0.0

        # 元数据索引
        self.metadata_index: Dict[str, Dict[str, Set[str]]] = {
            "filename": defaultdict(set),
            "extension": defaultdict(set),
            "doc_type": defaultdict(set),
        }

        # 统计信息
        self.stats = {
            "total_documents": 0,
            "total_tokens": 0,
            "unique_tokens": 0,
            "index_size_bytes": 0,
            "last_updated": None,
        }

    def index_document(self, filepath: str) -> Optional[str]:
        """索引单个文档。

        Args:
            filepath: 文件路径

        Returns:
            文档ID，失败返回None
        """
        # 检查是否已索引
        doc_id = self._generate_doc_id(filepath)
        if doc_id in self.documents:
            logger.debug(f"文档已索引，跳过: {filepath}")
            return doc_id

        # 解析文档
        parsed = self.parser.parse_file(filepath)
        if parsed is None:
            return None

        # 获取文件元数据
        file_meta = get_file_metadata(filepath)

        # 文本处理
        tokens = self.processor.process(parsed.content)

        # 创建索引文档
        doc = IndexedDocument(
            doc_id=doc_id,
            filepath=filepath,
            title=parsed.title,
            content=parsed.content,
            doc_type=parsed.doc_type,
            tokens=tokens,
            metadata=file_meta,
            sections=parsed.sections,
        )

        # 存储文档
        self.documents[doc_id] = doc

        # 构建倒排索引
        for pos, token in enumerate(tokens):
            self.inverted_index[token][doc_id].append(pos)

        # 更新元数据索引
        self.metadata_index["filename"][file_meta["filename"]].add(doc_id)
        self.metadata_index["extension"][file_meta["extension"]].add(doc_id)
        self.metadata_index["doc_type"][parsed.doc_type].add(doc_id)

        logger.debug(f"已索引: {filepath} ({len(tokens)} tokens)")
        return doc_id

    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        show_progress: bool = True,
    ) -> int:
        """索引目录中的所有文档。

        Args:
            directory: 目录路径
            recursive: 是否递归遍历
            show_progress: 是否显示进度条

        Returns:
            索引的文档数量
        """
        files = list(walk_files(directory, recursive=recursive))
        if not files:
            logger.warning(f"未找到可索引的文件: {directory}")
            return 0

        count = 0
        if show_progress:
            progress = ProgressBar(len(files), prefix="索引中")

        for filepath in files:
            result = self.index_document(filepath)
            if result:
                count += 1
            if show_progress:
                progress.update()

        if show_progress:
            progress.finish()

        # 重新计算索引统计
        self._recompute_stats()
        logger.info(f"索引完成: {count} 个文档")
        return count

    def remove_document(self, doc_id: str) -> bool:
        """从索引中移除文档。

        Args:
            doc_id: 文档ID

        Returns:
            是否成功移除
        """
        if doc_id not in self.documents:
            logger.warning(f"文档不存在: {doc_id}")
            return False

        doc = self.documents[doc_id]

        # 从倒排索引中移除
        tokens_to_remove = []
        for token, postings in self.inverted_index.items():
            if doc_id in postings:
                del postings[doc_id]
                if not postings:
                    tokens_to_remove.append(token)

        for token in tokens_to_remove:
            del self.inverted_index[token]

        # 从元数据索引中移除
        filename = doc.metadata.get("filename", "")
        ext = doc.metadata.get("extension", "")
        for meta_key, meta_val in [
            ("filename", filename),
            ("extension", ext),
            ("doc_type", doc.doc_type),
        ]:
            if meta_val in self.metadata_index.get(meta_key, {}):
                self.metadata_index[meta_key][meta_val].discard(doc_id)
                if not self.metadata_index[meta_key][meta_val]:
                    del self.metadata_index[meta_key][meta_val]

        # 移除文档
        del self.documents[doc_id]

        # 清理TF-IDF和BM25数据
        self.tfidf_vectors.pop(doc_id, None)
        self.bm25_scores.pop(doc_id, None)

        self._recompute_stats()
        logger.info(f"已移除文档: {doc_id}")
        return True

    def update_document(self, filepath: str) -> Optional[str]:
        """更新已索引的文档。

        Args:
            filepath: 文件路径

        Returns:
            文档ID，失败返回None
        """
        doc_id = self._generate_doc_id(filepath)
        if doc_id in self.documents:
            self.remove_document(doc_id)
        return self.index_document(filepath)

    def incremental_update(self, directory: str, recursive: bool = True) -> Tuple[int, int, int]:
        """增量更新索引。

        检查文件修改时间，只重新索引有变化的文件。

        Args:
            directory: 目录路径
            recursive: 是否递归

        Returns:
            (新增数, 更新数, 移除数)
        """
        current_files = set(walk_files(directory, recursive=recursive))
        indexed_files = {doc.filepath for doc in self.documents.values()}

        added = 0
        updated = 0
        removed = 0

        # 检查新增和更新的文件
        for filepath in current_files:
            doc_id = self._generate_doc_id(filepath)
            if doc_id not in self.documents:
                # 新增文件
                if self.index_document(filepath):
                    added += 1
            else:
                # 检查是否需要更新
                doc = self.documents[doc_id]
                file_meta = get_file_metadata(filepath)
                if file_meta["modified_time"] > doc.metadata.get("modified_time", 0):
                    if self.update_document(filepath):
                        updated += 1

        # 检查已删除的文件
        for filepath in indexed_files:
            if filepath not in current_files:
                doc_id = self._generate_doc_id(filepath)
                if self.remove_document(doc_id):
                    removed += 1

        self._recompute_stats()
        logger.info(f"增量更新: +{added} ~{updated} -{removed}")
        return added, updated, removed

    # ============================================================
    # TF-IDF 索引
    # ============================================================

    def build_tfidf_index(self) -> None:
        """构建TF-IDF索引。"""
        n_docs = len(self.documents)
        if n_docs == 0:
            logger.warning("没有文档，无法构建TF-IDF索引")
            return

        # 计算IDF
        doc_freq: Counter = Counter()
        for doc in self.documents.values():
            unique_tokens = set(doc.tokens)
            for token in unique_tokens:
                doc_freq[token] += 1

        self.idf = {}
        for token, df in doc_freq.items():
            self.idf[token] = math.log((n_docs + 1) / (df + 1)) + 1

        # 计算每个文档的TF-IDF向量
        self.tfidf_vectors = {}
        for doc_id, doc in self.documents.items():
            tf = Counter(doc.tokens)
            total = sum(tf.values()) if tf else 1
            tfidf: Dict[str, float] = {}
            for token, count in tf.items():
                normalized_tf = count / total
                tfidf[token] = normalized_tf * self.idf.get(token, 0)
            self.tfidf_vectors[doc_id] = tfidf

        logger.info(f"TF-IDF索引构建完成: {len(self.idf)} 个唯一词")

    # ============================================================
    # BM25 索引
    # ============================================================

    def build_bm25_index(self) -> None:
        """构建BM25索引。"""
        n_docs = len(self.documents)
        if n_docs == 0:
            logger.warning("没有文档，无法构建BM25索引")
            return

        # 计算平均文档长度
        total_length = sum(doc.token_count for doc in self.documents.values())
        self.avg_doc_length = total_length / n_docs if n_docs > 0 else 0

        # 计算IDF（与TF-IDF共用）
        doc_freq: Counter = Counter()
        for doc in self.documents.values():
            unique_tokens = set(doc.tokens)
            for token in unique_tokens:
                doc_freq[token] += 1

        self.idf = {}
        for token, df in doc_freq.items():
            self.idf[token] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)

        # 预计算BM25分数
        self.bm25_scores = {}
        for doc_id, doc in self.documents.items():
            tf = Counter(doc.tokens)
            doc_len = doc.token_count
            scores: Dict[str, float] = {}

            for token, freq in tf.items():
                idf_val = self.idf.get(token, 0)
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (
                    1 - self.b + self.b * (doc_len / self.avg_doc_length if self.avg_doc_length > 0 else 1)
                )
                scores[token] = idf_val * numerator / denominator

            self.bm25_scores[doc_id] = scores

        logger.info(f"BM25索引构建完成: avg_len={self.avg_doc_length:.1f}")

    def build_all_indexes(self) -> None:
        """构建所有索引。"""
        self.build_tfidf_index()
        self.build_bm25_index()
        self._recompute_stats()

    # ============================================================
    # 持久化
    # ============================================================

    def export_index(self, filepath: str) -> bool:
        """导出索引到JSON文件。

        Args:
            filepath: 导出文件路径

        Returns:
            是否成功
        """
        data = {
            "version": "1.0",
            "exported_at": time.time(),
            "stats": self.stats,
            "documents": {
                doc_id: doc.to_dict()
                for doc_id, doc in self.documents.items()
            },
            "inverted_index": {
                token: {did: positions for did, positions in postings.items()}
                for token, postings in self.inverted_index.items()
            },
            "idf": self.idf,
            "avg_doc_length": self.avg_doc_length,
            "bm25_k1": self.k1,
            "bm25_b": self.b,
        }

        # 将defaultdict转为普通dict
        metadata_index = {}
        for key, val in self.metadata_index.items():
            metadata_index[key] = {k: list(v) for k, v in val.items()}
        data["metadata_index"] = metadata_index

        return safe_write(filepath, json.dumps(data, indent=2, ensure_ascii=False))

    def import_index(self, filepath: str) -> bool:
        """从JSON文件导入索引。

        Args:
            filepath: 导入文件路径

        Returns:
            是否成功
        """
        content = safe_read(filepath)
        if content is None:
            return False

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"索引文件格式错误: {e}")
            return False

        try:
            # 导入文档
            self.documents = {}
            for doc_id, doc_data in data.get("documents", {}).items():
                self.documents[doc_id] = IndexedDocument.from_dict(doc_data)

            # 导入倒排索引
            self.inverted_index = defaultdict(lambda: defaultdict(list))
            for token, postings in data.get("inverted_index", {}).items():
                for doc_id, positions in postings.items():
                    self.inverted_index[token][doc_id] = positions

            # 导入IDF
            self.idf = data.get("idf", {})

            # 导入BM25参数
            self.avg_doc_length = data.get("avg_doc_length", 0)
            self.k1 = data.get("bm25_k1", 1.5)
            self.b = data.get("bm25_b", 0.75)

            # 导入元数据索引
            self.metadata_index = {
                "filename": defaultdict(set),
                "extension": defaultdict(set),
                "doc_type": defaultdict(set),
            }
            for key, val in data.get("metadata_index", {}).items():
                if key in self.metadata_index:
                    for k, v in val.items():
                        self.metadata_index[key][k] = set(v)

            # 导入统计
            self.stats = data.get("stats", self.stats)

            # 重建TF-IDF和BM25分数
            self.build_tfidf_index()
            self.build_bm25_index()

            logger.info(f"索引导入完成: {len(self.documents)} 个文档")
            return True

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"索引导入失败: {e}")
            return False

    # ============================================================
    # 查询接口
    # ============================================================

    def get_document(self, doc_id: str) -> Optional[IndexedDocument]:
        """获取索引中的文档。

        Args:
            doc_id: 文档ID

        Returns:
            IndexedDocument实例或None
        """
        return self.documents.get(doc_id)

    def search_inverted(self, token: str) -> Dict[str, List[int]]:
        """查询倒排索引。

        Args:
            token: 查询词元

        Returns:
            {doc_id: [positions]} 字典
        """
        return dict(self.inverted_index.get(token, {}))

    def get_all_doc_ids(self) -> List[str]:
        """获取所有文档ID。"""
        return list(self.documents.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息。"""
        return {
            **self.stats,
            "unique_tokens": len(self.inverted_index),
            "total_tokens": sum(doc.token_count for doc in self.documents.values()),
            "avg_doc_length": self.avg_doc_length,
            "index_size_bytes": self._estimate_index_size(),
        }

    # ============================================================
    # 内部方法
    # ============================================================

    def _generate_doc_id(self, filepath: str) -> str:
        """生成文档唯一ID。

        Args:
            filepath: 文件路径

        Returns:
            文档ID字符串
        """
        return str(hash(filepath))

    def _recompute_stats(self) -> None:
        """重新计算索引统计信息。"""
        self.stats["total_documents"] = len(self.documents)
        self.stats["total_tokens"] = sum(doc.token_count for doc in self.documents.values())
        self.stats["unique_tokens"] = len(self.inverted_index)
        self.stats["last_updated"] = time.time()
        self.stats["index_size_bytes"] = self._estimate_index_size()

    def _estimate_index_size(self) -> int:
        """估算索引占用的内存大小（字节）。"""
        size = 0
        for doc in self.documents.values():
            size += len(doc.content) * 2  # 粗略估算
            size += len(doc.tokens) * 8
        size += len(self.inverted_index) * 50  # 粗略估算
        return size
