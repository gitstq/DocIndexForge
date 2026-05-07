"""
DocIndexForge - CLI命令行接口模块

提供完整的命令行接口：index、search、analyze、export、
import、stats、tui、serve 等子命令。
纯Python标准库实现，零外部依赖。
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

from .indexer import IndexEngine
from .searcher import SearchEngine
from .analyzer import AnalysisEngine
from .utils import (
    Color, colored, Config, ProgressBar,
    logger, format_table, truncate, DEFAULT_CONFIG
)


# ============================================================
# CLI 应用
# ============================================================

class CLI:
    """DocIndexForge 命令行接口。"""

    # 默认索引存储路径（当前工作目录下）
    DEFAULT_INDEX_PATH = ".docindexforge_index.json"

    def __init__(self):
        """初始化CLI。"""
        self.config = Config()
        self._index_path = os.environ.get(
            "DOCINDEXFORGE_INDEX", self.DEFAULT_INDEX_PATH
        )
        self.index_engine = IndexEngine(
            k1=self.config.get("bm25_k1", 1.5),
            b=self.config.get("bm25_b", 0.75),
        )
        self.search_engine: Optional[SearchEngine] = None
        self.analysis_engine: Optional[AnalysisEngine] = None

        # 自动加载已有索引
        self._auto_load_index()

    def _auto_load_index(self) -> None:
        """自动加载已有索引文件。"""
        if os.path.exists(self._index_path):
            try:
                self.index_engine.import_index(self._index_path)
                logger.debug(f"已自动加载索引: {self._index_path}")
            except Exception as e:
                logger.debug(f"索引加载失败: {e}")

    def _auto_save_index(self) -> None:
        """自动保存索引到文件。"""
        if self.index_engine.documents:
            try:
                self.index_engine.export_index(self._index_path)
                logger.debug(f"已自动保存索引: {self._index_path}")
            except Exception as e:
                logger.debug(f"索引保存失败: {e}")

    def _init_engines(self) -> None:
        """延迟初始化搜索引擎和分析引擎。"""
        if self.search_engine is None:
            self.search_engine = SearchEngine(
                self.index_engine,
                snippet_length=self.config.get("snippet_length", 200),
                context_lines=self.config.get("context_lines", 2),
                fuzzy_threshold=self.config.get("fuzzy_threshold", 2),
            )
        if self.analysis_engine is None:
            self.analysis_engine = AnalysisEngine(self.index_engine)

    def run(self, args: Optional[list] = None) -> int:
        """运行CLI。

        Args:
            args: 命令行参数列表，为None则使用sys.argv

        Returns:
            退出码
        """
        parser = self._build_parser()
        parsed = parser.parse_args(args)

        # 设置日志级别
        log_level = getattr(parsed, "verbose", None)
        if log_level == "debug":
            logger.setLevel(10)  # DEBUG
        elif log_level == "quiet":
            logger.setLevel(40)  # ERROR

        # 执行子命令
        if not hasattr(parsed, "func"):
            parser.print_help()
            return 1

        try:
            return parsed.func(parsed)
        except KeyboardInterrupt:
            print(colored("\n操作已取消", Color.YELLOW))
            return 130
        except Exception as e:
            logger.error(f"执行失败: {e}")
            print(colored(f"错误: {e}", Color.RED))
            return 1

    def _build_parser(self) -> argparse.ArgumentParser:
        """构建参数解析器。

        Returns:
            ArgumentParser实例
        """
        parser = argparse.ArgumentParser(
            prog="docindexforge",
            description="DocIndexForge - 文档智能索引与语义检索引擎",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  %(prog)s index ./docs                    索引目录
  %(prog)s index ./docs -r                 递归索引目录
  %(prog)s search "关键词"                 搜索文档
  %(prog)s search "python AND web"         布尔搜索
  %(prog)s analyze                         分析索引
  %(prog)s export index.json               导出索引
  %(prog)s import index.json               导入索引
  %(prog)s stats                           显示统计
  %(prog)s tui                             启动TUI界面
  %(prog)s serve                           启动HTTP服务
""",
        )

        parser.add_argument(
            "-v", "--verbose",
            choices=["debug", "quiet"],
            default=None,
            help="日志级别 (debug/quiet)",
        )

        subparsers = parser.add_subparsers(dest="command", help="子命令")

        # index 命令
        index_parser = subparsers.add_parser("index", help="索引文档/目录")
        index_parser.add_argument("path", help="文件或目录路径")
        index_parser.add_argument("-r", "--recursive", action="store_true", default=True, help="递归索引")
        index_parser.add_argument("--no-recursive", action="store_false", dest="recursive", help="不递归")
        index_parser.add_argument("--update", action="store_true", help="增量更新")
        index_parser.add_argument("--build", action="store_true", default=True, help="构建索引")
        index_parser.set_defaults(func=self._cmd_index)

        # search 命令
        search_parser = subparsers.add_parser("search", help="搜索文档")
        search_parser.add_argument("query", nargs="?", default="", help="搜索查询")
        search_parser.add_argument("-n", "--max", type=int, default=20, help="最大结果数")
        search_parser.add_argument("-s", "--strategy", choices=["bm25", "tfidf", "boolean"], default="bm25", help="搜索策略")
        search_parser.add_argument("-f", "--fields", default="all", help="搜索字段 (all/content/title)")
        search_parser.add_argument("--json", action="store_true", dest="output_json", help="JSON格式输出")
        search_parser.set_defaults(func=self._cmd_search)

        # analyze 命令
        analyze_parser = subparsers.add_parser("analyze", help="分析文档")
        analyze_parser.add_argument("path", nargs="?", default="", help="文件路径（为空则分析全部索引）")
        analyze_parser.add_argument("--frequency", action="store_true", help="显示词频分析")
        analyze_parser.add_argument("--top", type=int, default=20, help="高频词数量")
        analyze_parser.add_argument("--health", action="store_true", help="显示健康报告")
        analyze_parser.set_defaults(func=self._cmd_analyze)

        # export 命令
        export_parser = subparsers.add_parser("export", help="导出索引")
        export_parser.add_argument("output", help="输出文件路径")
        export_parser.set_defaults(func=self._cmd_export)

        # import 命令
        import_parser = subparsers.add_parser("import", help="导入索引")
        import_parser.add_argument("input", help="输入文件路径")
        import_parser.set_defaults(func=self._cmd_import)

        # stats 命令
        stats_parser = subparsers.add_parser("stats", help="显示统计信息")
        stats_parser.set_defaults(func=self._cmd_stats)

        # tui 命令
        tui_parser = subparsers.add_parser("tui", help="启动TUI界面")
        tui_parser.set_defaults(func=self._cmd_tui)

        # serve 命令
        serve_parser = subparsers.add_parser("serve", help="启动HTTP API服务")
        serve_parser.add_argument("--host", default="127.0.0.1", help="监听地址")
        serve_parser.add_argument("-p", "--port", type=int, default=8765, help="监听端口")
        serve_parser.set_defaults(func=self._cmd_serve)

        return parser

    # ============================================================
    # 子命令实现
    # ============================================================

    def _cmd_index(self, args: argparse.Namespace) -> int:
        """处理 index 子命令。"""
        path = args.path
        if not os.path.exists(path):
            print(colored(f"路径不存在: {path}", Color.RED))
            return 1

        if args.update:
            added, updated, removed = self.index_engine.incremental_update(
                path, recursive=args.recursive
            )
            print(colored(f"增量更新完成:", Color.GREEN, bold=True))
            print(f"  新增: {added}")
            print(f"  更新: {updated}")
            print(f"  移除: {removed}")
        else:
            if os.path.isfile(path):
                doc_id = self.index_engine.index_document(path)
                if doc_id:
                    print(colored(f"已索引: {path}", Color.GREEN))
                else:
                    print(colored(f"索引失败: {path}", Color.RED))
                    return 1
            else:
                count = self.index_engine.index_directory(
                    path, recursive=args.recursive
                )
                print(colored(f"已索引 {count} 个文档", Color.GREEN))

        if args.build:
            print(colored("构建索引...", Color.YELLOW))
            self.index_engine.build_all_indexes()
            print(colored("索引构建完成", Color.GREEN))

        # 自动保存索引
        self._auto_save_index()

        return 0

    def _cmd_search(self, args: argparse.Namespace) -> int:
        """处理 search 子命令。"""
        self._init_engines()

        query = args.query
        if not query:
            # 交互式搜索
            print(colored("交互式搜索模式 (输入 q 退出)", Color.CYAN, bold=True))
            print()

            while True:
                try:
                    query = input(colored("搜索> ", Color.GREEN))
                except (EOFError, KeyboardInterrupt):
                    break

                if not query or query.strip().lower() == "q":
                    break

                self._do_search(query.strip(), args.max, args.strategy, args.fields, args.output_json)
                print()

            return 0

        return self._do_search(query, args.max, args.strategy, args.fields, args.output_json)

    def _do_search(
        self,
        query: str,
        max_results: int,
        strategy: str,
        fields: str,
        output_json: bool,
    ) -> int:
        """执行搜索并显示结果。

        Args:
            query: 搜索查询
            max_results: 最大结果数
            strategy: 搜索策略
            fields: 搜索字段
            output_json: 是否JSON输出

        Returns:
            退出码
        """
        field_list = fields.split(",") if fields != "all" else None

        results = self.search_engine.search(
            query=query,
            max_results=max_results,
            strategy=strategy,
            fields=field_list,
        )

        if output_json:
            output = {
                "query": query,
                "strategy": strategy,
                "total": len(results),
                "results": [r.to_dict() for r in results],
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            if not results:
                print(colored("未找到匹配结果", Color.YELLOW))
                return 0

            print(colored(f"搜索结果: \"{query}\" (策略: {strategy})", Color.CYAN, bold=True))
            print(colored(f"共 {len(results)} 条结果", Color.DIM))
            print()

            for i, r in enumerate(results, 1):
                score = colored(f"{r.score:.4f}", Color.GREEN)
                title = colored(truncate(r.title or "无标题", 60), Color.WHITE, bold=True)
                path = colored(r.filepath, Color.DIM)

                print(f"  {colored(f'{i}.', Color.YELLOW)} {score}  {title}")
                print(f"      {path}")

                if r.snippet:
                    snippet = truncate(r.snippet, 150)
                    print(f"      {colored(snippet, Color.DIM)}")

                if r.matched_terms:
                    terms = ", ".join(sorted(r.matched_terms)[:10])
                    print(f"      匹配词: {colored(terms, Color.CYAN)}")

                print()

        return 0

    def _cmd_analyze(self, args: argparse.Namespace) -> int:
        """处理 analyze 子命令。"""
        self._init_engines()

        if args.path:
            # 分析单个文件
            doc_id = self.index_engine.index_document(args.path)
            if not doc_id:
                print(colored(f"无法解析文件: {args.path}", Color.RED))
                return 1

            self.index_engine.build_all_indexes()
            stats = self.analysis_engine.analyze_document(doc_id)
            if stats:
                print(stats.format_report())
            return 0

        # 分析整个索引
        if not self.index_engine.documents:
            print(colored("索引为空，请先索引文档", Color.YELLOW))
            return 1

        if args.health:
            print(self.analysis_engine.format_health_report())
        elif args.frequency:
            wf = self.analysis_engine.word_frequency(top_n=args.top)
            print(wf.format_report(args.top))
        else:
            # 显示完整分析
            print(self.analysis_engine.global_stats())
            print()
            wf = self.analysis_engine.word_frequency(top_n=15)
            print(wf.format_report(15))
            print()
            print(self.analysis_engine.format_health_report())

        return 0

    def _cmd_export(self, args: argparse.Namespace) -> int:
        """处理 export 子命令。"""
        if not self.index_engine.documents:
            print(colored("索引为空，无内容可导出", Color.YELLOW))
            return 1

        success = self.index_engine.export_index(args.output)
        if success:
            print(colored(f"索引已导出到: {args.output}", Color.GREEN))
            return 0
        else:
            print(colored("导出失败", Color.RED))
            return 1

    def _cmd_import(self, args: argparse.Namespace) -> int:
        """处理 import 子命令。"""
        if not os.path.exists(args.input):
            print(colored(f"文件不存在: {args.input}", Color.RED))
            return 1

        success = self.index_engine.import_index(args.input)
        if success:
            stats = self.index_engine.get_stats()
            print(colored(f"索引已导入: {stats['total_documents']} 个文档", Color.GREEN))
            # 同步保存到默认路径
            self._auto_save_index()
            return 0
        else:
            print(colored("导入失败", Color.RED))
            return 1

    def _cmd_stats(self, args: argparse.Namespace) -> int:
        """处理 stats 子命令。"""
        self._init_engines()

        if not self.index_engine.documents:
            print(colored("索引为空", Color.YELLOW))
            return 0

        stats = self.index_engine.get_stats()

        print(colored("索引统计", Color.CYAN, bold=True))
        print(colored("─────────────────────────────", Color.BLUE))
        print(f"  文档总数:     {stats['total_documents']}")
        print(f"  总词元数:     {stats['total_tokens']:,}")
        print(f"  唯一词元数:   {stats['unique_tokens']:,}")
        print(f"  平均文档长度: {stats['avg_doc_length']:.1f}")
        print(f"  索引大小:     {stats['index_size_bytes'] / 1024:.1f} KB")

        if stats.get("last_updated"):
            updated = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(stats["last_updated"])
            )
            print(f"  最后更新:     {updated}")

        return 0

    def _cmd_tui(self, args: argparse.Namespace) -> int:
        """处理 tui 子命令。"""
        self._init_engines()

        if not self.index_engine.documents:
            print(colored("索引为空，请先使用 'index' 命令索引文档", Color.YELLOW))
            return 1

        try:
            from .tui import TUI
            tui = TUI(self.index_engine, self.search_engine, self.analysis_engine)
            tui.run()
        except ImportError as e:
            print(colored(f"TUI模块加载失败: {e}", Color.RED))
            return 1
        except Exception as e:
            print(colored(f"TUI运行错误: {e}", Color.RED))
            return 1

        return 0

    def _cmd_serve(self, args: argparse.Namespace) -> int:
        """处理 serve 子命令。"""
        if not self.index_engine.documents:
            print(colored("索引为空，服务将以空索引启动", Color.YELLOW))

        self._init_engines()
        self.index_engine.build_all_indexes()

        try:
            from .server import ServerApp
            app = ServerApp(
                self.index_engine,
                host=args.host,
                port=args.port,
            )
            app.run()
        except ImportError as e:
            print(colored(f"服务模块加载失败: {e}", Color.RED))
            return 1
        except Exception as e:
            print(colored(f"服务启动失败: {e}", Color.RED))
            return 1

        return 0


def main(args: Optional[list] = None) -> int:
    """CLI入口函数。

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    cli = CLI()
    return cli.run(args)
