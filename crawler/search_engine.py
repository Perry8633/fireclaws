from typing import Optional
from dataclasses import dataclass
from config.settings import SearchConfig, ProxyConfig
from utils.proxy_manager import ProxyManager


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    snippet: str


class SearchEngine:
    """搜索引擎"""

    def __init__(self, config: SearchConfig, proxy: Optional[ProxyConfig] = None):
        self.config = config
        self.proxy = proxy

    def _get_proxy(self):
        """获取代理"""
        return ProxyManager.get_requests_proxy(self.proxy) if self.proxy else None

    def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """搜索并返回结果"""
        if self.config.provider == "ddgs":
            return self._ddgs_search(query, max_results)
        elif self.config.provider == "brave":
            return self._brave_search(query, max_results)
        elif self.config.provider == "tavily":
            return self._tavily_search(query, max_results)
        else:
            return self._ddgs_search(query, max_results)

    def _ddgs_search(self, query: str, max_results: int) -> list[SearchResult]:
        """DuckDuckGo搜索（无需API Key）"""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS(proxies=self._get_proxy()) as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", "")
                    ))
            return results
        except Exception as e:
            print(f"DDGS搜索失败: {e}")
            return []

    def _brave_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Brave Search API"""
        try:
            import requests

            if not self.config.api_key:
                print("Brave Search需要API Key")
                return []

            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            params = {"q": query, "count": max_results}

            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                proxies=self._get_proxy(),
                timeout=30
            )

            results = []
            if response.status_code == 200:
                data = response.json()
                for item in data.get("web", {}).get("results", [])[:max_results]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", "")
                    ))
            return results
        except Exception as e:
            print(f"Brave搜索失败: {e}")
            return []

    def _tavily_search(self, query: str, max_results: int) -> list[SearchResult]:
        """Tavily API（专为AI优化）"""
        try:
            import requests

            if not self.config.api_key:
                print("Tavily需要API Key")
                return []

            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.config.api_key,
                    "query": query,
                    "max_results": max_results
                },
                proxies=self._get_proxy(),
                timeout=30
            )

            results = []
            if response.status_code == 200:
                data = response.json()
                for item in data.get("results", [])[:max_results]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", "")
                    ))
            return results
        except Exception as e:
            print(f"Tavily搜索失败: {e}")
            return []
