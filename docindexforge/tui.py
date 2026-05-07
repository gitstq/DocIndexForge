"""
DocIndexForge - TUI终端交互界面模块

提供终端交互界面：搜索结果分页显示、文档详情查看、
统计仪表盘、颜色主题、键盘导航。
纯Python标准库实现，零外部依赖。
"""

import sys
import os
import termios
import tty
import select
from typing import Dict, List, Any, Optional, Callable

from .indexer import IndexEngine
from .searcher import SearchEngine, SearchResult
from .analyzer import AnalysisEngine
from .utils import Color, colored, format_table, truncate, logger


# ============================================================
# 终端工具
# ============================================================

class Terminal:
    """终端控制工具类。"""

    def __init__(self):
        """初始化终端。"""
        self._original_settings = None

    def get_terminal_size(self) -> tuple:
        """获取终端大小。

        Returns:
            (行数, 列数) 元组
        """
        try:
            import shutil
            size = shutil.get_terminal_size()
            return (size.lines, size.columns)
        except Exception:
            return (24, 80)

    def clear_screen(self) -> None:
        """清屏。"""
        os.system("clear" if os.name != "Windows" else "cls")

    def move_cursor(self, row: int = 0, col: int = 0) -> None:
        """移动光标位置。

        Args:
            row: 行号
            col: 列号
        """
        sys.stdout.write(f"\033[{row};{col}H")
        sys.stdout.flush()

    def hide_cursor(self) -> None:
        """隐藏光标。"""
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    def show_cursor(self) -> None:
        """显示光标。"""
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    def read_key(self) -> str:
        """读取单个按键。

        Returns:
            按键字符串
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # 读取转义序列
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch += sys.stdin.read(2)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def input_line(self, prompt: str = "") -> str:
        """读取一行输入。

        Args:
            prompt: 提示符

        Returns:
            输入字符串
        """
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return ""


# ============================================================
# 颜色主题
# ============================================================

class Theme:
    """颜色主题。"""

    def __init__(
        self,
        title_color: str = Color.CYAN,
        header_color: str = Color.YELLOW,
        accent_color: str = Color.GREEN,
        error_color: str = Color.RED,
        dim_color: str = Color.DIM,
        text_color: str = Color.WHITE,
        highlight_color: str = Color.YELLOW,
        border_color: str = Color.BLUE,
    ):
        """初始化主题。

        Args:
            title_color: 标题颜色
            header_color: 表头颜色
            accent_color: 强调颜色
            error_color: 错误颜色
            dim_color: 暗淡颜色
            text_color: 文本颜色
            highlight_color: 高亮颜色
            border_color: 边框颜色
        """
        self.title_color = title_color
        self.header_color = header_color
        self.accent_color = accent_color
        self.error_color = error_color
        self.dim_color = dim_color
        self.text_color = text_color
        self.highlight_color = highlight_color
        self.border_color = border_color


# ============================================================
# 分页显示
# ============================================================

class PagedView:
    """分页显示视图。"""

    def __init__(self, terminal: Terminal, theme: Theme, page_size: int = 10):
        """初始化分页视图。

        Args:
            terminal: 终端实例
            theme: 颜色主题
            page_size: 每页显示数量
        """
        self.terminal = terminal
        self.theme = theme
        self.page_size = page_size
        self.current_page = 0
        self.total_items = 0

    def render(
        self,
        title: str,
        items: List[str],
        footer: str = "",
    ) -> None:
        """渲染分页内容。

        Args:
            title: 标题
            items: 内容行列表
            footer: 页脚信息
        """
        self.total_items = len(items)
        total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
        self.current_page = min(self.current_page, total_pages - 1)

        start = self.current_page * self.page_size
        end = min(start + self.page_size, self.total_items)
        page_items = items[start:end]

        _, cols = self.terminal.get_terminal_size()
        border = "─" * min(cols - 4, 60)

        self.terminal.clear_screen()

        # 标题
        print(colored(f"  {title}", self.theme.title_color, bold=True))
        print(colored(f"  {border}", self.theme.border_color))
        print()

        # 内容
        for i, item in enumerate(page_items):
            idx = start + i + 1
            print(f"  {colored(f'{idx:>4}.', self.theme.dim_color)} {item}")

        # 空行填充
        remaining = self.page_size - len(page_items)
        for _ in range(max(0, remaining)):
            print()

        # 分页信息
        page_info = f"  页 {self.current_page + 1}/{total_pages}  |  共 {self.total_items} 项"
        if footer:
            page_info += f"  |  {footer}"

        print(colored(f"  {border}", self.theme.border_color))
        print(colored(page_info, self.theme.dim_color))
        print(colored("  [n]下一页 [p]上一页 [q]返回", self.theme.dim_color))


# ============================================================
# TUI主界面
# ============================================================

class TUI:
    """终端交互界面主类。"""

    def __init__(
        self,
        index_engine: IndexEngine,
        search_engine: SearchEngine,
        analysis_engine: AnalysisEngine,
    ):
        """初始化TUI。

        Args:
            index_engine: 索引引擎
            search_engine: 检索引擎
            analysis_engine: 分析引擎
        """
        self.index = index_engine
        self.searcher = search_engine
        self.analyzer = analysis_engine
        self.terminal = Terminal()
        self.theme = Theme()
        self.running = True

    def run(self) -> None:
        """启动TUI主循环。"""
        self.terminal.clear_screen()
        self._show_banner()

        while self.running:
            self._show_main_menu()
            choice = self.terminal.input_line(colored("  请选择 > ", self.theme.accent_color))

            if not choice:
                continue

            cmd = choice.strip().lower()

            if cmd == "1" or cmd == "s" or cmd == "search":
                self._search_mode()
            elif cmd == "2" or cmd == "d" or cmd == "docs":
                self._docs_mode()
            elif cmd == "3" or cmd == "a" or cmd == "analyze":
                self._analyze_mode()
            elif cmd == "4" or cmd == "t" or cmd == "stats":
                self._stats_mode()
            elif cmd == "5" or cmd == "h" or cmd == "help":
                self._show_help()
            elif cmd == "q" or cmd == "exit" or cmd == "quit":
                self.running = False
            else:
                print(colored("  无效选择，请重新输入", self.theme.error_color))

        self.terminal.clear_screen()
        print(colored("  再见！", self.theme.title_color))

    def _show_banner(self) -> None:
        """显示欢迎横幅。"""
        banner = f"""
  {colored('╔══════════════════════════════════════════╗', self.theme.border_color)}
  {colored('║', self.theme.border_color)}       {colored('DocIndexForge', self.theme.title_color, bold=True)}              {colored('║', self.theme.border_color)}
  {colored('║', self.theme.border_color)}   文档智能索引与语义检索引擎      {colored('║', self.theme.border_color)}
  {colored('║', self.theme.border_color)}   Document Index & Search Engine  {colored('║', self.theme.border_color)}
  {colored('╚══════════════════════════════════════════╝', self.theme.border_color)}
"""
        print(banner)

        stats = self.index.get_stats()
        doc_count = stats.get("total_documents", 0)
        print(f"  已索引文档: {colored(str(doc_count), self.theme.accent_color)}")
        print()

    def _show_main_menu(self) -> None:
        """显示主菜单。"""
        print(colored("  ── 主菜单 ──", self.theme.header_color))
        print(f"    {colored('1', self.theme.accent_color)}. 搜索文档 (search)")
        print(f"    {colored('2', self.theme.accent_color)}. 浏览文档 (docs)")
        print(f"    {colored('3', self.theme.accent_color)}. 分析文档 (analyze)")
        print(f"    {colored('4', self.theme.accent_color)}. 统计信息 (stats)")
        print(f"    {colored('5', self.theme.accent_color)}. 帮助 (help)")
        print(f"    {colored('q', self.theme.error_color)}. 退出 (quit)")
        print()

    def _show_help(self) -> None:
        """显示帮助信息。"""
        self.terminal.clear_screen()
        help_text = f"""
  {colored('DocIndexForge 使用帮助', self.theme.title_color, bold=True)}
  {colored('─────────────────────────────────────────', self.theme.border_color)}

  {colored('搜索功能:', self.theme.header_color)}
    - 支持关键词搜索、布尔查询 (AND/OR/NOT)
    - 支持模糊匹配（自动扩展相似词）
    - 搜索结果按相关度排序

  {colored('布尔查询示例:', self.theme.header_color)}
    - python AND web        同时包含两个词
    - python OR java        包含任一词
    - python NOT test       包含python但不包含test

  {colored('快捷键:', self.theme.header_color)}
    - [n] 下一页
    - [p] 上一页
    - [q] 返回上级

"""
        print(help_text)
        self.terminal.input_line(colored("  按回车键返回...", self.theme.dim_color))

    # ============================================================
    # 搜索模式
    # ============================================================

    def _search_mode(self) -> None:
        """搜索模式。"""
        while True:
            self.terminal.clear_screen()
            print(colored("  ── 搜索模式 ──", self.theme.title_color, bold=True))
            print()

            query = self.terminal.input_line(
                colored("  输入搜索词 (q返回): ", self.theme.accent_color)
            )

            if not query or query.strip().lower() == "q":
                return

            # 执行搜索
            results = self.searcher.search(query.strip(), max_results=50)

            if not results:
                print(colored("  未找到匹配结果", self.theme.error_color))
                self.terminal.input_line(colored("  按回车键继续...", self.theme.dim_color))
                continue

            # 格式化结果
            items = []
            for r in results:
                score_str = colored(f"{r.score:.4f}", self.theme.accent_color)
                title_str = colored(truncate(r.title or "无标题", 50), self.theme.text_color, bold=True)
                path_str = colored(truncate(r.filepath, 60), self.theme.dim_color)
                items.append(f"{score_str}  {title_str}\n          {path_str}")

            # 分页显示
            paged = PagedView(self.terminal, self.theme, page_size=8)
            paged.render(f"搜索结果: {query}", items, footer=f"共 {len(results)} 条结果")

            # 交互导航
            while True:
                try:
                    key = self.terminal.input_line()
                    if key.lower() == "n":
                        paged.current_page += 1
                        paged.render(f"搜索结果: {query}", items, footer=f"共 {len(results)} 条结果")
                    elif key.lower() == "p":
                        paged.current_page = max(0, paged.current_page - 1)
                        paged.render(f"搜索结果: {query}", items, footer=f"共 {len(results)} 条结果")
                    elif key.lower() == "q":
                        break
                except (EOFError, KeyboardInterrupt):
                    break

    # ============================================================
    # 文档浏览模式
    # ============================================================

    def _docs_mode(self) -> None:
        """文档浏览模式。"""
        doc_ids = self.index.get_all_doc_ids()

        if not doc_ids:
            print(colored("  索引中没有文档", self.theme.error_color))
            self.terminal.input_line(colored("  按回车键继续...", self.theme.dim_color))
            return

        items = []
        for doc_id in doc_ids:
            doc = self.index.get_document(doc_id)
            if doc is None:
                continue
            title = colored(truncate(doc.title or "无标题", 40), self.theme.text_color, bold=True)
            dtype = colored(f"[{doc.doc_type}]", self.theme.dim_color)
            path = colored(truncate(doc.filepath, 50), self.theme.dim_color)
            items.append(f"{dtype} {title}\n          {path}")

        paged = PagedView(self.terminal, self.theme, page_size=8)
        paged.render("文档列表", items)

        while True:
            try:
                key = self.terminal.input_line()
                if key.lower() == "n":
                    paged.current_page += 1
                    paged.render("文档列表", items)
                elif key.lower() == "p":
                    paged.current_page = max(0, paged.current_page - 1)
                    paged.render("文档列表", items)
                elif key.lower() == "q":
                    break
                elif key.strip().isdigit():
                    # 查看文档详情
                    idx = int(key.strip()) - 1
                    if 0 <= idx < len(doc_ids):
                        self._show_doc_detail(doc_ids[idx])
                    paged.render("文档列表", items)
            except (EOFError, KeyboardInterrupt):
                break

    def _show_doc_detail(self, doc_id: str) -> None:
        """显示文档详情。

        Args:
            doc_id: 文档ID
        """
        doc = self.index.get_document(doc_id)
        if doc is None:
            return

        stats = self.analyzer.analyze_document(doc_id)
        if stats is None:
            return

        self.terminal.clear_screen()
        print(colored("  ── 文档详情 ──", self.theme.title_color, bold=True))
        print()
        print(stats.format_report())
        print()

        # 显示前几行内容
        if doc.content:
            lines = doc.content.split("\n")[:20]
            print(colored("  内容预览 (前20行):", self.theme.header_color))
            print(colored("  ──────────────────────", self.theme.border_color))
            for line in lines:
                print(f"  {line}")
            if len(doc.content.split("\n")) > 20:
                print(colored("  ... (更多内容省略)", self.theme.dim_color))

        print()
        self.terminal.input_line(colored("  按回车键返回...", self.theme.dim_color))

    # ============================================================
    # 分析模式
    # ============================================================

    def _analyze_mode(self) -> None:
        """分析模式。"""
        self.terminal.clear_screen()
        print(colored("  ── 分析模式 ──", self.theme.title_color, bold=True))
        print()

        # 词频分析
        wf = self.analyzer.word_frequency(top_n=15)
        print(wf.format_report(15))
        print()

        # 索引健康报告
        print(self.analyzer.format_health_report())
        print()

        self.terminal.input_line(colored("  按回车键返回...", self.theme.dim_color))

    # ============================================================
    # 统计模式
    # ============================================================

    def _stats_mode(self) -> None:
        """统计模式。"""
        self.terminal.clear_screen()
        print(colored("  ── 统计仪表盘 ──", self.theme.title_color, bold=True))
        print()
        print(self.analyzer.global_stats())
        print()
        self.terminal.input_line(colored("  按回车键返回...", self.theme.dim_color))
