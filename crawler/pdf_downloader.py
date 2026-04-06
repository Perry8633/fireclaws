import requests
import re
from pathlib import Path
from typing import Optional, List
from bs4 import BeautifulSoup
from config.settings import ProxyConfig
from utils.proxy_manager import ProxyManager


class PDFDownloader:
    """PDF下载器"""

    def __init__(self, proxy: Optional[ProxyConfig] = None, output_dir: str = "data/downloads"):
        self.proxy = proxy
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_proxy(self):
        return ProxyManager.get_requests_proxy(self.proxy) if self.proxy else None

    def find_pdf_links(self, html: str, base_url: str) -> List[str]:
        """从HTML中查找PDF链接"""
        soup = BeautifulSoup(html, 'lxml')
        pdf_links = []

        # 查找 <a href="*.pdf">
        for a in soup.find_all('a', href=True):
            href = a['href']
            if self._is_pdf_url(href):
                pdf_links.append(self._make_absolute_url(href, base_url))

        # 查找 <a href="..." onclick=...pdf...>
        for a in soup.find_all('a', onclick=True):
            onclick = a.get('onclick', '')
            if '.pdf' in onclick.lower():
                href = a.get('href', '')
                if href:
                    pdf_links.append(self._make_absolute_url(href, base_url))

        return list(set(pdf_links))

    def _is_pdf_url(self, url: str) -> bool:
        """判断是否为PDF链接"""
        if not url:
            return False
        url_lower = url.lower()
        return (
            url_lower.endswith('.pdf') or
            'application/pdf' in url_lower or
            '/pdf' in url_lower
        )

    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """转换为绝对URL"""
        if not url:
            return base_url

        if url.startswith('http://') or url.startswith('https://'):
            return url

        if url.startswith('//'):
            return 'https:' + url

        if url.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{url}"

        return f"{base_url.rstrip('/')}/{url}"

    def download_pdf(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """下载PDF到本地"""
        try:
            response = requests.get(
                url,
                proxies=self._get_proxy(),
                timeout=60,
                stream=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()

            # 确定文件名
            if not filename:
                from urllib.parse import urlparse, unquote
                path = urlparse(url).path
                filename = unquote(Path(path).name)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'

            # 保存文件
            filepath = self.output_dir / filename

            # 处理重名
            counter = 1
            while filepath.exists():
                stem = filepath.stem
                suffix = filepath.suffix
                filepath = self.output_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return str(filepath)

        except Exception as e:
            print(f"下载PDF失败 {url}: {e}")
            return None

    def download_all(self, pdf_links: List[str]) -> List[str]:
        """下载所有PDF"""
        saved_paths = []
        for link in pdf_links:
            path = self.download_pdf(link)
            if path:
                saved_paths.append(path)
        return saved_paths
