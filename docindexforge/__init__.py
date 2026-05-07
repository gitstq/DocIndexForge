"""
DocIndexForge - 文档智能索引与语义检索引擎

一个轻量级的CLI工具，支持多种文档格式的解析、索引和语义检索。
纯Python 3.8+实现，零外部依赖。

功能特性:
- 多格式文档解析 (Markdown, TXT, JSON, CSV, HTML)
- 中英文文本处理与分词
- TF-IDF 和 BM25 索引
- 智能检索（模糊匹配、布尔查询）
- 文档分析与相似度计算
- TUI终端交互界面
- HTTP API 服务
"""

__version__ = "1.0.0"
__author__ = "DocIndexForge"
__license__ = "MIT"

from .indexer import IndexEngine
from .searcher import SearchEngine
from .analyzer import AnalysisEngine
from .parser import DocumentParser
from .processor import TextProcessor

__all__ = [
    "IndexEngine",
    "SearchEngine",
    "AnalysisEngine",
    "DocumentParser",
    "TextProcessor",
]
