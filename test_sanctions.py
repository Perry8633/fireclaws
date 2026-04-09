#!/usr/bin/env python3
"""
OFAC/BIS 制裁清单监测系统 - 测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings('ignore')

from crawler.sanctions_crawler import SanctionsCrawler
from crawler.base_crawler import BaseCrawler
from llm.sanctions_analyzer import SanctionsAnalyzer
from config.settings import LLMConfig, ProxyConfig, SanctionsCrawlResult
from bs4 import BeautifulSoup


# ==================== 测试数据 ====================

OFAC_SAMPLE = """
OFAC Recent Actions - April 8, 2026

DESIGNATED ENTITIES:

1. Huawei Technologies Co., Ltd.
   Address: Shenzhen, Guangdong, China
   Alt Name: 华为技术有限公司

2. SMIC - Semiconductor Manufacturing International Corporation
   Address: Shanghai, China
   Alt Name: 中芯国际

3. ZTE Corporation
   Address: Shenzhen, China
   Alt Name: 中兴通讯
"""

BIS_SAMPLE = """
BIS Entity List Additions - April 8, 2026

1. Huawei Technologies Co., Ltd. ( Shenzhen, China )
2. BYD Company Limited ( Shenzhen, China )
3. CATL - Contemporary Amperex Technology ( Fujian, China )
4. Beijing Institute of Technology ( Beijing, China )
"""

KEYWORDS = ["china", "China", "shenzhen", "shanghai", "hong kong", "beijing"]


# ==================== 测试函数 ====================

def test_china_detection():
    """TC-003: 中国主体识别测试"""
    print("\n" + "="*60)
    print("TC-003: 中国主体识别测试")
    print("="*60)

    crawler = SanctionsCrawler(proxy=None)

    # 测试 OFAC 样本
    has_china, matched, companies = crawler.detect_china_entities(OFAC_SAMPLE, KEYWORDS)
    print(f"OFAC 样本检测结果:")
    print(f"  - 涉及中国主体: {has_china}")
    print(f"  - 匹配关键词: {matched}")
    print(f"  - 识别公司: {companies[:5]}")

    assert has_china == True, "应该检测到中国主体"
    assert len(companies) >= 3, "应该识别到至少3个公司"

    # 测试 BIS 样本
    has_china, matched, companies = crawler.detect_china_entities(BIS_SAMPLE, KEYWORDS)
    print(f"\nBIS 样本检测结果:")
    print(f"  - 涉及中国主体: {has_china}")
    print(f"  - 匹配关键词: {matched}")
    print(f"  - 识别公司: {companies[:5]}")

    assert has_china == True, "应该检测到中国主体"

    print("\n✅ TC-003 通过")


def test_crawl_result_creation():
    """测试爬取结果数据结构"""
    print("\n" + "="*60)
    print("测试: 爬取结果数据结构")
    print("="*60)

    result = SanctionsCrawlResult(
        success=True,
        date="2026-04-08",
        content=OFAC_SAMPLE[:200],
        url="https://ofac.treasury.gov/test",
        source="OFAC",
        title="Test OFAC Action",
        entities=["Huawei", "SMIC", "ZTE"],
        has_china=True,
        matched_keywords=["China", "Shenzhen"]
    )

    print(f"success: {result.success}")
    print(f"date: {result.date}")
    print(f"source: {result.source}")
    print(f"has_china: {result.has_china}")
    print(f"entities: {result.entities}")
    print(f"matched_keywords: {result.matched_keywords}")

    assert result.success == True
    assert result.has_china == True
    assert "Huawei" in result.entities

    print("\n✅ 数据结构测试通过")


def test_llm_analyzer_init():
    """测试 LLM 分析器初始化"""
    print("\n" + "="*60)
    print("测试: LLM 分析器初始化")
    print("="*60)

    llm_config = LLMConfig(
        base_url="http://127.0.0.1:4000/v1",
        api_key="sk-test",
        model="deepseek-chat"
    )

    analyzer = SanctionsAnalyzer(llm_config=llm_config)

    print(f"LLM config base_url: {analyzer.llm_config.base_url}")
    print(f"LLM model: {analyzer.llm_config.model}")

    assert analyzer.llm_config.base_url == "http://127.0.0.1:4000/v1"

    print("\n✅ 分析器初始化测试通过")


def test_markdown_conversion():
    """测试 Markdown 转换"""
    print("\n" + "="*60)
    print("测试: Markdown 转换")
    print("="*60)

    from crawler.markdown_converter import MarkdownConverter

    html = """
    <html>
    <body>
        <h1>Huawei Technologies Co., Ltd.</h1>
        <p>这是<strong>华为</strong>技术有限公司的描述。</p>
        <ul>
            <li>深圳，中国</li>
            <li>成立于1987年</li>
        </ul>
    </body>
    </html>
    """

    converter = MarkdownConverter()
    markdown = converter.convert(html)

    print("转换结果:")
    print("-" * 40)
    print(markdown[:300])
    print("-" * 40)

    assert "# Huawei Technologies Co., Ltd." in markdown
    assert "深圳，中国" in markdown

    print("\n✅ Markdown 转换测试通过")


def test_entity_extraction():
    """测试实体提取"""
    print("\n" + "="*60)
    print("测试: 实体提取")
    print("="*60)

    crawler = SanctionsCrawler(proxy=None)
    # 使用 _extract_entities_from_text 处理纯文本
    entities = crawler._extract_entities_from_text(OFAC_SAMPLE)

    print(f"提取到的实体: {entities[:10]}")

    assert len(entities) > 0, "应该提取到实体"

    print("\n✅ 实体提取测试通过")


def test_config_loading():
    """测试配置加载"""
    print("\n" + "="*60)
    print("测试: 配置加载")
    print("="*60)

    from config.settings import AppConfig, SanctionsConfig

    config = AppConfig()

    print(f"sanctions.keywords: {config.sanctions.keywords}")
    print(f"sanctions.ofac_url: {config.sanctions.ofac_url}")
    print(f"sanctions.bis_url: {config.sanctions.bis_url}")
    print(f"llm.base_url: {config.llm.base_url}")
    print(f"llm_proxy.host: {config.llm_proxy.host}")
    print(f"llm_proxy.port: {config.llm_proxy.port}")

    assert "china" in config.sanctions.keywords
    assert "ofac.treasury.gov" in config.sanctions.ofac_url

    print("\n✅ 配置加载测试通过")


def main():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# OFAC/BIS 制裁清单监测系统 - 测试套件")
    print("#"*60)

    try:
        test_config_loading()
        test_crawl_result_creation()
        test_entity_extraction()
        test_china_detection()
        test_llm_analyzer_init()
        test_markdown_conversion()

        print("\n" + "="*60)
        print("🎉 所有基础测试通过!")
        print("="*60)
        print("\n备注: LLM 实际调用需要:")
        print("  1. 有效的 LLM API 端点")
        print("  2. 网络连接")
        print("  3. 代理配置(如需要)")
        print("\n完整测试请在 GUI 中运行.")
        print("\n测试文件: test_plan.md")
        print("测试数据: 本文件中的 OFAC_SAMPLE, BIS_SAMPLE")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
