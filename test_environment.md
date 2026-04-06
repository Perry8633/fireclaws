# 测试环境配置指南

## 1. Docker + Playwright 测试环境

### 1.1 Dockerfile

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Playwright 和 Chrome
RUN pip install playwright \
    && playwright install chromium \
    && playwright install-deps

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install -r requirements.txt

# 默认命令
CMD ["python", "main.py"]
```

### 1.2 docker-compose.yml

```yaml
version: '3.8'

services:
  crawler-app:
    build: .
    container_name: fireclaws-crawler
    volumes:
      - ./data:/app/data
    environment:
      - HTTP_PROXY=http://proxy:8080
      - HTTPS_PROXY=http://proxy:8080
      - NO_PROXY=localhost,127.0.0.1
    networks:
      - crawler-network

  proxy:
    image: mitmproxy/mitmproxy:latest
    container_name: fireclaws-proxy
    ports:
      - "8080:8080"
    networks:
      - crawler-network

networks:
  crawler-network:
    driver: bridge
```

---

## 2. Playwright 爬虫配置（模拟 Windows 浏览器）

### 2.1 安装依赖

```bash
pip install playwright
playwright install chromium
playwright install-deps
```

### 2.2 Playwright 爬虫示例

```python
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import hashlib
import re


class PlaywrightCrawler:
    """使用 Playwright 的爬虫，模拟 Windows 浏览器"""

    def __init__(
        self,
        proxy: str = None,
        timeout: int = 30000,
        delay: float = 1.0
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.delay = delay

    def _get_browser_context(self, playwright):
        """获取浏览器上下文"""
        return {
            "proxy": {"server": self.proxy} if self.proxy else None,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }

    def crawl(self, url: str) -> dict:
        """爬取单个URL"""
        result = {
            "url": url,
            "title": "",
            "content": "",
            "markdown": "",
            "error": ""
        }

        with sync_playwright() as p:
            try:
                # 启动 Chromium
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox"
                    ]
                )

                context = browser.new_context(**self._get_browser_context(p))
                page = context.new_page()

                # 设置默认超时
                page.set_default_timeout(self.timeout)

                # 访问页面
                page.goto(url, wait_until="networkidle")

                # 等待内容加载
                page.wait_for_load_state("domcontentloaded")

                # 获取标题
                result["title"] = page.title()

                # 获取页面内容
                content_html = page.content()

                # 转换为BeautifulSoup清洗
                soup = BeautifulSoup(content_html, 'lxml')

                # 提取正文
                result["content"] = self._extract_content(soup)

                # 转换为Markdown
                result["markdown"] = self._to_markdown(result["content"])

                # 关闭浏览器
                context.close()
                browser.close()

            except Exception as e:
                result["error"] = str(e)

        return result

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取正文内容"""
        # 移除script、style等
        for tag in soup.find_all(['script', 'style', 'noscript']):
            tag.decompose()

        # 查找主要内容区域
        main_tags = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', class_=re.compile(r'content|article|post|entry', re.I)),
        ]

        for tag in main_tags:
            if tag:
                return tag.get_text(separator='\n', strip=True)

        if soup.body:
            return soup.body.get_text(separator='\n', strip=True)

        return soup.get_text(separator='\n', strip=True)

    def _to_markdown(self, text: str) -> str:
        """简单文本转Markdown"""
        import re

        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 标题处理（简单的）
        lines = text.split('\n')
        markdown_lines = []

        for line in lines:
            stripped = line.strip()
            if len(stripped) > 0:
                # 如果行以大写字母开头且长度适中，可能是标题
                if (stripped[0].isupper() and 20 <= len(stripped) <= 100
                    and not stripped.endswith(('.', '!', '?', ':'))):
                    markdown_lines.append(f"## {stripped}")
                else:
                    markdown_lines.append(stripped)

        return '\n\n'.join(markdown_lines)


def test_crawl():
    """测试爬虫"""
    import os

    # 代理配置（http:// 不要 https://）
    proxy = os.getenv("HTTP_PROXY") or None

    crawler = PlaywrightCrawler(
        proxy=proxy,
        timeout=30000,
        delay=1.0
    )

    # 测试URL
    urls = [
        "https://www.federalregister.gov/agencies/industry-and-security-bureau",
        "https://ofac.treasury.gov/recent-actions",
    ]

    for url in urls:
        print(f"\n{'='*60}")
        print(f"爬取: {url}")
        print('='*60)

        result = crawler.crawl(url)

        if result["error"]:
            print(f"错误: {result['error']}")
        else:
            print(f"标题: {result['title']}")
            print(f"内容长度: {len(result['content'])} 字符")
            print(f"Markdown预览:\n{result['markdown'][:500]}...")


if __name__ == "__main__":
    test_crawl()
```

---

## 3. requirements.txt（测试环境）

```txt
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

# 代理支持
httpx>=0.25.0
PySocks>=1.7.0

# 配置与安全
cryptography>=41.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# 日志和进度
loguru>=0.7.0
tqdm>=4.65.0

# 定时任务
croniter>=4.0.0

# Playwright（测试用）
playwright>=1.40.0
```

---

## 4. 代理配置注意

**重要**：代理必须使用 `http://` 而不是 `https://`

### 4.1 正确的代理格式

```python
# 正确
proxy = "http://username:password@proxy.example.com:8080"
proxy = "http://proxy.example.com:8080"

# 错误
proxy = "https://username:password@proxy.example.com:8080"
proxy = "https://proxy.example.com:8080"
```

### 4.2 代理配置类

```python
class ProxyConfig(BaseModel):
    enabled: bool = False
    protocol: str = "http"  # 固定为 http，不要用 https
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    def to_proxy_url(self) -> str:
        """转换为代理URL"""
        if not self.enabled or not self.host:
            return None

        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"

        # 固定使用 http://
        return f"http://{auth}{self.host}:{self.port}"
```

---

## 5. 一条龙测试脚本

```bash
#!/bin/bash
# test_crawler.sh - 爬虫一条龙测试

set -e

echo "=========================================="
echo "开始爬虫测试"
echo "=========================================="

# 启动Docker环境（可选）
# docker-compose up -d

# 安装依赖
pip install -r requirements.txt

# 运行Playwright测试
python test_playwright_crawler.py

# 运行普通爬虫测试
python test_crawler.py

# 运行完整流程测试
python test_full_flow.py

echo "=========================================="
echo "测试完成"
echo "=========================================="
```

---

## 6. 完整流程测试脚本

```python
"""
完整流程测试：爬虫 → 文本清洗 → LLM生成报告
"""

from playwright_crawler import PlaywrightCrawler
from llm.analyzer import LLMAgent
from crawler.search_engine import SearchEngine
from config.settings import LLMConfig, SearchConfig
import json


def full_flow_test():
    """完整流程测试"""

    # 1. 爬虫配置
    proxy = "http://proxy.example.com:8080"  # http:// 不是 https://

    crawler = PlaywrightCrawler(
        proxy=proxy,
        timeout=30000
    )

    # 2. 目标URLs
    urls = [
        "https://www.federalregister.gov/agencies/industry-and-security-bureau",
        "https://ofac.treasury.gov/recent-actions",
    ]

    # 3. 爬取内容
    print("步骤1: 爬取网页...")
    all_content = []

    for url in urls:
        result = crawler.crawl(url)
        if not result["error"]:
            all_content.append(f"## {result['title']}\n\n{result['markdown']}")
            print(f"  ✓ {url}")

    # 4. 合并内容
    combined = "\n\n---\n\n".join(all_content)

    # 5. LLM分析
    print("\n步骤2: LLM分析...")

    llm_config = LLMConfig(
        base_url="http://127.0.0.1:4000/v1",
        api_key="sk-test",
        model="deepseek-chat"
    )

    search_config = SearchConfig(provider="ddgs")

    llm_agent = LLMAgent(
        llm_config=llm_config,
        search_engine=SearchEngine(config=search_config)
    )

    # 6. 生成报告
    print("\n步骤3: 生成报告...")

    user_query = "分析这些制裁名单的最新更新，提取关键信息"

    for chunk in llm_agent.analyze(
        context=combined,
        user_query=user_query
    ):
        print(chunk, end="", flush=True)

    # 7. 导出
    print("\n\n步骤4: 导出报告...")

    report = {
        "title": "制裁名单分析报告",
        "sources": urls,
        "content": combined,
        "analysis": ""  # LLM输出
    }

    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("  ✓ 已导出到 report.json")


if __name__ == "__main__":
    full_flow_test()
```

---

## 7. 快速启动命令

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器
playwright install chromium

# 3. 运行测试
python test_playwright_crawler.py

# 4. 使用 Docker
docker-compose up --build
```
