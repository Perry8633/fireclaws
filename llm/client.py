from typing import Optional, Iterator, Dict, Any, List
from openai import OpenAI
from config.settings import LLMConfig, ProxyConfig
from utils.proxy_manager import ProxyManager


class LLMClient:
    """OpenAI兼容的LLM客户端"""

    def __init__(self, config: LLMConfig, proxy: Optional[ProxyConfig] = None):
        self.config = config
        self.proxy = proxy
        self._client = None

    def _get_client(self) -> OpenAI:
        """获取或创建客户端"""
        if self._client is None:
            import os
            # 清除可能存在的代理环境变量，防止冲突
            for k in list(os.environ.keys()):
                if 'proxy' in k.lower():
                    del os.environ[k]

            # 设置代理（如果需要）
            http_proxy = ProxyManager.get_httpx_proxy(self.proxy)
            if http_proxy:
                os.environ["http_proxy"] = http_proxy
                os.environ["https_proxy"] = http_proxy

            self._client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                timeout=120
            )
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: Optional[float] = None
    ) -> Iterator[str]:
        """发送聊天请求"""
        client = self._get_client()

        if temperature is None:
            temperature = self.config.temperature

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            stream=stream,
            temperature=temperature
        )

        if stream:
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            if response.choices and response.choices[0].message:
                yield response.choices[0].message.content

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        stream: bool = True
    ) -> Iterator[Dict[str, Any]]:
        """发送带工具调用的聊天请求"""
        client = self._get_client()

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=tools,
            stream=stream,
            temperature=self.config.temperature
        )

        if stream:
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    yield {
                        "content": delta.content if delta.content else "",
                        "tool_calls": delta.tool_calls if delta.tool_calls else []
                    }
        else:
            if response.choices and response.choices[0].message:
                msg = response.choices[0].message
                yield {
                    "content": msg.content if msg.content else "",
                    "tool_calls": msg.tool_calls if msg.tool_calls else []
                }
