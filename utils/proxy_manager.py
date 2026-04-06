from typing import Optional
from config.settings import ProxyConfig


class ProxyManager:
    """代理管理器"""

    @staticmethod
    def get_http_proxy(proxy: Optional[ProxyConfig]) -> Optional[str]:
        """获取HTTP代理URL"""
        if not proxy or not proxy.enabled or not proxy.host:
            return None

        auth = ""
        if proxy.username and proxy.password:
            auth = f"{proxy.username}:{proxy.password}@"

        return f"{proxy.protocol}://{auth}{proxy.host}:{proxy.port}"

    @staticmethod
    def get_requests_proxy(proxy: ProxyConfig) -> Optional[dict]:
        """获取requests库需要的代理格式"""
        http_proxy = ProxyManager.get_http_proxy(proxy)
        if not http_proxy:
            return None

        # requests 支持 http/https/socks5
        return {"http": http_proxy, "https": http_proxy}

    @staticmethod
    def get_httpx_proxy(proxy: ProxyConfig) -> Optional[str]:
        """获取httpx库需要的代理格式"""
        return ProxyManager.get_http_proxy(proxy)
