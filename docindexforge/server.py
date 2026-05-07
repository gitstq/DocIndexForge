"""
DocIndexForge - HTTP API 服务模块

提供简单的HTTP API服务，支持通过REST接口进行搜索和索引操作。
使用Python标准库 http.server 实现，零外部依赖。
"""

import json
import os
import sys
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .indexer import IndexEngine
from .searcher import SearchEngine
from .analyzer import AnalysisEngine
from .utils import logger, Color, colored


# ============================================================
# API请求处理器
# ============================================================

class APIRequestHandler(BaseHTTPRequestHandler):
    """HTTP API请求处理器。"""

    # 引擎实例（由ServerApp注入）
    index_engine: IndexEngine = None  # type: ignore
    search_engine: SearchEngine = None  # type: ignore
    analysis_engine: AnalysisEngine = None  # type: ignore

    def log_message(self, format: str, *args: Any) -> None:
        """重写日志方法。"""
        logger.debug(f"HTTP: {format % args}")

    def _send_json_response(self, data: Dict[str, Any], status: int = 200) -> None:
        """发送JSON响应。

        Args:
            data: 响应数据字典
            status: HTTP状态码
        """
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        response_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.wfile.write(response_bytes)

    def _send_error(self, message: str, status: int = 400) -> None:
        """发送错误响应。

        Args:
            message: 错误消息
            status: HTTP状态码
        """
        self._send_json_response({"error": message}, status)

    def _read_body(self) -> Optional[bytes]:
        """读取请求体。"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return None

    def _parse_path(self) -> tuple:
        """解析请求路径和查询参数。

        Returns:
            (path, query_params) 元组
        """
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    # ============================================================
    # GET 请求处理
    # ============================================================

    def do_GET(self) -> None:
        """处理GET请求。"""
        path, params = self._parse_path()

        try:
            if path == "/" or path == "/api":
                self._handle_info()
            elif path == "/api/search":
                self._handle_search(params)
            elif path == "/api/stats":
                self._handle_stats()
            elif path == "/api/health":
                self._handle_health()
            elif path == "/api/documents":
                self._handle_list_documents(params)
            elif path.startswith("/api/documents/"):
                doc_id = path.split("/")[-1]
                self._handle_get_document(doc_id)
            elif path == "/api/analyze/frequency":
                self._handle_word_frequency(params)
            elif path == "/api/analyze/similar":
                self._handle_similar_documents(params)
            else:
                self._send_error(f"未知路径: {path}", 404)

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            self._send_error(f"服务器内部错误: {str(e)}", 500)

    # ============================================================
    # POST 请求处理
    # ============================================================

    def do_POST(self) -> None:
        """处理POST请求。"""
        path, params = self._parse_path()

        try:
            if path == "/api/index":
                self._handle_index()
            elif path == "/api/index/directory":
                self._handle_index_directory()
            elif path == "/api/export":
                self._handle_export()
            elif path == "/api/import":
                self._handle_import()
            else:
                self._send_error(f"未知路径: {path}", 404)

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            self._send_error(f"服务器内部错误: {str(e)}", 500)

    # ============================================================
    # API 端点实现
    # ============================================================

    def _handle_info(self) -> None:
        """API信息端点。"""
        self._send_json_response({
            "name": "DocIndexForge API",
            "version": "1.0.0",
            "description": "文档智能索引与语义检索引擎",
            "endpoints": {
                "GET /": "API信息",
                "GET /api/search?q=xxx&max=20&strategy=bm25": "搜索文档",
                "GET /api/stats": "索引统计",
                "GET /api/health": "索引健康状态",
                "GET /api/documents": "文档列表",
                "GET /api/documents/{doc_id}": "文档详情",
                "GET /api/analyze/frequency?top_n=20": "词频分析",
                "GET /api/analyze/similar?doc_id=xxx&top_n=10": "相似文档",
                "POST /api/index": "索引单个文件",
                "POST /api/index/directory": "索引目录",
                "POST /api/export": "导出索引",
                "POST /api/import": "导入索引",
            },
        })

    def _handle_search(self, params: Dict[str, list]) -> None:
        """搜索端点。

        Args:
            params: 查询参数
        """
        query = params.get("q", [""])[0]
        if not query:
            self._send_error("缺少搜索参数 q")
            return

        max_results = int(params.get("max", ["20"])[0])
        strategy = params.get("strategy", ["bm25"])[0]
        fields = params.get("fields", [""])[0].split(",") if params.get("fields") else None

        results = self.search_engine.search(
            query=query,
            max_results=max_results,
            strategy=strategy,
            fields=fields,
        )

        self._send_json_response({
            "query": query,
            "strategy": strategy,
            "total": len(results),
            "results": [r.to_dict() for r in results],
        })

    def _handle_stats(self) -> None:
        """统计端点。"""
        stats = self.index_engine.get_stats()
        self._send_json_response(stats)

    def _handle_health(self) -> None:
        """健康检查端点。"""
        report = self.analysis_engine.health_report()
        self._send_json_response(report)

    def _handle_list_documents(self, params: Dict[str, list]) -> None:
        """文档列表端点。

        Args:
            params: 查询参数
        """
        doc_ids = self.index_engine.get_all_doc_ids()
        offset = int(params.get("offset", ["0"])[0])
        limit = int(params.get("limit", ["20"])[0])

        documents = []
        for doc_id in doc_ids[offset:offset + limit]:
            doc = self.index_engine.get_document(doc_id)
            if doc:
                documents.append({
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "filepath": doc.filepath,
                    "doc_type": doc.doc_type,
                    "token_count": doc.token_count,
                })

        self._send_json_response({
            "total": len(doc_ids),
            "offset": offset,
            "limit": limit,
            "documents": documents,
        })

    def _handle_get_document(self, doc_id: str) -> None:
        """文档详情端点。

        Args:
            doc_id: 文档ID
        """
        doc = self.index_engine.get_document(doc_id)
        if doc is None:
            self._send_error(f"文档不存在: {doc_id}", 404)
            return

        self._send_json_response(doc.to_dict())

    def _handle_word_frequency(self, params: Dict[str, list]) -> None:
        """词频分析端点。

        Args:
            params: 查询参数
        """
        doc_id = params.get("doc_id", [None])[0]
        top_n = int(params.get("top_n", ["20"])[0])

        wf = self.analysis_engine.word_frequency(
            doc_id=doc_id,
            top_n=top_n,
        )

        self._send_json_response({
            "total_words": wf.total,
            "vocabulary_size": wf.vocabulary_size,
            "top_words": [
                {"word": w, "count": c, "ratio": r}
                for w, c, r in wf.top_with_ratio(top_n)
            ],
        })

    def _handle_similar_documents(self, params: Dict[str, list]) -> None:
        """相似文档端点。

        Args:
            params: 查询参数
        """
        doc_id = params.get("doc_id", [""])[0]
        if not doc_id:
            self._send_error("缺少参数 doc_id")
            return

        top_n = int(params.get("top_n", ["10"])[0])
        threshold = float(params.get("threshold", ["0"])[0])

        similar = self.analysis_engine.find_similar_documents(
            doc_id=doc_id,
            top_n=top_n,
            threshold=threshold,
        )

        results = []
        for sid, score in similar:
            doc = self.index_engine.get_document(sid)
            if doc:
                results.append({
                    "doc_id": sid,
                    "title": doc.title,
                    "filepath": doc.filepath,
                    "similarity": round(score, 4),
                })

        self._send_json_response({
            "doc_id": doc_id,
            "similar_documents": results,
        })

    def _handle_index(self) -> None:
        """索引单个文件端点。"""
        body = self._read_body()
        if not body:
            self._send_error("请求体为空")
            return

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_error("无效的JSON格式")
            return

        filepath = data.get("filepath", "")
        if not filepath:
            self._send_error("缺少参数 filepath")
            return

        doc_id = self.index_engine.index_document(filepath)
        if doc_id:
            # 重建索引
            self.index_engine.build_all_indexes()
            self._send_json_response({
                "success": True,
                "doc_id": doc_id,
                "message": f"已索引: {filepath}",
            })
        else:
            self._send_error(f"索引失败: {filepath}")

    def _handle_index_directory(self) -> None:
        """索引目录端点。"""
        body = self._read_body()
        if not body:
            self._send_error("请求体为空")
            return

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_error("无效的JSON格式")
            return

        directory = data.get("directory", "")
        recursive = data.get("recursive", True)

        if not directory:
            self._send_error("缺少参数 directory")
            return

        count = self.index_engine.index_directory(directory, recursive=recursive)
        self.index_engine.build_all_indexes()

        self._send_json_response({
            "success": True,
            "indexed_count": count,
            "message": f"已索引 {count} 个文档",
        })

    def _handle_export(self) -> None:
        """导出索引端点。"""
        body = self._read_body()
        if not body:
            self._send_error("请求体为空")
            return

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_error("无效的JSON格式")
            return

        filepath = data.get("filepath", "index_export.json")
        success = self.index_engine.export_index(filepath)

        if success:
            self._send_json_response({
                "success": True,
                "message": f"索引已导出到: {filepath}",
            })
        else:
            self._send_error("导出失败")

    def _handle_import(self) -> None:
        """导入索引端点。"""
        body = self._read_body()
        if not body:
            self._send_error("请求体为空")
            return

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_error("无效的JSON格式")
            return

        filepath = data.get("filepath", "")
        if not filepath:
            self._send_error("缺少参数 filepath")
            return

        success = self.index_engine.import_index(filepath)

        if success:
            self._send_json_response({
                "success": True,
                "message": f"索引已从 {filepath} 导入",
            })
        else:
            self._send_error("导入失败")


# ============================================================
# HTTP服务应用
# ============================================================

class ServerApp:
    """HTTP API服务应用。"""

    def __init__(
        self,
        index_engine: IndexEngine,
        host: str = "127.0.0.1",
        port: int = 8765,
    ):
        """初始化服务应用。

        Args:
            index_engine: 索引引擎
            host: 监听地址
            port: 监听端口
        """
        self.index_engine = index_engine
        self.search_engine = SearchEngine(index_engine)
        self.analysis_engine = AnalysisEngine(index_engine)
        self.host = host
        self.port = port

        # 注入引擎实例到请求处理器
        APIRequestHandler.index_engine = index_engine
        APIRequestHandler.search_engine = self.search_engine
        APIRequestHandler.analysis_engine = self.analysis_engine

    def run(self) -> None:
        """启动HTTP服务。"""
        server = HTTPServer((self.host, self.port), APIRequestHandler)

        print(colored(f"  DocIndexForge HTTP API 服务", Color.CYAN, bold=True))
        print(colored(f"  ─────────────────────────────", Color.BLUE))
        print(f"  地址: http://{self.host}:{self.port}")
        print(f"  API:  http://{self.host}:{self.port}/api")
        print()
        print(colored("  按 Ctrl+C 停止服务", Color.YELLOW))
        print()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print(colored("\n  服务已停止", Color.YELLOW))
        finally:
            server.server_close()
