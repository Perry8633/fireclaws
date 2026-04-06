import requests
import time
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from config.settings import ProxyConfig
from utils.proxy_manager import ProxyManager
from .markdown_converter import MarkdownConverter


@dataclass
class CrawlResult:
    """爬取结果"""
    url: str
    title: str = ""
    markdown: str = ""
    children: List['CrawlResult'] = field(default_factory=list)
    error: str = ""


class BaseCrawler:
    """基础爬虫类"""

    def __init__(
        self,
        proxy: Optional[ProxyConfig] = None,
        delay: float = 1.0,
        timeout: int = 30,
        max_depth: int = 2,
        max_pages_per_depth: int = 20
    ):
        self.proxy = proxy
        self.delay = delay
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_pages_per_depth = max_pages_per_depth
        self.markdown_converter = MarkdownConverter()

    def _get_proxy(self):
        return ProxyManager.get_requests_proxy(self.proxy) if self.proxy else None

    def _get_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def fetch(self, url: str) -> Optional[str]:
        """获取页面HTML"""
        try:
            response = requests.get(
                url,
                proxies=self._get_proxy(),
                headers=self._get_headers(),
                timeout=self.timeout,
                allow_redirects=True,
                verify=False  # 代理环境下禁用SSL验证
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except Exception as e:
            print(f"获取页面失败 {url}: {e}")
            return None

    def parse(self, html: str) -> Optional[BeautifulSoup]:
        """解析HTML"""
        if not html:
            return None
        try:
            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            print(f"解析HTML失败: {e}")
            return None

    def extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题"""
        # 尝试多种方式获取标题
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content', '').strip()

        return ""

    def extract_content(self, soup: BeautifulSoup) -> str:
        """提取正文内容"""
        # 尝试查找主要内容区域
        content_tags = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', class_=re.compile(r'content|article|post|entry', re.I)),
            soup.find('div', id=re.compile(r'content|article|post|entry', re.I)),
        ]

        for tag in content_tags:
            if tag:
                return str(tag)

        # 如果没找到，返回body
        if soup.body:
            return str(soup.body)

        return str(soup)

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取同域名链接"""
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']

            # 跳过锚点、javascript、mailto等
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue

            # 转换为绝对URL
            abs_url = urljoin(base_url, href)
            parsed = urlparse(abs_url)

            # 只保留同域名链接
            if parsed.netloc == base_domain:
                # 移除fragment
                clean_url = parsed._replace(fragment='').geturl()
                links.add(clean_url)

        return list(links)

    def convert_to_markdown(self, html: str) -> str:
        """HTML转Markdown"""
        return self.markdown_converter.convert(html)

    def crawl_url(self, url: str, depth: int = 0) -> CrawlResult:
        """爬取单个URL"""
        result = CrawlResult(url=url)

        # 获取页面
        html = self.fetch(url)
        if not html:
            result.error = "获取页面失败"
            return result

        # 解析
        soup = self.parse(html)
        if not soup:
            result.error = "解析页面失败"
            return result

        # 提取信息
        result.title = self.extract_title(soup)
        content_html = self.extract_content(soup)
        result.markdown = self.convert_to_markdown(content_html)

        # 递归爬取子链接（如果深度未达上限）
        if depth < self.max_depth:
            child_links = self.extract_links(soup, url)[:self.max_pages_per_depth]
            for child_url in child_links:
                time.sleep(self.delay)  # 礼貌爬取
                child_result = self.crawl_url(child_url, depth + 1)
                result.children.append(child_result)

        return result

    def crawl(self, urls: List[str], progress_callback=None) -> List[CrawlResult]:
        """爬取多个URL"""
        results = []
        total = len(urls)
        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(i + 1, total, url)
            results.append(self.crawl_url(url))
            time.sleep(self.delay)
        return results

    def flatten_results(self, results: List[CrawlResult]) -> List[CrawlResult]:
        """展开所有结果（包含子页面）"""
        flattened = []
        for result in results:
            flattened.append(result)
            if result.children:
                flattened.extend(self.flatten_results(result.children))
        return flattened
