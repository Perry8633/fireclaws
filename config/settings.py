from pydantic import BaseModel, Field
from typing import Optional


class ProxyConfig(BaseModel):
    enabled: bool = False
    protocol: str = "http"  # http / https / socks5
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    def to_proxy_dict(self) -> Optional[dict]:
        if not self.enabled or not self.host:
            return None
        protocol = self.protocol
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return {protocol: f"{protocol}://{auth}{self.host}:{self.port}"}


class LLMConfig(BaseModel):
    provider: str = "custom"  # minimax / deepseek / qwen / custom
    base_url: str = "http://127.0.0.1:4000/v1"
    api_key: str = ""  # 请在设置中配置
    model: str = "deepseek-chat"
    temperature: float = 0.7
    system_prompt: str = "你是一个专业的分析助手，请分析用户提供的内容并生成结构化报告，包含标题、概述和详细内容。"


class SearchConfig(BaseModel):
    provider: str = "ddgs"  # ddgs / brave / tavily
    api_key: str = ""  # Brave/Tavily需要，DDGS不需要


class FeishuConfig(BaseModel):
    enabled: bool = False
    cli_path: str = ""
    app_id: str = ""
    app_secret: str = ""


class ScheduleConfig(BaseModel):
    """定时任务配置"""
    enabled: bool = False
    schedule_type: str = "once"  # once / daily / weekly / cron
    daily_time: str = "09:00"
    weekly_day: int = 0  # 0=Monday
    weekly_time: str = "09:00"
    cron_expression: str = "0 9 * * *"


class AppConfig(BaseModel):
    llm_proxy: ProxyConfig = ProxyConfig()
    search_proxy: ProxyConfig = ProxyConfig()  # 搜索引擎代理
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    feishu: FeishuConfig = FeishuConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    password_hash: str = ""  # PBKDF2 hash
