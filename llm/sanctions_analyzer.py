"""
OFAC/BIS 制裁分析器
使用LLM进行深度分析
"""
from typing import Optional, Iterator, Dict, Any, List, Callable
from config.settings import LLMConfig, ProxyConfig, SanctionsCrawlResult, SanctionsAnalysisResult
from llm.client import LLMClient


class SanctionsAnalyzer:
    """OFAC/BIS 制裁分析器"""

    SYSTEM_PROMPT = """你是一个专业的OFAC/BIS制裁清单分析助手，负责分析美国制裁实体信息并生成结构化报告。

【任务描述】
{task_desc}

【网页内容】
{content}

【中国主体识别结果】
{china_info}

【分析要求】
请分析上述内容，提取制裁相关信息，生成以下格式的报告：

## 一、核心信息速览
| 字段名 | 原始信息 | 中文翻译 |
|--------|----------|----------|
| 公司名称 | {company_name} | {chinese_name} |
| 国籍/注册地 | China | 中国 |
| 注册地址 | {address} | {chinese_address} |

## 二、制裁类型分析

### 2.1 OFAC制裁（美国）
| 实体名称 | 制裁类型 | 列入日期 | 状态 | 风险等级 |
|----------|----------|----------|------|----------|
| {ofac_info} | OFAC SDN名单 | {ofac_date} | {ofac_status} | {ofac_risk} |

### 2.2 BIS实体清单（美国）
| 实体名称 | 制裁类型 | 列入日期 | 状态 | 风险等级 |
|----------|----------|----------|------|----------|
| {bis_info} | {bis_type} | {bis_date} | {bis_status} | {bis_risk} |

**BIS制裁类型说明：**
- Entity List (EL) - 实体清单
- Entity List Footnote - 带脚注实体清单
- Unverified List (UVL) - 未经核实清单 / 未经验证清单
- Denied Persons List (DPL) - 被拒绝人员清单
- Military End User List (MEU) - 军事最终用户清单

## 三、综合风险评估
{risk_assessment}

## 四、补充信息
如需查询更详细的中文信息，可参考：
- 天眼查：https://www.tianyancha.com/
- 爱企查：https://aiqicha.baidu.com/
- 企查查：https://www.qcc.com/

请严格按照上述格式输出，确保信息准确。"""

    def __init__(
        self,
        llm_config: LLMConfig,
        llm_proxy: Optional[ProxyConfig] = None
    ):
        self.llm_config = llm_config
        self.llm_proxy = llm_proxy
        self.llm = LLMClient(llm_config, llm_proxy)

    def _build_china_info(self, crawl_result: SanctionsCrawlResult) -> str:
        """构建中国主体信息字符串"""
        if not crawl_result.has_china:
            return "未发现明确的中国主体"

        info_parts = []
        if crawl_result.matched_keywords:
            info_parts.append(f"匹配关键词: {', '.join(crawl_result.matched_keywords)}")
        if crawl_result.entities:
            info_parts.append(f"涉及实体: {', '.join(crawl_result.entities[:10])}")

        return "\n".join(info_parts) if info_parts else "发现中国主体"

    def _build_analysis_prompt(self, crawl_result: SanctionsCrawlResult, task_desc: str) -> str:
        """构建分析提示词"""
        china_info = self._build_china_info(crawl_result)

        return self.SYSTEM_PROMPT.format(
            task_desc=task_desc,
            content=crawl_result.content[:3000],
            china_info=china_info,
            company_name=crawl_result.title or "未知",
            chinese_name="（需查询）",
            address="（需查询）",
            chinese_address="（需查询）",
            ofac_info=crawl_result.source,
            ofac_date="（需从内容提取）",
            ofac_status="（需从内容提取）",
            ofac_risk="🔴" if crawl_result.source == "OFAC" else "🟢",
            bis_info=crawl_result.source,
            bis_type="（需从内容提取）",
            bis_date="（需从内容提取）",
            bis_status="（需从内容提取）",
            bis_risk="🔴" if crawl_result.source == "BIS" else "🟢",
            risk_assessment="请根据上述信息进行综合风险评估。"
        )

    def analyze(
        self,
        crawl_result: SanctionsCrawlResult,
        task_desc: str = "分析OFAC/BIS制裁清单更新，识别涉及中国主体的制裁实体",
        progress_callback: Optional[Callable] = None
    ) -> Iterator[str]:
        """执行分析，返回流式输出"""
        prompt = self._build_analysis_prompt(crawl_result, task_desc)

        messages = [
            {"role": "system", "content": "你是一个专业的美国制裁清单分析助手。"},
            {"role": "user", "content": prompt}
        ]

        for chunk in self.llm.chat(messages, stream=True):
            if chunk:
                yield chunk

            if progress_callback:
                progress_callback(f"分析中: {crawl_result.title or crawl_result.source}")

    def analyze_sync(
        self,
        crawl_result: SanctionsCrawlResult,
        task_desc: str = "分析OFAC/BIS制裁清单更新"
    ) -> str:
        """同步执行分析"""
        prompt = self._build_analysis_prompt(crawl_result, task_desc)

        messages = [
            {"role": "system", "content": "你是一个专业的美国制裁清单分析助手。"},
            {"role": "user", "content": prompt}
        ]

        chunks = []
        for chunk in self.llm.chat(messages, stream=False):
            chunks.append(chunk)

        return "".join(chunks)

    def analyze_batch(
        self,
        crawl_results: List[SanctionsCrawlResult],
        task_desc: str = "分析OFAC/BIS制裁清单更新，识别涉及中国主体的制裁实体"
    ) -> List[tuple[SanctionsCrawlResult, str]]:
        """
        批量分析

        Returns:
            List of (crawl_result, analysis)
        """
        results = []

        for result in crawl_results:
            if result.has_china:
                analysis = self.analyze_sync(result, task_desc)
                results.append((result, analysis))

        return results


def extract_sanctions_info(analysis_text: str) -> SanctionsAnalysisResult:
    """从分析文本中提取结构化信息"""
    result = SanctionsAnalysisResult()

    # 提取公司名称
    name_match = analysis_text.split('## 一、核心信息速览')
    if len(name_match) > 1:
        lines = name_match[1].split('\n')
        for line in lines:
            if '公司名称' in line or 'Company' in line:
                # 简单提取
                pass

    # 判断OFAC/BIS
    if 'OFAC' in analysis_text or 'SDN' in analysis_text:
        result.ofac_sanction = True
    if 'BIS' in analysis_text or 'Entity List' in analysis_text:
        result.bis_sanction = True

    # 判断风险等级
    if '🔴' in analysis_text or '高风险' in analysis_text:
        result.risk_level = "🔴"
    elif '🟡' in analysis_text or '中风险' in analysis_text:
        result.risk_level = "🟡"
    else:
        result.risk_level = "🟢"

    result.analysis = analysis_text

    return result
