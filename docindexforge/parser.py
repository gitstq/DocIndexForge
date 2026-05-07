"""
DocIndexForge - 文档解析器模块

支持解析多种文档格式：Markdown、纯文本、JSON、CSV、HTML。
自动检测文件格式并提取结构化内容。
纯Python标准库实现，零外部依赖。
"""

import os
import json
import csv
import re
import io
from typing import Dict, List, Any, Optional, Tuple
from html.parser import HTMLParser
from pathlib import Path

from .utils import detect_file_type, logger


# ============================================================
# 解析结果数据结构
# ============================================================

class ParsedDocument:
    """解析后的文档数据结构。"""

    def __init__(
        self,
        filepath: str,
        doc_type: str,
        title: str = "",
        sections: Optional[List[Dict[str, Any]]] = None,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        raw_text: str = ""
    ):
        """初始化解析文档。

        Args:
            filepath: 文件路径
            doc_type: 文档类型
            title: 文档标题
            sections: 章节列表，每个章节包含 type, heading, content, level
            content: 提取的纯文本内容
            metadata: 额外元数据
            raw_text: 原始文本
        """
        self.filepath = filepath
        self.doc_type = doc_type
        self.title = title
        self.sections = sections or []
        self.content = content
        self.metadata = metadata or {}
        self.raw_text = raw_text

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "filepath": self.filepath,
            "doc_type": self.doc_type,
            "title": self.title,
            "sections": self.sections,
            "content": self.content,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"ParsedDocument(type={self.doc_type}, title={self.title!r}, sections={len(self.sections)})"


# ============================================================
# Markdown 解析器
# ============================================================

class MarkdownParser:
    """Markdown文档解析器，提取标题、段落、代码块等结构。"""

    # 匹配Markdown标题
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    # 匹配代码块（围栏式）
    FENCED_CODE_PATTERN = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)
    # 匹配行内代码
    INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
    # 匹配链接
    LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    # 匹配图片
    IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    # 匹配粗体
    BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
    # 匹配斜体
    ITALIC_PATTERN = re.compile(r"\*(.+?)\*|_(.+?)_")
    # 匹配列表项
    LIST_PATTERN = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.+)$", re.MULTILINE)
    # 匹配水平分割线
    HR_PATTERN = re.compile(r"^(---|\*\*\*|___)\s*$", re.MULTILINE)

    def parse(self, text: str, filepath: str = "") -> ParsedDocument:
        """解析Markdown文本。

        Args:
            text: Markdown文本内容
            filepath: 文件路径

        Returns:
            ParsedDocument实例
        """
        raw_text = text
        sections = []
        title = ""

        # 提取标题层级和位置
        headings = []
        for match in self.HEADING_PATTERN.finditer(text):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            headings.append((match.start(), level, heading_text))

        # 设置文档标题（第一个标题）
        if headings:
            title = headings[0][2]

        # 按标题分割文档为章节
        split_positions = [h[0] for h in headings] + [len(text)]

        for i, (pos, level, heading) in enumerate(headings):
            start = pos
            end = split_positions[i + 1] if i + 1 < len(split_positions) else len(text)
            section_text = text[start:end]

            # 清理章节内容
            clean_content = self._clean_section(section_text, heading)

            sections.append({
                "type": "heading",
                "heading": heading,
                "level": level,
                "content": clean_content,
            })

        # 如果没有标题，将整个内容作为一个段落
        if not headings:
            clean_content = self._strip_markdown(text)
            sections.append({
                "type": "paragraph",
                "heading": "",
                "level": 0,
                "content": clean_content,
            })

        # 提取纯文本
        content = self._strip_markdown(text)

        return ParsedDocument(
            filepath=filepath,
            doc_type="markdown",
            title=title,
            sections=sections,
            content=content,
            raw_text=raw_text,
        )

    def _clean_section(self, section_text: str, heading: str) -> str:
        """清理章节内容，去除标题行和Markdown标记。"""
        lines = section_text.split("\n")
        # 去除标题行
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and heading in stripped:
                continue
            cleaned_lines.append(line)

        return self._strip_markdown("\n".join(cleaned_lines))

    def _strip_markdown(self, text: str) -> str:
        """去除Markdown标记，返回纯文本。"""
        # 移除代码块标记但保留内容
        text = self.FENCED_CODE_PATTERN.sub(r"\1", text)
        # 移除行内代码标记
        text = self.INLINE_CODE_PATTERN.sub(r"\1", text)
        # 移除链接，保留文字
        text = self.LINK_PATTERN.sub(r"\1", text)
        # 移除图片
        text = self.IMAGE_PATTERN.sub("", text)
        # 移除粗体
        text = self.BOLD_PATTERN.sub(r"\1\2", text)
        # 移除斜体
        text = self.ITALIC_PATTERN.sub(r"\1\2", text)
        # 移除水平线
        text = self.HR_PATTERN.sub("", text)
        # 移除列表标记
        text = self.LIST_PATTERN.sub(r"\3", text)
        # 移除多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


# ============================================================
# 纯文本解析器
# ============================================================

class TextParser:
    """纯文本文件解析器。"""

    def parse(self, text: str, filepath: str = "") -> ParsedDocument:
        """解析纯文本。

        Args:
            text: 文本内容
            filepath: 文件路径

        Returns:
            ParsedDocument实例
        """
        lines = text.split("\n")
        paragraphs = []
        current_paragraph = []

        for line in lines:
            stripped = line.strip()
            if stripped:
                current_paragraph.append(stripped)
            else:
                if current_paragraph:
                    paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []

        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))

        # 第一行作为标题（如果有）
        title = paragraphs[0][:100] if paragraphs else ""

        sections = []
        for i, para in enumerate(paragraphs):
            sections.append({
                "type": "paragraph",
                "heading": title if i == 0 else "",
                "level": 0,
                "content": para,
            })

        return ParsedDocument(
            filepath=filepath,
            doc_type="text",
            title=title,
            sections=sections,
            content=text.strip(),
            raw_text=text,
        )


# ============================================================
# JSON 解析器
# ============================================================

class JSONParser:
    """JSON文件解析器，递归提取所有字符串值。"""

    def parse(self, text: str, filepath: str = "") -> ParsedDocument:
        """解析JSON文件，递归提取所有字符串值。

        Args:
            text: JSON文本内容
            filepath: 文件路径

        Returns:
            ParsedDocument实例
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {filepath}: {e}")
            return ParsedDocument(
                filepath=filepath,
                doc_type="json",
                content=text,
                raw_text=text,
            )

        # 递归提取所有字符串值
        string_values = []
        self._extract_strings(data, string_values)

        content = "\n".join(string_values)
        title = string_values[0][:100] if string_values else ""

        sections = []
        for i, val in enumerate(string_values):
            sections.append({
                "type": "value",
                "heading": f"Value #{i + 1}",
                "level": 0,
                "content": val,
            })

        return ParsedDocument(
            filepath=filepath,
            doc_type="json",
            title=title,
            sections=sections,
            content=content,
            metadata={"top_level_keys": list(data.keys()) if isinstance(data, dict) else []},
            raw_text=text,
        )

    def _extract_strings(self, obj: Any, result: List[str]) -> None:
        """递归提取JSON中所有字符串值。

        Args:
            obj: JSON对象
            result: 字符串值收集列表
        """
        if isinstance(obj, str):
            if obj.strip():
                result.append(obj.strip())
        elif isinstance(obj, dict):
            for key, value in obj.items():
                # 也提取键名
                if isinstance(key, str) and key.strip():
                    result.append(key.strip())
                self._extract_strings(value, result)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_strings(item, result)


# ============================================================
# CSV 解析器
# ============================================================

class CSVParser:
    """CSV文件解析器，逐行提取内容。"""

    def parse(self, text: str, filepath: str = "") -> ParsedDocument:
        """解析CSV文件。

        Args:
            text: CSV文本内容
            filepath: 文件路径

        Returns:
            ParsedDocument实例
        """
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            return ParsedDocument(
                filepath=filepath,
                doc_type="csv",
                content="",
                raw_text=text,
            )

        # 第一行作为标题
        header = rows[0] if rows else []
        title = " | ".join(header[:5])  # 最多取前5列作为标题

        sections = []
        # 添加表头
        sections.append({
            "type": "header",
            "heading": "CSV Header",
            "level": 1,
            "content": " | ".join(header),
        })

        # 添加数据行
        for i, row in enumerate(rows[1:], 1):
            row_text = " | ".join(row)
            sections.append({
                "type": "row",
                "heading": f"Row {i}",
                "level": 0,
                "content": row_text,
            })

        content_lines = [" | ".join(row) for row in rows]
        content = "\n".join(content_lines)

        return ParsedDocument(
            filepath=filepath,
            doc_type="csv",
            title=title,
            sections=sections,
            content=content,
            metadata={
                "row_count": len(rows) - 1,
                "column_count": len(header),
                "headers": header,
            },
            raw_text=text,
        )


# ============================================================
# HTML 解析器
# ============================================================

class _HTMLTextExtractor(HTMLParser):
    """HTML文本提取器，使用html.parser提取纯文本。"""

    SKIP_TAGS = {"script", "style", "head", "meta", "link", "noscript"}

    def __init__(self):
        super().__init__()
        self._result: List[str] = []
        self._skip_depth = 0
        self._current_tag = ""
        self._title = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        self._current_tag = tag_lower
        if tag_lower in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag_lower == "title":
            self._skip_depth += 1  # 标题单独处理

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag_lower == "title":
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            if self._current_tag == "title":
                self._title = data.strip()
            return
        text = data.strip()
        if text:
            self._result.append(text)

    def get_text(self) -> str:
        """获取提取的文本。"""
        return "\n".join(self._result)

    def get_title(self) -> str:
        """获取页面标题。"""
        return self._title


class HTMLParserModule:
    """HTML文件解析器。"""

    def parse(self, text: str, filepath: str = "") -> ParsedDocument:
        """解析HTML文件，提取纯文本内容。

        Args:
            text: HTML文本内容
            filepath: 文件路径

        Returns:
            ParsedDocument实例
        """
        extractor = _HTMLTextExtractor()
        try:
            extractor.feed(text)
        except Exception as e:
            logger.error(f"HTML解析失败 {filepath}: {e}")

        content = extractor.get_text()
        title = extractor.get_title()

        # 按段落分割
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

        sections = []
        for i, para in enumerate(paragraphs):
            sections.append({
                "type": "paragraph",
                "heading": title if i == 0 else "",
                "level": 0,
                "content": para,
            })

        return ParsedDocument(
            filepath=filepath,
            doc_type="html",
            title=title,
            sections=sections,
            content=content,
            raw_text=text,
        )


# ============================================================
# 统一解析接口
# ============================================================

class DocumentParser:
    """统一文档解析器，根据文件类型自动选择解析策略。"""

    def __init__(self):
        """初始化解析器，注册所有支持的格式解析器。"""
        self._parsers = {
            "markdown": MarkdownParser(),
            "text": TextParser(),
            "json": JSONParser(),
            "csv": CSVParser(),
            "html": HTMLParserModule(),
        }

    def parse_file(self, filepath: str) -> Optional[ParsedDocument]:
        """解析文件。

        Args:
            filepath: 文件路径

        Returns:
            ParsedDocument实例，解析失败返回None
        """
        if not os.path.exists(filepath):
            logger.error(f"文件不存在: {filepath}")
            return None

        doc_type = detect_file_type(filepath)
        if doc_type == "unknown":
            logger.warning(f"不支持的文件格式: {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except (IOError, OSError, UnicodeDecodeError) as e:
            logger.error(f"读取文件失败 {filepath}: {e}")
            return None

        return self.parse_text(text, doc_type, filepath)

    def parse_text(self, text: str, doc_type: str, filepath: str = "") -> Optional[ParsedDocument]:
        """解析文本内容。

        Args:
            text: 文本内容
            doc_type: 文档类型
            filepath: 文件路径（可选）

        Returns:
            ParsedDocument实例
        """
        parser = self._parsers.get(doc_type)
        if parser is None:
            logger.error(f"不支持的文档类型: {doc_type}")
            return None

        try:
            return parser.parse(text, filepath)
        except Exception as e:
            logger.error(f"解析失败 {filepath} ({doc_type}): {e}")
            return None

    def supported_types(self) -> List[str]:
        """返回支持的文档类型列表。"""
        return list(self._parsers.keys())
