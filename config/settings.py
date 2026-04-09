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


class HistoryItem(BaseModel):
    """历史记录项"""
    id: str = ""
    timestamp: str = ""
    task_desc: str = ""
    keywords: list[str] = []
    urls: list[str] = ""


class HistoryConfig(BaseModel):
    """历史记录配置"""
    items: list[HistoryItem] = []
    max_items: int = 6


# ============ OFAC/BIS 制裁监测相关配置 ============

class SanctionsConfig(BaseModel):
    """制裁监测配置"""
    keywords: list[str] = ["china", "中国", "hong kong", "北京", "上海", "深圳"]
    ofac_url: str = "https://ofac.treasury.gov/recent-actions/sanctions-list-updates"
    bis_url: str = "https://www.federalregister.gov/agencies/industry-and-security-bureau"
    date_range_start: str = ""  # YYYY-MM-DD
    date_range_end: str = ""    # YYYY-MM-DD
    email_recipients: list[str] = []
    email_enabled: bool = False
    icenter_enabled: bool = False


class SanctionsCrawlResult(BaseModel):
    """制裁爬取结果"""
    success: bool = False
    date: str = ""  # 发布日期
    content: str = ""
    url: str = ""
    source: str = ""  # OFAC / BIS
    title: str = ""
    entities: list[str] = []  # 实体名称列表
    has_china: bool = False
    matched_keywords: list[str] = []


class SanctionsAnalysisResult(BaseModel):
    """制裁分析结果"""
    company_name: str = ""
    chinese_name: str = ""
    chinese_address: str = ""
    registration_number: str = ""
    shareholders: str = ""
    parent_company: str = ""
    ofac_sanction: bool = False
    bis_sanction: bool = False
    risk_level: str = "🟢"  # 🔴 高风险 🟡 中风险 🟢 低风险
    analysis: str = ""
    source: str = ""


class EmailConfig(BaseModel):
    """邮件配置"""
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = ""
    recipients: list[str] = []


class AppConfig(BaseModel):
    llm_proxy: ProxyConfig = ProxyConfig(
        enabled=True,
        protocol="http",
        host="proxysz.zte.com.cn",
        port=80
    )
    search_proxy: ProxyConfig = ProxyConfig()  # 搜索引擎代理
    llm: LLMConfig = LLMConfig()
    search: SearchConfig = SearchConfig()
    feishu: FeishuConfig = FeishuConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    history: HistoryConfig = HistoryConfig()
    sanctions: SanctionsConfig = SanctionsConfig()
    email: EmailConfig = EmailConfig()
    password_hash: str = ""  # PBKDF2 hash
