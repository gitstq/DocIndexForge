<div align="center">

# DocIndexForge

**Lightweight Document Intelligent Indexing & Semantic Search Engine CLI**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-green.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)]()

[English](#english) | [简体中文](#简体中文)

</div>

---

## 简体中文

### 项目介绍

在信息爆炸的时代，我们每天都在与海量文档打交道——技术文档、项目笔记、知识库、日志文件……如何在这些文档中快速找到所需内容，成了一个普遍存在的痛点。

**DocIndexForge** 正是为解决这一问题而生的轻量级文档智能索引与语义检索引擎。它是一个纯 Python 标准库实现的 CLI 工具，**零外部依赖**，开箱即用，无需配置向量数据库或安装复杂的环境。

**核心价值：**

- **极简部署** —— `pip install` 一条命令搞定，不依赖任何第三方库
- **多格式支持** —— Markdown、TXT、JSON、CSV、HTML，常见文档格式通吃
- **专业级检索** —— 内置 TF-IDF、BM25、倒排索引三种策略，支持布尔查询与模糊匹配
- **中英文友好** —— 原生中英文混合分词，对中文文档同样友好
- **交互体验** —— 内置 TUI 终端交互界面与 HTTP API 服务，灵活接入各种工作流

**差异化亮点：**

| 特性 | DocIndexForge | 传统全文搜索 | 向量数据库方案 |
|------|:---:|:---:|:---:|
| 零外部依赖 | **Yes** | No | No |
| 无需数据库 | **Yes** | No | No |
| 中英文混合分词 | **Yes** | 部分支持 | 部分支持 |
| 内置 TUI 界面 | **Yes** | No | No |
| 内置 HTTP API | **Yes** | 部分支持 | 部分支持 |
| 索引自动持久化 | **Yes** | No | No |
| 安装复杂度 | **pip install** | 中等 | 高 |

---

### 核心特性

- **多格式文档解析** —— 支持 Markdown、TXT、JSON、CSV、HTML 五种常见文档格式，自动识别文件类型并提取结构化内容
- **多策略索引引擎** —— 内置 **TF-IDF**、**BM25**、**倒排索引** 三种经典索引策略，可根据场景灵活选择
- **智能语义检索** —— 支持 **AND/OR/NOT 布尔查询**、**模糊匹配**、**关键词高亮**、**上下文摘要**，让搜索结果精准且直观
- **文档深度分析** —— 提供 **词频统计**、**文档相似度计算**、**索引健康报告**，全方位洞察文档集合
- **TUI 终端交互界面** —— 内置终端图形界面，无需离开命令行即可完成索引、搜索、分析等全部操作
- **HTTP API 服务** —— 一键启动 RESTful API 服务，方便集成到其他应用或搭建 Web 搜索服务
- **索引持久化** —— 支持 **JSON 导出/导入** 与 **增量更新**，索引自动保存，跨会话无缝衔接
- **中英文混合分词** —— 原生支持中文与英文混合文档的智能分词，无需额外安装分词工具

---

### 快速开始

#### 环境要求

- Python 3.8 或更高版本
- 无需安装任何第三方依赖

#### 安装

```bash
# 方式一：从 PyPI 安装（推荐）
pip install git+https://github.com/gitstq/DocIndexForge.git

# 方式二：从源码安装
git clone https://github.com/gitstq/DocIndexForge.git
cd DocIndexForge
pip install .
```

#### 三步上手

```bash
# 第一步：索引你的文档目录
python -m docindexforge index ./my-docs

# 第二步：搜索关键词
python -m docindexforge search "Python 异步编程"

# 第三步：查看统计信息
python -m docindexforge stats
```

就是这么简单！索引会自动保存到当前目录，下次启动时自动加载。

---

### 详细使用指南

#### 1. 索引文档

```bash
# 索引单个文件
python -m docindexforge index README.md

# 索引整个目录（默认递归）
python -m docindexforge index ./docs

# 索引目录（不递归子目录）
python -m docindexforge index ./docs --no-recursive

# 增量更新（仅处理新增和修改的文件）
python -m docindexforge index ./docs --update
```

#### 2. 搜索文档

```bash
# 基本搜索
python -m docindexforge search "机器学习"

# 指定搜索策略（bm25 / tfidf / boolean）
python -m docindexforge search "深度学习" -s tfidf

# 限制结果数量
python -m docindexforge search "API设计" -n 5

# 布尔查询
python -m docindexforge search "Python AND Web"
python -m docindexforge search "数据库 NOT SQL"
python -m docindexforge search "前端 OR 后端"

# JSON 格式输出（方便脚本处理）
python -m docindexforge search "微服务" --json

# 交互式搜索模式
python -m docindexforge search
```

#### 3. 文档分析

```bash
# 综合分析（词频 + 健康报告）
python -m docindexforge analyze

# 查看词频统计（显示前 30 个高频词）
python -m docindexforge analyze --frequency --top 30

# 查看索引健康报告
python -m docindexforge analyze --health

# 分析单个文件
python -m docindexforge analyze ./docs/api.md
```

#### 4. 索引管理

```bash
# 导出索引到 JSON 文件
python -m docindexforge export my-index.json

# 从 JSON 文件导入索引
python -m docindexforge import my-index.json

# 查看索引统计信息
python -m docindexforge stats
```

#### 5. TUI 交互界面

```bash
# 启动终端图形界面
python -m docindexforge tui
```

在 TUI 界面中，你可以通过键盘完成所有操作：浏览文档、搜索内容、查看分析报告等。

#### 6. HTTP API 服务

```bash
# 启动 API 服务（默认 127.0.0.1:8765）
python -m docindexforge serve

# 指定地址和端口
python -m docindexforge serve --host 0.0.0.0 -p 9000
```

启动后可通过 HTTP 请求进行搜索和查询，方便集成到其他系统。

---

### 设计思路与迭代规划

#### 设计哲学

DocIndexForge 的核心设计理念是 **"轻量但不简陋"**：

1. **零依赖原则** —— 全部基于 Python 标准库实现，降低使用门槛，避免依赖冲突
2. **渐进式复杂度** —— 简单场景一条命令搞定，复杂场景提供丰富的参数和策略选择
3. **数据自主可控** —— 索引以 JSON 格式存储在本地，用户完全掌控自己的数据
4. **多模式接入** —— CLI、TUI、HTTP API 三种模式，覆盖从个人使用到服务集成的各种场景

#### 架构概览

```
DocIndexForge
├── parser.py        # 多格式文档解析器
├── processor.py     # 文本处理与分词
├── indexer.py       # 索引引擎（TF-IDF/BM25/倒排索引）
├── searcher.py      # 智能搜索引擎
├── analyzer.py      # 文档分析引擎
├── tui.py           # TUI 终端交互界面
├── server.py        # HTTP API 服务
├── cli.py           # 命令行接口
└── utils.py         # 工具函数
```

#### 迭代规划

- [x] v1.0 - 核心功能：多格式解析、多策略索引、智能检索、TUI、HTTP API
- [ ] v1.1 - 增强分词：支持自定义词典、停用词过滤优化
- [ ] v1.2 - 更多格式：支持 PDF、DOCX、EPUB 等格式解析
- [ ] v1.3 - 插件体系：支持自定义解析器、索引策略、搜索过滤器
- [ ] v2.0 - 分布式支持：多节点索引同步与分布式检索

---

### 贡献指南

我们欢迎并感谢所有形式的贡献！无论是提交 Bug 报告、功能建议，还是直接提交 Pull Request。

#### 参与步骤

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/my-new-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/my-new-feature`
5. 提交 **Pull Request**

#### 贡献规范

- 代码风格遵循 PEP 8
- 提交信息使用清晰、描述性的语言
- 为新功能编写相应的测试用例
- 确保所有测试通过后再提交 PR

---

### 开源协议

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

```
MIT License

Copyright (c) 2024 DocIndexForge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## English

### Introduction

In the era of information overload, we deal with massive amounts of documents every day -- technical docs, project notes, knowledge bases, log files... Finding the right content quickly has become a universal pain point.

**DocIndexForge** is a lightweight document intelligent indexing and semantic search engine built to solve exactly this problem. It is a pure Python standard library CLI tool with **zero external dependencies** -- ready to use out of the box, no need to set up vector databases or complex environments.

**Core Values:**

- **Minimal Deployment** -- One `pip install` command and you're good to go, no third-party libraries required
- **Multi-Format Support** -- Markdown, TXT, JSON, CSV, HTML -- all common document formats covered
- **Professional-Grade Search** -- Built-in TF-IDF, BM25, and inverted index strategies with boolean queries and fuzzy matching
- **Bilingual Friendly** -- Native Chinese-English mixed tokenization, equally capable with both languages
- **Flexible Interaction** -- Built-in TUI terminal interface and HTTP API service for seamless integration into any workflow

**What Makes Us Different:**

| Feature | DocIndexForge | Traditional Full-Text Search | Vector DB Solutions |
|---------|:---:|:---:|:---:|
| Zero Dependencies | **Yes** | No | No |
| No Database Required | **Yes** | No | No |
| Chinese-English Mixed Tokenization | **Yes** | Partial | Partial |
| Built-in TUI | **Yes** | No | No |
| Built-in HTTP API | **Yes** | Partial | Partial |
| Auto Index Persistence | **Yes** | No | No |
| Setup Complexity | **pip install** | Medium | High |

---

### Key Features

- **Multi-Format Document Parsing** -- Supports Markdown, TXT, JSON, CSV, and HTML with automatic file type detection and structured content extraction
- **Multi-Strategy Indexing Engine** -- Three classic indexing strategies built in: **TF-IDF**, **BM25**, and **Inverted Index**, with flexible strategy selection per use case
- **Intelligent Semantic Search** -- Supports **AND/OR/NOT boolean queries**, **fuzzy matching**, **keyword highlighting**, and **contextual snippets** for precise and intuitive results
- **In-Depth Document Analysis** -- Provides **word frequency statistics**, **document similarity computation**, and **index health reports** for comprehensive insights into your document collection
- **TUI Terminal Interface** -- Built-in terminal graphical interface to perform indexing, searching, and analysis without leaving the command line
- **HTTP API Service** -- One-command launch of a RESTful API server for easy integration with other applications or building web search services
- **Index Persistence** -- Supports **JSON export/import** and **incremental updates** with automatic index saving for seamless cross-session continuity
- **Chinese-English Mixed Tokenization** -- Native support for intelligent tokenization of mixed Chinese and English documents, no additional NLP tools needed

---

### Quick Start

#### Prerequisites

- Python 3.8 or later
- No third-party dependencies required

#### Installation

```bash
# Option 1: Install from GitHub (recommended)
pip install git+https://github.com/gitstq/DocIndexForge.git

# Option 2: Install from source
git clone https://github.com/gitstq/DocIndexForge.git
cd DocIndexForge
pip install .
```

#### Three Steps to Get Started

```bash
# Step 1: Index your document directory
python -m docindexforge index ./my-docs

# Step 2: Search for keywords
python -m docindexforge search "async programming"

# Step 3: View statistics
python -m docindexforge stats
```

It's that simple! The index is automatically saved to the current directory and loaded on the next startup.

---

### Detailed Usage Guide

#### 1. Indexing Documents

```bash
# Index a single file
python -m docindexforge index README.md

# Index an entire directory (recursive by default)
python -m docindexforge index ./docs

# Index a directory without recursion
python -m docindexforge index ./docs --no-recursive

# Incremental update (only process new and modified files)
python -m docindexforge index ./docs --update
```

#### 2. Searching Documents

```bash
# Basic search
python -m docindexforge search "machine learning"

# Specify search strategy (bm25 / tfidf / boolean)
python -m docindexforge search "deep learning" -s tfidf

# Limit the number of results
python -m docindexforge search "API design" -n 5

# Boolean queries
python -m docindexforge search "Python AND Web"
python -m docindexforge search "database NOT SQL"
python -m docindexforge search "frontend OR backend"

# JSON output (for scripting)
python -m docindexforge search "microservices" --json

# Interactive search mode
python -m docindexforge search
```

#### 3. Document Analysis

```bash
# Comprehensive analysis (word frequency + health report)
python -m docindexforge analyze

# Word frequency statistics (top 30 terms)
python -m docindexforge analyze --frequency --top 30

# Index health report
python -m docindexforge analyze --health

# Analyze a single file
python -m docindexforge analyze ./docs/api.md
```

#### 4. Index Management

```bash
# Export index to a JSON file
python -m docindexforge export my-index.json

# Import index from a JSON file
python -m docindexforge import my-index.json

# View index statistics
python -m docindexforge stats
```

#### 5. TUI Interactive Interface

```bash
# Launch the terminal graphical interface
python -m docindexforge tui
```

In the TUI interface, you can perform all operations via keyboard: browse documents, search content, view analysis reports, and more.

#### 6. HTTP API Service

```bash
# Start the API service (default: 127.0.0.1:8765)
python -m docindexforge serve

# Specify host and port
python -m docindexforge serve --host 0.0.0.0 -p 9000
```

Once started, you can send HTTP requests for searching and querying, making it easy to integrate with other systems.

---

### Design Philosophy & Roadmap

#### Design Philosophy

The core design principle of DocIndexForge is **"Lightweight, Not Simplistic"**:

1. **Zero-Dependency Principle** -- Entirely built on the Python standard library to lower the barrier to entry and avoid dependency conflicts
2. **Progressive Complexity** -- Simple scenarios require a single command; complex scenarios offer rich parameters and strategy choices
3. **Data Sovereignty** -- Indexes are stored locally in JSON format; users have full control over their data
4. **Multi-Mode Access** -- CLI, TUI, and HTTP API modes cover everything from personal use to service integration

#### Architecture Overview

```
DocIndexForge
├── parser.py        # Multi-format document parser
├── processor.py     # Text processing & tokenization
├── indexer.py       # Index engine (TF-IDF/BM25/Inverted Index)
├── searcher.py      # Intelligent search engine
├── analyzer.py      # Document analysis engine
├── tui.py           # TUI terminal interface
├── server.py        # HTTP API service
├── cli.py           # Command-line interface
└── utils.py         # Utility functions
```

#### Roadmap

- [x] v1.0 - Core features: multi-format parsing, multi-strategy indexing, intelligent search, TUI, HTTP API
- [ ] v1.1 - Enhanced tokenization: custom dictionaries, optimized stop-word filtering
- [ ] v1.2 - More formats: PDF, DOCX, EPUB support
- [ ] v1.3 - Plugin system: custom parsers, indexing strategies, search filters
- [ ] v2.0 - Distributed support: multi-node index sync and distributed search

---

### Contributing

We welcome and appreciate contributions of all forms -- whether it's submitting bug reports, feature requests, or pull requests.

#### How to Contribute

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a **Pull Request**

#### Contribution Guidelines

- Follow PEP 8 code style
- Use clear, descriptive commit messages
- Write test cases for new features
- Ensure all tests pass before submitting a PR

---

### License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

```
MIT License

Copyright (c) 2024 DocIndexForge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

<div align="center">

**Made with passion by the DocIndexForge team**

</div>
