from typing import Iterator, Optional, Callable
from dataclasses import dataclass

from config.settings import LLMConfig, ProxyConfig
from crawler.search_engine import SearchEngine, SearchResult
from .client import LLMClient


@dataclass
class AnalysisReport:
    """分析报告"""
    title: str = ""
    summary: str = ""
    content: str = ""
    sources: list = None

    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class LLMAgent:
    """LLM分析代理"""

    # 工具定义
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "搜索网络获取相关信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    SYSTEM_PROMPT = """你是一个专业的分析助手。你具有搜索网络的能力。

当分析过程中发现信息不足时，你可以通过调用 search(query) 函数搜索相关信息。
搜索时使用简短的关键词。

当直接输出分析报告，不需要再调用搜索时，说"完成"。

请按以下格式输出报告：
# 标题
## 概述
[简要总结关键发现]

## 详细内容
[详细分析，可包含引用来源]

"""

    def __init__(
        self,
        llm_config: LLMConfig,
        search_engine: SearchEngine,
        llm_proxy: Optional[ProxyConfig] = None
    ):
        self.llm = LLMClient(llm_config, llm_proxy)
        self.search_engine = search_engine
        self.messages = []

    def reset(self):
        """重置对话"""
        self.messages = []

    def analyze(
        self,
        context: str,
        user_query: str,
        custom_system_prompt: Optional[str] = None,
        max_search_rounds: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> Iterator[str]:
        """
        分析内容并返回流式输出

        Args:
            context: 爬取的内容
            user_query: 用户的问题
            custom_system_prompt: 自定义系统提示词
            max_search_rounds: 最大搜索轮次
            progress_callback: 进度回调 (status: str)
        """
        system_prompt = custom_system_prompt or self.SYSTEM_PROMPT

        # 构建初始消息
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下内容并输出报告：\n\n{context}\n\n用户问题：{user_query}"}
        ]

        search_count = 0
        is_searching = False

        # 流式生成
        for chunk in self.llm.chat_with_tools(self.messages, tools=self.TOOLS, stream=True):
            content = chunk.get("content", "")
            tool_calls = chunk.get("tool_calls", [])

            # 如果有内容输出
            if content:
                yield content

            # 检查是否需要调用搜索
            if tool_calls and search_count < max_search_rounds:
                for tool_call in tool_calls:
                    if tool_call.function and tool_call.function.name == "search":
                        query = tool_call.function.arguments.get("query", "")
                        if query and not is_searching:
                            is_searching = True
                            search_count += 1

                            if progress_callback:
                                progress_callback(f"LLM正在搜索: {query}")

                            # 执行搜索
                            search_results = self.search_engine.search(query, max_results=5)

                            # 将搜索结果添加到对话
                            results_text = "\n".join([
                                f"- {r.title}: {r.url}\n  {r.snippet}"
                                for r in search_results
                            ])

                            self.messages.append({
                                "role": "assistant",
                                "content": content if content else ""
                            })
                            self.messages.append({
                                "role": "system",
                                "content": f"搜索结果：\n{results_text}"
                            })

                            is_searching = False
                            break

        # 最后一轮没有tool_calls时的处理
        if not any(
            tc.function.name == "search"
            for chunk in [self.messages]
            for tc in (chunk.get("tool_calls") or [])
            if hasattr(chunk, "tool_calls")
        ):
            # 结束分析
            pass

    def analyze_simple(
        self,
        context: str,
        user_query: str,
        custom_system_prompt: Optional[str] = None
    ) -> str:
        """
        简单分析（无搜索功能，一次性返回）
        """
        system_prompt = custom_system_prompt or self.SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下内容并输出报告：\n\n{context}\n\n用户问题：{user_query}"}
        ]

        # 非流式获取完整回复
        response = list(self.llm.chat(messages, stream=False))
        return "".join(response)


def extract_report_sections(markdown_text: str) -> AnalysisReport:
    """从Markdown文本中提取报告各部分"""
    report = AnalysisReport()

    lines = markdown_text.split('\n')
    current_section = None
    content_buffer = []

    for line in lines:
        if line.startswith('# ') and not report.title:
            report.title = line[2:].strip()
            current_section = None
        elif line.startswith('## '):
            if current_section == "content":
                report.content = '\n'.join(content_buffer).strip()
                content_buffer = []
            elif current_section == "summary" and content_buffer:
                report.summary = '\n'.join(content_buffer).strip()
                content_buffer = []

            section_name = line[3:].strip().lower()
            if '概述' in section_name or 'summary' in section_name:
                current_section = "summary"
            elif '详细' in section_name or 'content' in section_name:
                current_section = "content"
        else:
            content_buffer.append(line)

    # 处理最后一部分
    if current_section == "content":
        report.content = '\n'.join(content_buffer).strip()
    elif current_section == "summary" and content_buffer:
        report.summary = '\n'.join(content_buffer).strip()

    return report
