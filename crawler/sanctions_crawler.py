"""
OFAC/BIS 制裁清单爬虫
专门用于爬取美国OFAC和BIS制裁清单更新
"""
import re
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
import requests
from config.settings import ProxyConfig, SanctionsCrawlResult
from crawler.markdown_converter import MarkdownConverter


class SanctionsCrawler:
    """OFAC/BIS 制裁清单爬虫"""

    def __init__(self, proxy: Optional[ProxyConfig] = None, timeout: int = 60):
        self.proxy = proxy
        self.timeout = timeout
        self.converter = MarkdownConverter()

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        }

    def _get_proxy(self) -> Optional[dict]:
        """获取代理配置"""
        if not self.proxy or not self.proxy.enabled:
            return None
        return {
            'http': f"http://{self.proxy.host}:{self.proxy.port}",
            'https': f"http://{self.proxy.host}:{self.proxy.port}",
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
                verify=False
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except Exception as e:
            print(f"获取页面失败 {url}: {e}")
            return None

    def crawl_ofac(self, keywords: list[str], date_start: str = "", date_end: str = "") -> list[SanctionsCrawlResult]:
        """
        爬取OFAC制裁清单

        Args:
            keywords: 关键词列表
            date_start: 开始日期 YYYY-MM-DD
            date_end: 结束日期 YYYY-MM-DD

        Returns:
            爬取结果列表
        """
        results = []
        base_url = "https://ofac.treasury.gov"

        # 获取主页面
        html = self.fetch("https://ofac.treasury.gov/recent-actions/sanctions-list-updates")
        if not html:
            return results

        soup = BeautifulSoup(html, 'lxml')

        # 查找所有日期链接
        date_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # 匹配 /recent-actions/YYYYMMDD 格式
            match = re.search(r'/recent-actions/(\d{8})', href)
            if match:
                date_str = match.group(1)
                date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                # 日期过滤
                if date_start and date_formatted < date_start:
                    continue
                if date_end and date_formatted > date_end:
                    continue

                date_links.append({
                    'url': base_url + href if href.startswith('/') else href,
                    'date': date_formatted,
                    'title': text
                })

        # 去重
        seen = set()
        unique_links = []
        for item in date_links:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique_links.append(item)

        # 爬取每个日期页面
        for item in unique_links[:20]:  # 限制最多20个
            detail_html = self.fetch(item['url'])
            if not detail_html:
                continue

            detail_soup = BeautifulSoup(detail_html, 'lxml')

            # 获取页面文本
            content = detail_soup.get_text(separator=' ', strip=True)

            # 关键词匹配
            matched = []
            content_lower = content.lower()
            for kw in keywords:
                if kw.lower() in content_lower:
                    matched.append(kw)

            has_china = len(matched) > 0

            # 提取实体名称（简化版）
            entities = self._extract_entities(detail_soup)

            result = SanctionsCrawlResult(
                success=True,
                date=item['date'],
                content=content[:5000],  # 限制内容长度
                url=item['url'],
                source="OFAC",
                title=item['title'],
                entities=entities,
                has_china=has_china,
                matched_keywords=matched
            )
            results.append(result)

        return results

    def crawl_bis(self, keywords: list[str], date_start: str = "", date_end: str = "") -> list[SanctionsCrawlResult]:
        """
        爬取BIS实体清单 - 使用 Playwright 2层爬取

        Args:
            keywords: 关键词列表
            date_start: 开始日期 YYYY-MM-DD
            date_end: 结束日期 YYYY-MM-DD

        Returns:
            爬取结果列表
        """
        import asyncio
        try:
            return asyncio.run(self._crawl_bis_async(keywords, date_start, date_end))
        except RuntimeError:
            # 如果已经在事件循环中，使用同步版本
            return []

    async def _crawl_bis_async(self, keywords: list[str], date_start: str = "", date_end: str = "") -> list[SanctionsCrawlResult]:
        """
        异步爬取BIS实体清单 - 2层爬取

        第1层: 日期页面 -> 查找 "Industry and Security Bureau" 后的 Permalink
        第2层: 文档详情页 -> 提取内容
        """
        from datetime import datetime, timedelta

        results = []
        base_url = "https://www.federalregister.gov"

        # 解析日期范围
        if date_start:
            start_dt = datetime.strptime(date_start, "%Y-%m-%d")
        else:
            start_dt = datetime.now() - timedelta(days=30)

        if date_end:
            end_dt = datetime.strptime(date_end, "%Y-%m-%d")
        else:
            end_dt = datetime.now()

        # 生成日期范围内的所有日期
        dates = []
        current_dt = start_dt
        while current_dt <= end_dt:
            dates.append(current_dt.strftime("%Y/%m/%d"))
            current_dt += timedelta(days=1)

        print(f"BIS: 遍历 {len(dates)} 个日期")

        # 第1层: 遍历每个日期页面
        for date_str in dates:
            date_url = f"{base_url}/documents/{date_str}/"
            print(f"BIS: 访问日期页面: {date_str}")

            html = await self.fetch_with_playwright(date_url, wait_time=3)
            if not html:
                continue

            soup = BeautifulSoup(html, 'lxml')
            body = soup.find('body')
            if not body:
                continue

            # 查找 "Industry and Security Bureau" 文本
            found_bis = False
            permalink_url = None
            permalink_title = ""

            # 遍历所有元素，查找 BIS 标题后的 Permalink
            for element in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'div']):
                text = element.get_text(strip=True)

                if 'Industry and Security Bureau' in text or 'INDUSTRY AND SECURITY BUREAU' in text.upper():
                    found_bis = True
                    # 查找下一个链接元素
                    next_link = element.find_next('a', href=True)
                    if next_link:
                        href = next_link.get('href', '')
                        link_text = next_link.get_text(strip=True)
                        # 检查是否是 Permalink
                        if 'permalink' in href.lower() or 'Permalink' in link_text:
                            permalink_url = href if href.startswith('http') else base_url + href
                            permalink_title = link_text
                            break

                    # 也可能在同一元素内找到多个链接
                    links = element.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if 'documents' in href or 'permalink' in href.lower():
                            permalink_url = href if href.startswith('http') else base_url + href
                            permalink_title = link.get_text(strip=True)
                            break

                    if permalink_url:
                        break

                # 如果已找到 BIS，继续找下一个 Permalink
                if found_bis and not permalink_url:
                    next_link = element.find_next('a', href=True)
                    if next_link:
                        href = next_link.get('href', '')
                        link_text = next_link.get_text(strip=True)
                        # Permalink 通常是相对路径
                        if 'documents/' in href or 'permalink' in href.lower():
                            permalink_url = base_url + href if href.startswith('/') else href
                            permalink_title = link_text or "BIS Document"
                            break

            # 第2层: 访问文档详情页
            if permalink_url:
                print(f"BIS: 找到文档: {permalink_title[:40]}")
                doc_html = await self.fetch_with_playwright(permalink_url, wait_time=3)
                if doc_html:
                    doc_content = self.extract_text_from_html(doc_html)

                    # 关键词匹配
                    matched = []
                    content_lower = doc_content.lower()
                    for kw in keywords:
                        if kw.lower() in content_lower:
                            matched.append(kw)

                    has_china = len(matched) > 0

                    # 提取实体
                    entities = self._extract_entities_from_text(doc_content)

                    result = SanctionsCrawlResult(
                        success=True,
                        date=date_str.replace('/', '-'),
                        content=doc_content[:10000],
                        url=permalink_url,
                        source="BIS",
                        title=permalink_title or "BIS Document",
                        entities=entities,
                        has_china=has_china,
                        matched_keywords=matched
                    )
                    results.append(result)

        return results

    def _extract_entities(self, soup: BeautifulSoup) -> list[str]:
        """从页面提取实体名称"""
        entities = []

        # 查找可能包含实体名称的元素
        for element in soup.find_all(['p', 'li', 'div']):
            text = element.get_text(strip=True)

            # 匹配公司名称模式
            patterns = [
                r'([A-Z][a-zA-Z\s]+(?:Technologies|Group|Corp|Inc|Ltd|Company|Co\.|Holdings|Pte|Limited))',
                r'(Huawei|ZTE|SMIC|Tencent|BYD|CATL|Alibaba|Baidu)',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text)
                entities.extend(matches)

        # 去重
        seen = set()
        unique = []
        for e in entities:
            if e not in seen and len(e) > 3:
                seen.add(e)
                unique.append(e)

        return unique[:50]  # 限制实体数量

    def detect_china_entities(self, content: str, keywords: list[str]) -> tuple[bool, list[str], list[str]]:
        """
        检测中国主体

        Returns:
            (是否有中国主体, 匹配的关键词, 涉及的公司)
        """
        content_lower = content.lower()
        matched_keywords = []
        companies = []

        # 关键词检测
        for kw in keywords:
            if kw.lower() in content_lower:
                matched_keywords.append(kw)

        # 公司名称检测
        company_patterns = [
            r'Huawei',
            r'ZTE',
            r'SMIC',
            r'Tencent',
            r'BYD',
            r'CATL',
            r'Alibaba',
            r'Baidu',
            r'China\s+(?:Electronics|Aviation|General)',
            r'Beijing',
            r'Shanghai',
            r'Shenzhen',
            r'Hong\s+Kong',
        ]

        for pattern in company_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            companies.extend(matches)

        has_china = len(matched_keywords) > 0 or len(companies) > 0

        return has_china, matched_keywords, list(set(companies))

    def crawl_all(self, keywords: list[str], date_start: str = "", date_end: str = "") -> dict:
        """
        爬取所有来源

        Returns:
            {'ofac': [...], 'bis': [...]}
        """
        return {
            'ofac': self.crawl_ofac(keywords, date_start, date_end),
            'bis': self.crawl_bis(keywords, date_start, date_end),
        }

    # ==================== Playwright 支持 ====================

    def _get_playwright_proxy(self) -> Optional[dict]:
        """获取 Playwright 代理配置"""
        if not self.proxy or not self.proxy.enabled:
            return None
        proxy_str = f"http://{self.proxy.host}:{self.proxy.port}"
        return {
            'server': proxy_str,
            'bypass': '<local>'
        }

    async def fetch_with_playwright(self, url: str, wait_time: int = 5) -> Optional[str]:
        """使用 Playwright 获取页面内容（渲染 JavaScript）"""
        from playwright.async_api import async_playwright

        proxy = self._get_playwright_proxy()

        async with async_playwright() as p:
            options = {
                'headless': True,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ]
            }

            if proxy:
                options['proxy'] = proxy

            try:
                browser = await p.chromium.launch(**options)
                context = await browser.new_context(
                    locale='en-US',
                    timezone_id='America/New_York',
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()

                await page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
                await page.wait_for_timeout(wait_time * 1000)  # 等待动态内容加载

                html = await page.content()
                await browser.close()
                return html

            except Exception as e:
                print(f"Playwright 获取失败 {url}: {e}")
                await browser.close()
                return None

    def extract_text_from_html(self, html: str) -> str:
        """从 HTML 提取文本"""
        soup = BeautifulSoup(html, 'lxml')

        # 移除脚本和样式
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()

        # 获取主内容
        text = soup.get_text(separator='\n', strip=True)

        # 清理空行
        lines = [line for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)

    async def crawl_ofac_with_playwright(self, keywords: list[str], date_start: str = "", date_end: str = "") -> list[SanctionsCrawlResult]:
        """使用 Playwright 爬取 OFAC 制裁清单"""
        results = []

        # 使用 Playwright 获取主页面
        html = await self.fetch_with_playwright("https://ofac.treasury.gov/recent-actions/sanctions-list-updates")
        if not html:
            return results

        soup = BeautifulSoup(html, 'lxml')
        text = self.extract_text_from_html(html)

        # 查找所有日期链接
        date_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)

            match = re.search(r'/recent-actions/(\d{8})', href)
            if match:
                date_str = match.group(1)
                date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                if date_start and date_formatted < date_start:
                    continue
                if date_end and date_formatted > date_end:
                    continue

                date_links.append({
                    'url': 'https://ofac.treasury.gov' + href if href.startswith('/') else href,
                    'date': date_formatted,
                    'title': link_text
                })

        # 去重
        seen = set()
        unique_links = []
        for item in date_links:
            if item['url'] not in seen:
                seen.add(item['url'])
                unique_links.append(item)

        # 爬取每个日期页面
        for item in unique_links[:10]:
            detail_html = await self.fetch_with_playwright(item['url'])
            if not detail_html:
                continue

            content = self.extract_text_from_html(detail_html)

            # 关键词匹配
            matched = []
            content_lower = content.lower()
            for kw in keywords:
                if kw.lower() in content_lower:
                    matched.append(kw)

            has_china = len(matched) > 0

            # 提取实体
            entities = self._extract_entities_from_text(content)

            result = SanctionsCrawlResult(
                success=True,
                date=item['date'],
                content=content[:10000],
                url=item['url'],
                source="OFAC",
                title=item['title'],
                entities=entities,
                has_china=has_china,
                matched_keywords=matched
            )
            results.append(result)

        return results

    def _extract_entities_from_text(self, text: str) -> list[str]:
        """从文本提取实体名称"""
        entities = []

        patterns = [
            r'\b([A-Z][a-zA-Z\s]+(?:Technologies|Group|Corp|Inc|Ltd|Company|Co\.|Holdings|Pte|Limited))\b',
            r'\b(Huawei|ZTE|SMIC|Tencent|BYD|CATL|Alibaba|Baidu|China\s+(?:Electronics|Aviation|General))\b',
            r'([\u4e00-\u9fa5]+(?:技术有限公司|集团|有限公司|股份有限公司))\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)

        seen = set()
        unique = []
        for e in entities:
            if e not in seen and len(e) > 2:
                seen.add(e)
                unique.append(e)

        return unique[:50]
