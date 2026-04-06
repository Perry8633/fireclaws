# 网页爬虫 + LLM 分析工具

基于 Python 的桌面应用程序，用于爬取网页内容并使用大语言模型进行分析。

## 主要功能

### 1. 智能爬虫
- 支持多个起始 URL（最多 5 个）
- 可配置爬取深度（1-3 层）
- 自动识别并下载 PDF 文档
- HTML 转 Markdown（参考 Firecrawl 思路）

### 2. 搜索引擎集成
- **DuckDuckGo (DDGS)**: 无需 API Key，免费使用
- **Brave Search**: 需 API Key，每月 2000 次免费
- **Tavily**: 专为 AI 优化，1000 次/月免费

### 3. LLM 分析
- OpenAI 兼容接口，支持任意 BASE_URL
- 支持自定义提示词
- 支持流式输出
- 可主动搜索网络补充信息

### 4. 其他特性
- 密码保护配置（PBKDF2 + Fernet 加密）
- 爬虫和 LLM 独立代理配置（HTTP/HTTPS/SOCKS5）
- 飞书文档发送接口（预留）
- HTML/Markdown 导出

## 技术栈

| 功能 | 方案 |
|------|------|
| GUI | Tkinter（内置） |
| 爬虫 | requests + BeautifulSoup |
| PDF | PyMuPDF / pdfplumber |
| LLM | openai 库 |
| 搜索引擎 | DuckDuckGo / Brave Search / Tavily |
| 代理 | httpx |
| 加密 | cryptography |
| 日志 | loguru |
| 打包 | PyInstaller |

## 项目结构

```
fireclaws/
├── main.py                  # 程序入口
├── requirements.txt         # 依赖
├── config/
│   ├── settings.py         # 配置模型
│   └── encryption.py       # 密码加密
├── crawler/
│   ├── base_crawler.py     # 爬虫核心
│   ├── markdown_converter.py# HTML→Markdown
│   ├── pdf_downloader.py   # PDF下载
│   └── search_engine.py    # 搜索引擎
├── llm/
│   ├── client.py           # OpenAI客户端
│   └── analyzer.py         # LLM分析
├── gui/
│   ├── main_window.py      # 主窗口
│   └── settings_dialog.py  # 设置弹窗
├── feishu/                 # 飞书预留接口
└── utils/                  # 工具函数
```

## 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- requests, beautifulsoup4, lxml
- PyMuPDF, pdfplumber
- openai
- duckduckgo-search
- httpx, PySocks
- cryptography, pydantic, pydantic-settings
- loguru, tqdm

### 2. 运行

```bash
python main.py
```

首次运行需要设置管理员密码。

## 使用方法

### 基本流程

1. **输入任务描述**：说明你想了解什么内容
2. **输入关键词**（可选）：用于搜索引擎发现相关 URL
3. **输入 URLs**（可选）：直接指定要爬取的页面
4. **选择搜索引擎**：DuckDuckGo（免费）或 Tavily/Brave（需 API Key）
5. **点击"开始任务"**：程序将自动执行：
   - 搜索引擎搜索关键词发现 URLs
   - 爬虫爬取页面内容和 PDF
   - LLM 分析并生成报告

### 设置

点击菜单 `设置 → 打开设置`，可配置：

- **大模型**：Provider 预设、Base URL、API Key、Model、提示词
- **搜索引擎**：选择引擎、API Key
- **爬虫代理**：独立配置爬虫使用的代理
- **LLM 代理**：独立配置 LLM API 使用的代理
- **飞书**：预留接口

## 配置示例

### LLM 配置（支持 OpenAI 兼容接口）

```json
{
  "provider": "custom",
  "base_url": "http://127.0.0.1:4000/v1",
  "api_key": "your-api-key",
  "model": "deepseek-chat"
}
```

支持：
- 本地模型（如 ollama）
- 中转 API（如 One API）
- 各厂商 API（DeepSeek、Qwen、MiniMax 等）

### 搜索配置

```json
{
  "provider": "ddgs",
  "api_key": ""
}
```

或使用 Tavily：
```json
{
  "provider": "tavily",
  "api_key": "tvly-xxx"
}
```

## 代理配置

支持 HTTP、HTTPS、SOCKS5 协议，可分别为爬虫和 LLM 配置不同代理。

```
代理类型: HTTP / HTTPS / SOCKS5
地址: proxy.example.com
端口: 8080
用户名: （可选）
密码: （可选）
```

## 导出

分析完成后可导出：
- **HTML**：带样式的可视化页面
- **Markdown**：纯文本格式

## 飞书集成（预留）

预留了飞书文档发送接口，可配置：
- CLI 路径
- App ID
- App Secret

## 注意事项

1. 请遵守网站的 robots.txt 和使用条款
2. 设置合理的爬取间隔，避免对目标网站造成压力
3. 妥善保管 API Key 和代理凭证
4. 定期备份加密后的配置文件

## 打包

使用 PyInstaller 打包为单文件 exe：

```bash
pyinstaller build.spec
```

## License

MIT
