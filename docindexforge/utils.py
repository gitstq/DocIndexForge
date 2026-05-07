"""
DocIndexForge - 通用工具模块

提供文件遍历、进度条、颜色输出、配置管理等通用工具函数。
纯Python标准库实现，零外部依赖。
"""

import os
import sys
import json
import time
import logging
import platform
from typing import List, Dict, Any, Optional, Generator, Tuple
from pathlib import Path

# ============================================================
# 日志配置
# ============================================================

def setup_logger(
    name: str = "docindexforge",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
) -> logging.Logger:
    """配置并返回日志记录器。

    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径，为None则仅输出到终端
        fmt: 日志格式字符串

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(fmt)

    # 终端输出
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# ============================================================
# ANSI 颜色输出
# ============================================================

class Color:
    """ANSI终端颜色常量。"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def colored(text: str, color: str, bold: bool = False) -> str:
    """为文本添加ANSI颜色。

    Args:
        text: 要着色的文本
        color: ANSI颜色代码
        bold: 是否加粗

    Returns:
        着色后的文本字符串
    """
    prefix = color
    if bold:
        prefix = Color.BOLD + color
    return f"{prefix}{text}{Color.RESET}"


def color_enabled() -> bool:
    """检测终端是否支持颜色输出。"""
    if platform.system() == "Windows":
        return os.environ.get("ANSICON") is not None or "256color" in os.environ.get("TERM", "")
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


# ============================================================
# 进度条
# ============================================================

class ProgressBar:
    """简单的终端进度条。"""

    def __init__(
        self,
        total: int,
        width: int = 40,
        prefix: str = "",
        fill_char: str = "=",
        empty_char: str = "-",
        show_percent: bool = True,
        show_count: bool = True
    ):
        """初始化进度条。

        Args:
            total: 总项目数
            width: 进度条宽度（字符数）
            prefix: 前缀文本
            fill_char: 填充字符
            empty_char: 空白字符
            show_percent: 是否显示百分比
            show_count: 是否显示计数
        """
        self.total = total
        self.width = width
        self.prefix = prefix
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.show_percent = show_percent
        self.show_count = show_count
        self.current = 0
        self.start_time = time.time()
        self._use_color = color_enabled()

    def update(self, current: Optional[int] = None) -> None:
        """更新进度条显示。

        Args:
            current: 当前进度值，为None则自动+1
        """
        if current is not None:
            self.current = current
        else:
            self.current += 1

        if self.total <= 0:
            return

        ratio = min(self.current / self.total, 1.0)
        filled = int(self.width * ratio)
        empty = self.width - filled

        bar = self.fill_char * filled + self.empty_char * empty

        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = elapsed / self.current * (self.total - self.current)
        else:
            eta = 0

        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(f"[{bar}]")

        if self.show_percent:
            parts.append(f"{ratio * 100:.1f}%")

        if self.show_count:
            parts.append(f"({self.current}/{self.total})")

        parts.append(f"ETA: {eta:.1f}s")

        line = " ".join(parts)
        sys.stderr.write(f"\r{line}")
        sys.stderr.flush()

        if self.current >= self.total:
            sys.stderr.write("\n")
            sys.stderr.flush()

    def finish(self) -> None:
        """完成进度条。"""
        self.update(self.total)


# ============================================================
# 文件遍历
# ============================================================

SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".html", ".htm"}

DEFAULT_IGNORE_DIRS = {
    ".git", "__pycache__", ".idea", ".vscode",
    "node_modules", ".svn", ".hg", "venv", ".venv",
    "env", ".env", ".tox", "dist", "build", ".eggs"
}

DEFAULT_IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", ".gitkeep"
}


def walk_files(
    path: str,
    extensions: Optional[set] = None,
    ignore_dirs: Optional[set] = None,
    ignore_files: Optional[set] = None,
    recursive: bool = True
) -> Generator[str, None, None]:
    """遍历目录，生成匹配的文件路径。

    Args:
        path: 要遍历的目录或文件路径
        extensions: 允许的文件扩展名集合，为None则使用默认值
        ignore_dirs: 要忽略的目录名集合
        ignore_files: 要忽略的文件名集合
        recursive: 是否递归遍历子目录

    Yields:
        匹配的文件绝对路径
    """
    if extensions is None:
        extensions = SUPPORTED_EXTENSIONS
    if ignore_dirs is None:
        ignore_dirs = DEFAULT_IGNORE_DIRS
    if ignore_files is None:
        ignore_files = DEFAULT_IGNORE_FILES

    target = Path(path).resolve()

    if target.is_file():
        if target.suffix.lower() in extensions:
            yield str(target)
        return

    if not target.is_dir():
        logger.warning(f"路径不存在或不可访问: {path}")
        return

    if recursive:
        for root, dirs, files in os.walk(str(target)):
            # 过滤忽略的目录（原地修改dirs以阻止os.walk递归进入）
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            dirs.sort()

            for filename in sorted(files):
                if filename in ignore_files:
                    continue
                filepath = os.path.join(root, filename)
                ext = Path(filename).suffix.lower()
                if ext in extensions:
                    yield filepath
    else:
        for item in sorted(target.iterdir()):
            if item.is_file() and item.suffix.lower() in extensions:
                if item.name not in ignore_files:
                    yield str(item)


def get_file_metadata(filepath: str) -> Dict[str, Any]:
    """获取文件元数据。

    Args:
        filepath: 文件路径

    Returns:
        包含文件元数据的字典
    """
    p = Path(filepath)
    stat = p.stat()
    return {
        "filename": p.name,
        "filepath": str(p),
        "extension": p.suffix.lower(),
        "size_bytes": stat.st_size,
        "size_human": _human_readable_size(stat.st_size),
        "modified_time": stat.st_mtime,
        "modified_time_str": time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)
        ),
        "created_time": stat.st_ctime,
        "is_file": p.is_file(),
        "is_dir": p.is_dir(),
    }


def _human_readable_size(size: int) -> str:
    """将字节数转换为人类可读的大小格式。

    Args:
        size: 字节数

    Returns:
        人类可读的大小字符串
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def detect_file_type(filepath: str) -> str:
    """根据文件扩展名检测文件类型。

    Args:
        filepath: 文件路径

    Returns:
        文件类型字符串（如 'markdown', 'text', 'json', 'csv', 'html'）
    """
    ext = Path(filepath).suffix.lower()
    type_map = {
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".csv": "csv",
        ".html": "html",
        ".htm": "html",
    }
    return type_map.get(ext, "unknown")


# ============================================================
# 配置管理
# ============================================================

DEFAULT_CONFIG = {
    "index_dir": ".docindexforge_index",
    "index_file": "index.json",
    "max_results": 20,
    "snippet_length": 200,
    "context_lines": 2,
    "bm25_k1": 1.5,
    "bm25_b": 0.75,
    "fuzzy_threshold": 2,
    "log_level": "INFO",
    "log_file": None,
    "server_host": "127.0.0.1",
    "server_port": 8765,
    "color": True,
}


class Config:
    """配置管理器，支持从文件加载和保存配置。"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器。

        Args:
            config_path: 配置文件路径，为None则使用默认路径
        """
        self._data: Dict[str, Any] = {}
        self._config_path = config_path

        if config_path and os.path.exists(config_path):
            self.load(config_path)
        else:
            self._data = dict(DEFAULT_CONFIG)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值。

        Args:
            key: 配置键
            value: 配置值
        """
        self._data[key] = value

    def load(self, config_path: Optional[str] = None) -> None:
        """从JSON文件加载配置。

        Args:
            config_path: 配置文件路径
        """
        path = config_path or self._config_path
        if not path:
            logger.warning("未指定配置文件路径")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self._data = {**DEFAULT_CONFIG, **loaded}
            self._config_path = path
            logger.debug(f"已加载配置: {path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"加载配置失败: {e}")
            self._data = dict(DEFAULT_CONFIG)

    def save(self, config_path: Optional[str] = None) -> None:
        """保存配置到JSON文件。

        Args:
            config_path: 配置文件路径
        """
        path = config_path or self._config_path
        if not path:
            logger.warning("未指定配置文件路径")
            return

        try:
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.debug(f"已保存配置: {path}")
        except (IOError, OSError) as e:
            logger.error(f"保存配置失败: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """返回配置字典的副本。"""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"Config(path={self._config_path})"


# ============================================================
# 文本工具
# ============================================================

def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本到指定长度。

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_table(
    headers: List[str],
    rows: List[List[str]],
    padding: int = 2
) -> str:
    """格式化简单文本表格。

    Args:
        headers: 表头列表
        rows: 数据行列表
        padding: 单元格内边距

    Returns:
        格式化的表格字符串
    """
    if not rows:
        return " | ".join(headers)

    # 计算每列最大宽度
    col_count = len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < col_count:
                widths[i] = max(widths[i], len(str(cell)))

    # 构建分隔线
    sep = "+" + "+".join("-" * (w + padding * 2) for w in widths) + "+"

    # 构建表头
    header_line = "|" + "|".join(
        f"{' ' * padding}{headers[i]:<{widths[i]}}{' ' * padding}"
        for i in range(col_count)
    ) + "|"

    # 构建数据行
    lines = [sep, header_line, sep]
    for row in rows:
        cells = []
        for i in range(col_count):
            val = str(row[i]) if i < len(row) else ""
            cells.append(f"{' ' * padding}{val:<{widths[i]}}{' ' * padding}")
        lines.append("|" + "|".join(cells) + "|")
    lines.append(sep)

    return "\n".join(lines)


def ensure_dir(filepath: str) -> None:
    """确保文件所在目录存在。

    Args:
        filepath: 文件路径
    """
    dirpath = os.path.dirname(filepath)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)


def safe_read(filepath: str, encoding: str = "utf-8") -> Optional[str]:
    """安全读取文件内容。

    Args:
        filepath: 文件路径
        encoding: 文件编码

    Returns:
        文件内容字符串，读取失败返回None
    """
    try:
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError) as e:
        logger.error(f"读取文件失败 {filepath}: {e}")
        return None


def safe_write(filepath: str, content: str, encoding: str = "utf-8") -> bool:
    """安全写入文件内容。

    Args:
        filepath: 文件路径
        content: 要写入的内容
        encoding: 文件编码

    Returns:
        写入成功返回True
    """
    try:
        ensure_dir(filepath)
        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except (IOError, OSError) as e:
        logger.error(f"写入文件失败 {filepath}: {e}")
        return False
