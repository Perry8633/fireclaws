# 网页爬虫 + LLM 分析工具 - 软件规格说明书

## 1. 项目概述

开发一个 Windows 桌面应用，用于：
- 用户输入关键词（用于搜索引擎发现URLs）
- 用户输入URLs（直接爬取指定页面）
- 爬虫爬取URLs内容和PDF
- LLM分析内容，并可主动搜索网络补充信息
- LLM输出结构化分析报告（标题+概述+内容）
- Tkinter GUI + PyInstaller 单exe打包

## 2. 技术栈

| 功能 | 方案 |
|------|------|
| GUI | Tkinter（内置） |
| 爬虫 | requests + BeautifulSoup |
| PDF | PyMuPDF / pdfplumber |
| LLM | openai 库 |
| 搜索引擎 | DuckDuckGo (DDGS) / Brave Search / Tavily |
| 代理 | httpx（支持SOCKS5） |
| 加密 | cryptography (Fernet) |
| 日志 | loguru |
| 打包 | PyInstaller --onefile |

## 3. 项目结构

```
crawler_llm_app/
├── main.py                  # 程序入口
├── config/
│   ├── settings.py         # Pydantic 配置模型
│   ├── encryption.py       # PBKDF2 + Fernet 加密
│   └── presets.py          # LLM 预设（minimax/deepseek/QWEN等）
├── gui/
│   ├── main_window.py      # 主窗口
│   ├── settings_dialog.py   # 设置弹窗（带密码保护）
│   └── components/         # 进度条、结果面板等
├── crawler/
│   ├── base_crawler.py     # 基础爬虫类
│   ├── keyword_filter.py   # 关键词触发逻辑
│   ├── pdf_downloader.py    # PDF 下载保存
│   ├── markdown_converter.py# HTML→Markdown（参考Firecrawl）
│   └── search_engine.py    # 搜索引擎集成（DDGS/Brave/Tavily）
├── llm/
│   ├── analyzer.py         # LLM分析+流式输出
│   └── client.py           # OpenAI兼容客户端
├── feishu/
│   └── __init__.py         # 飞书集成（预留接口）
├── utils/
│   ├── proxy_manager.py    # 代理管理
│   ├── logger.py           # 日志配置
│   └── helpers.py
├── data/                   # 运行时文件夹（自动创建）
│   ├── configs/            # 加密配置
│   ├── downloads/          # PDF保存
│   └── logs/
├── requirements.txt
├── build.spec             # PyInstaller配置
└── README.md
```

## 4. 核心模块设计

### 4.1 配置模型 (config/settings.py)

```python
class ProxyConfig(BaseModel):
    enabled: bool = False
    protocol: str = "http"  # http / https / socks5
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

class LLMConfig(BaseModel):
    provider: str = "custom"  # minimax / deepseek / qwen / custom
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4"
    temperature: float = 0.7
    system_prompt: str = ""

class SearchConfig(BaseModel):
    provider: str = "ddgs"  # ddgs / brave / tavily
    api_key: str = ""  # Brave/Tavily需要，DDGS不需要

class FeishuConfig(BaseModel):
    enabled: bool = False
    cli_path: str = ""
    app_id: str = ""
    app_secret: str = ""

class AppConfig(BaseModel):
    llm_proxy: ProxyConfig = ProxyConfig()
    search_proxy: ProxyConfig = ProxyConfig()
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    feishu: FeishuConfig = FeishuConfig()
    password_hash: str = ""  # PBKDF2 hash
```

### 4.2 加密模块 (config/encryption.py)

- 首次设置密码 → PBKDF2 生成 hash 存储
- 登录时验证 → 正确则用密码生成 Fernet key 加密配置
- 配置文件：`data/configs/config.json`（加密后）

### 4.3 整体工作流程 (Agent Loop)

```
用户输入关键词（用于搜索引擎发现URLs）
用户输入URLs（直接爬取指定页面）
    ↓
合并所有URLs
    ↓
爬虫爬取URLs内容 + PDF下载
    ↓
LLM分析内容（可主动调用搜索引擎补充信息）
    ↓
LLM输出结构化报告（标题+概述+内容）
    ↓
导出HTML / Markdown / 发送飞书
```

### 4.4 爬虫流程 (crawler/base_crawler.py)

```
输入: urls[], depth
输出: [{url, markdown, pdfs[]}]

1. fetch(url) → requests.get + proxy
2. parse(html) → BeautifulSoup
3. extract_text() → 清洗HTML获取正文
4. to_markdown() → 转Markdown（参考Firecrawl）
5. extract_links() → 过滤同域名链接
6. download_pdfs() → 检测PDF链接并下载
7. 递归 depth 层
```

### 4.5 Markdown转换 (crawler/markdown_converter.py)

参考Firecrawl思路：
- 移除script/style等干扰标签
- 保留语义结构（h1-h6, p, ul, ol, blockquote）
- 提取pre/code块内容
- 转换img为markdown格式
- 清理空白字符

### 4.6 LLM分析 + 主动搜索 (llm/analyzer.py)

LLM具有搜索能力，可在分析过程中主动搜索网络补充信息：

```python
class LLMAgent:
    def __init__(self, config: LLMConfig, search_engine: SearchEngine):
        self.llm = OpenAIClient(config)
        self.search = search_engine

    def analyze_with_search(self, context: str, user_query: str):
        """
        LLM分析 + 主动搜索的Agent循环：
        1. LLM分析当前内容
        2. 如果信息不足，LLM决定需要搜索什么
        3. 调用搜索引擎获取更多信息
        4. 合并结果再次分析
        5. 重复直到足够，输出最终报告
        """
```

### 4.7 LLM输出格式

最终报告包含三部分结构：
- **标题** (`title`)：简短概括
- **概述** (`summary`)：关键发现
- **内容** (`content`)：详细分析（可包含引用来源）

### 4.8 导出格式

| 格式 | 说明 |
|------|------|
| HTML | 带样式的可视化页面（标题+概述+内容），可直接浏览器打开 |
| Markdown | 纯文本格式，便于编辑和复制 |

### 4.9 飞书集成接口 (feishu/)

```python
class FeishuConfig(BaseModel):
    enabled: bool = False
    cli_path: str = ""  # 飞书CLI可执行文件路径
    app_id: str = ""
    app_secret: str = ""

def send_to_feishu(content: str, config: FeishuConfig):
    # 调用飞书CLI创建文档/发送消息
    # 预留接口，暂不实现具体逻辑
```

### 4.10 搜索引擎集成 (crawler/search_engine.py)

支持三种搜索引擎，可通过下拉选择：

| 引擎 | API Key | 免费额度 | 说明 |
|------|---------|---------|------|
| DuckDuckGo (DDGS) | 不需要 | 无限制 | 100%免费开源 |
| Brave Search | 需要 | 2000次/月 | 隐私保护强 |
| Tavily | 需要 | 1000次/月 | 专为AI优化 |

```python
class SearchEngine:
    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """返回 [{title, url, snippet}, ...]"""
        if self.provider == "ddgs":
            return self._ddgs_search(query, max_results)
        elif self.provider == "brave":
            return self._brave_search(query, max_results)
        elif self.provider == "tavily":
            return self._tavily_search(query, max_results)
```

## 5. GUI 设计

### 5.1 主窗口布局

```
┌─────────────────────────────────────────────────────┐
│ 菜单: 文件 | 设置 | 帮助                              │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │ 任务配置面板      │  │ 结果显示区               │  │
│  │                 │  │                          │  │
│  │ 任务描述输入框    │  │ [Tab] 爬取内容 | LLM分析 │  │
│  │ (你想了解什么?)  │  │                          │  │
│  │ ─────────────── │  │ Markdown预览/流式输出    │  │
│  │ 关键词[输入框]  │  │                          │  │
│  │ [标签1][标签2]✕ │  │                          │  │
│  │ ─────────────── │  │                          │  │
│  │ URLs输入框(多行)│  │                          │  │
│  │ ─────────────── │  │                          │  │
│  │ [搜索引擎▼]     │  │                          │  │
│  │ [开始任务]      │  │                          │  │
│  │ 进度条          │  │                          │  │
│  │ 状态: 搜索中... │  │                          │  │
│  │ [导出HTML][导出MD][发送飞书]                    │  │
│  └─────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 5.2 设置弹窗（需要登录）

```
┌─────────────────────────────────────┐
│  🔒 请输入管理员密码                 │
│  ┌─────────────────────────────┐    │
│  │ ************************** │    │
│  └─────────────────────────────┘    │
│           [登录] [取消]              │
└─────────────────────────────────────┘

登录后Tab页：
┌────────────────────────────────────────────────────────────┐
│ [通用] [大模型] [搜索引擎] [爬虫代理] [LLM代理] [飞书]       │
├────────────────────────────────────────────────────────────┤
│ 大模型：                                                   │
│   Provider预设、Base URL、API Key、Model、                   │
│   Temperature、自定义System Prompt                           │
│                                                             │
│ 搜索引擎：                                                 │
│   引擎[DuckDuckGo▼]  API Key（仅Brave/Tavily需要）          │
│                                                             │
│ 爬虫代理 / LLM代理：                                       │
│   □ 启用  协议[HTTP▼]  地址   端口                         │
│   用户名     密码                                           │
│                                                             │
│ 飞书（预留）：                                              │
│   □ 启用  CLI路径  App ID  App Secret                       │
└────────────────────────────────────────────────────────────┘
```

### 5.3 关键词输入 - 标签输入框

- 输入框输入关键词 → 按 Enter 添加为标签
- 每个标签右上角有 ✕ 按钮可删除
- 标签横向排列，数量不限

## 6. 实施步骤

### Phase 1: 项目骨架
1. 创建目录结构
2. 配置 `requirements.txt`
3. 实现 `config/settings.py`（Pydantic模型）
4. 实现 `config/encryption.py`（密码加密）
5. 实现 `utils/logger.py`

### Phase 2: 爬虫核心
6. 实现 `crawler/markdown_converter.py`
7. 实现 `crawler/base_crawler.py`
8. 实现 `crawler/pdf_downloader.py`
9. 实现 `crawler/search_engine.py`
10. 实现 `utils/proxy_manager.py`

### Phase 3: LLM模块
11. 实现 `llm/client.py`
12. 实现 `llm/analyzer.py`

### Phase 4: GUI
13. 实现 `gui/components/`（进度条、面板）
14. 实现 `gui/settings_dialog.py`
15. 实现 `gui/main_window.py`
16. 实现 `main.py`

### Phase 5: 打包
17. 编写 `build.spec`
18. 测试打包

## 7. 验证方式

1. `pip install -r requirements.txt`
2. 运行 `python main.py` 启动GUI
3. 测试密码设置流程
4. 输入任务描述，选择搜索引擎，测试"开始任务"
5. 观察搜索引擎 → 爬取 → LLM分析的完整流程
6. 验证LLM主动搜索补充信息功能
7. 测试导出HTML/Markdown
8. 测试代理开关
9. `pyinstaller build.spec` 打包exe

## 8. 依赖清单

```
# 核心依赖
requests>=2.28.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# PDF处理
PyMuPDF>=1.23.0
pdfplumber>=0.10.0

# LLM
openai>=1.0.0

# 搜索引擎
duckduckgo-search>=4.0.0

# 代理
httpx>=0.25.0
PySocks>=1.7.0

# 配置与安全
cryptography>=41.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# 日志和进度
loguru>=0.7.0
tqdm>=4.65.0
```

## 9. 配置文件格式

配置文件加密存储在 `data/configs/config.json`，包含：

- LLM 配置（Provider、Base URL、API Key、Model、Temperature、System Prompt）
- 搜索引擎配置（Provider、API Key）
- 代理配置（爬虫代理、LLM代理独立配置）
- 飞书配置（预留）
- 密码哈希
