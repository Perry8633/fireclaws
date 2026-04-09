# OFAC/BIS 制裁清单监测系统 - 测试方案

## 测试范围

| 模块 | 测试内容 | 优先级 |
|------|----------|--------|
| 爬虫模块 | OFAC/BIS 页面爬取 | P0 |
| 中国主体识别 | 关键词匹配、实体提取 | P0 |
| LLM 分析 | 分析格式、内容质量 | P1 |
| 报告生成 | 导出 HTML/MD/JSON | P1 |
| 定时任务 | 定时执行逻辑 | P2 |

---

## 测试数据

### 1. OFAC 模拟数据

```python
OFAC_TEST_DATA = {
    "url": "https://ofac.treasury.gov/recent-actions/sanctions-list-updates",
    "test_pages": [
        {
            "date": "2026-04-08",
            "title": "OFAC Recent Actions - April 8, 2026",
            "content": """
            OFAC TAKES ACTION AGAINST PRC-BASED SANCTIONS EVADERS

            The U.S. Department of the Treasury's Office of Foreign Assets Control (OFAC)
            designated the following entities for their involvement in sanctions evasion
            related to Iran:

            DESIGNATED ENTITIES:

            1. Huawei Technologies Co., Ltd.
               Address: Huawei Technologies Co., Ltd., Shenzhen, Guangdong, China
               Alt Name: 华为技术有限公司
               Reason: Providing surveillance technology to Iran

            2. ZTE Corporation
               Address: ZTE Corporation, Shenzhen, China
               Alt Name: 中兴通讯
               Reason: Sanctions evasion

            3. China Electronics Technology Group Corporation (CETC)
               Address: Beijing, China
               Alt Name: 中国电子科技集团有限公司
               Reason: Supporting PRC military

            4. SMIC (Semiconductor Manufacturing International Corporation)
               Address: Shanghai, China
               Alt Name: 中芯国际
               Reason: Military end-use

            5. Tencent Holdings Ltd.
               Address: Shenzhen, China
               Alt Name: 腾讯控股有限公司
               Reason: Surveillance technology

            For more information, visit ofac.treasury.gov
            """,
            "expected_china": True,
            "expected_entities": ["Huawei", "ZTE", "CETC", "SMIC", "Tencent"]
        },
        {
            "date": "2026-04-07",
            "title": "OFAC Recent Actions - April 7, 2026",
            "content": """
            OFAC ACTIONS AGAINST RUSSIAN ELITE

            The following Russian entities were designated:

            1. Gazprom Neft
               Address: Moscow, Russia

            2. Rosneft
               Address: Moscow, Russia

            No PRC-linked entities in this action.
            """,
            "expected_china": False,
            "expected_entities": ["Gazprom", "Rosneft"]
        }
    ]
}
```

### 2. BIS 模拟数据

```python
BIS_TEST_DATA = {
    "url": "https://www.federalregister.gov/agencies/industry-and-security-bureau",
    "test_content": """
    BUREAU OF INDUSTRY AND SECURITY

    Recent Rulemaking:

    ENTITY LIST ADDITIONS - April 8, 2026

    The following entities have been added to the Entity List:

    1. Huawei Technologies Co., Ltd. ( Shenzhen, China )
       Federal Register Citation: 91 FR 12345
       Addition Date: April 8, 2026
       Basis: National security

    2. SMIC - Semiconductor Manufacturing International Corp.
       ( Shanghai, China )
       Federal Register Citation: 91 FR 12346
       Addition Date: April 8, 2026
       Basis: Military end-use

    3. BYD Company Limited
       ( Shenzhen, China )
       Federal Register Citation: 91 FR 12347
       Addition Date: April 8, 2026
       Basis: Surveillance technology

    4. CATL - Contemporary Amperex Technology Co. Limited
       ( Fujian, China )
       Federal Register Citation: 91 FR 12348
       Addition Date: April 8, 2026
       Basis: Military end-use

    5. Beijing Institute of Technology
       ( Beijing, China )
       Federal Register Citation: 91 FR 12349
       Addition Date: April 8, 2026
       Basis: Weapons of mass destruction

    Entity List changes are effective upon publication in the Federal Register.
    """,
    "expected_china": True,
    "expected_entities": ["Huawei", "SMIC", "BYD", "CATL", "Beijing Institute"]
}
```

### 3. 测试关键词

```python
TEST_KEYWORDS = [
    "china",
    "chinese",
    "中国",
    "beijing",
    "shanghai",
    "shenzhen",
    "hong kong",
    "华为",
    "中兴",
    "中芯",
]
```

### 4. 预期分析报告格式

```python
EXPECTED_REPORT_FORMAT = {
    "title_pattern": r"【LLM分析结果】",
    "sections": [
        "## 一、核心信息速览",
        "## 二、制裁类型分析",
        "## 三、综合风险评估",
    ],
    "risk_indicators": ["🔴", "🟡", "🟢"],
    "required_fields": [
        "公司名称",
        "国籍/注册地",
        "注册地址",
    ]
}
```

---

## 测试用例

### TC-001: OFAC 爬虫测试

**目的**: 验证 OFAC 页面爬取功能

```python
def test_crawl_ofac():
    # 准备
    crawler = SanctionsCrawler(proxy=None)

    # 使用模拟数据测试
    # 由于网络限制，使用本地 HTML 解析

    html_content = OFAC_TEST_DATA["test_pages"][0]["content"]
    soup = BeautifulSoup(html_content, 'lxml')

    # 验证实体提取
    entities = crawler._extract_entities(soup)

    assert "Huawei" in str(entities)
    assert "ZTE" in str(entities)

    # 验证关键词匹配
    has_china, matched_kw, companies = crawler.detect_china_entities(
        html_content, TEST_KEYWORDS
    )

    assert has_china == True
    assert "China" in matched_kw or "china" in matched_kw
```

### TC-002: BIS 爬虫测试

**目的**: 验证 BIS 页面爬取功能

```python
def test_crawl_bis():
    crawler = SanctionsCrawler(proxy=None)

    content = BIS_TEST_DATA["test_content"]

    # 验证中国主体检测
    has_china, matched_kw, companies = crawler.detect_china_entities(
        content, TEST_KEYWORDS
    )

    assert has_china == True
    assert len(companies) >= 5  # Huawei, SMIC, BYD, CATL, Beijing
```

### TC-003: 中国主体识别测试

**目的**: 验证关键词匹配和实体提取

```python
def test_china_detection():
    crawler = SanctionsCrawler(proxy=None)

    test_cases = [
        {
            "content": "Huawei Technologies Co., Ltd. headquartered in Shenzhen, China",
            "expected": True,
            "expected_keywords": ["China", "Shenzhen"]
        },
        {
            "content": "Russian company based in Moscow",
            "expected": False,
            "expected_keywords": []
        },
        {
            "content": "北京理工大学 Beijing Institute of Technology",
            "expected": True,
            "expected_keywords": ["beijing", "北京"]
        }
    ]

    for case in test_cases:
        has_china, matched_kw, companies = crawler.detect_china_entities(
            case["content"], TEST_KEYWORDS
        )
        assert has_china == case["expected"], f"Failed for: {case['content'][:50]}"
```

### TC-004: LLM 分析输出格式测试

**目的**: 验证分析报告格式

```python
def test_llm_analysis_format():
    analyzer = SanctionsAnalyzer(llm_config, llm_proxy)

    # 使用模拟爬取结果
    crawl_result = SanctionsCrawlResult(
        success=True,
        date="2026-04-08",
        content=BIS_TEST_DATA["test_content"],
        url="https://example.com",
        source="BIS",
        title="BIS Entity List Update",
        entities=["Huawei", "SMIC", "BYD"],
        has_china=True,
        matched_keywords=["China", "Shenzhen"]
    )

    # 执行分析
    result = analyzer.analyze_sync(crawl_result, "分析制裁实体")

    # 验证格式
    assert "【LLM分析结果】" in result or "## " in result
    assert "核心信息" in result or "## 一" in result

    # 验证制裁类型提及
    assert "BIS" in result or "OFAC" in result
```

### TC-005: 批量分析测试

**目的**: 验证批量处理逻辑

```python
def test_batch_analysis():
    analyzer = SanctionsAnalyzer(llm_config, llm_proxy)

    crawl_results = [
        SanctionsCrawlResult(
            success=True,
            date="2026-04-08",
            content="Huawei Technologies Co., Ltd. - China",
            url="https://example.com/1",
            source="OFAC",
            title="Test Entity 1",
            entities=["Huawei"],
            has_china=True,
            matched_keywords=["China"]
        ),
        SanctionsCrawlResult(
            success=True,
            date="2026-04-08",
            content="Russian company - Russia",
            url="https://example.com/2",
            source="OFAC",
            title="Test Entity 2",
            entities=["Gazprom"],
            has_china=False,  # 不涉及中国
            matched_keywords=[]
        )
    ]

    results = analyzer.analyze_batch(crawl_results)

    # 验证只分析了中国主体
    assert len(results) == 1
    assert results[0][0].title == "Test Entity 1"
```

### TC-006: 报告导出格式测试

**目的**: 验证 HTML/MD/JSON 导出

```python
def test_export_formats():
    from gui.main_window import MainWindow

    # 模拟分析内容
    analysis_content = """# OFAC/BIS制裁分析报告

## 一、核心信息速览
| 公司名称 | Huawei Technologies Co., Ltd. |
| 国籍 | China |

## 二、制裁类型分析
### 2.1 OFAC制裁
| 实体 | 风险 |
|------|------|
| Huawei | 🔴 |
"""

    # 测试 Markdown 导出
    filepath = "/tmp/test_report.md"
    Path(filepath).write_text(analysis_content)
    content = Path(filepath).read_text()
    assert "# OFAC/BIS制裁分析报告" in content

    # 测试 JSON 解析
    from gui.main_window import MainWindow
    # 使用内部方法解析
    report_json = MainWindow()._parse_report_to_json(analysis_content)
    assert "title" in report_json or "content" in report_json
```

---

## 测试脚本

创建 `test_sanctions.py`:

```python
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
"""

BIS_SAMPLE = """
BIS Entity List Additions - April 8, 2026

1. Huawei Technologies Co., Ltd. ( Shenzhen, China )
2. BYD Company Limited ( Shenzhen, China )
3. CATL - Contemporary Amperex Technology ( Fujian, China )
"""

KEYWORDS = ["china", "China", "shenzhen", "shanghai", "hong kong"]


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
    print(f"  - 识别公司: {companies}")

    assert has_china == True, "应该检测到中国主体"
    assert len(companies) >= 2, "应该识别到至少2个公司"

    # 测试 BIS 样本
    has_china, matched, companies = crawler.detect_china_entities(BIS_SAMPLE, KEYWORDS)
    print(f"\nBIS 样本检测结果:")
    print(f"  - 涉及中国主体: {has_china}")
    print(f"  - 匹配关键词: {matched}")
    print(f"  - 识别公司: {companies}")

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
        entities=["Huawei", "SMIC"],
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
    print(markdown[:300])

    assert "# Huawei Technologies Co., Ltd." in markdown
    assert "深圳，中国" in markdown

    print("\n✅ Markdown 转换测试通过")


def main():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# OFAC/BIS 制裁清单监测系统 - 测试套件")
    print("#"*60)

    try:
        test_crawl_result_creation()
        test_china_detection()
        test_llm_analyzer_init()
        test_markdown_conversion()

        print("\n" + "="*60)
        print("🎉 所有基础测试通过!")
        print("="*60)
        print("\n备注: LLM 实际调用需要:")
        print("  1. 有效的 LLM API 端点")
        print("  2. 网络连接")
        print("  3. 代理配置(如有)")
        print("\n完整测试请在 GUI 中运行.")

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
```

---

## 运行测试

```bash
# 运行基础测试（不需要网络）
python test_sanctions.py

# 运行 GUI 测试（需要 Display）
python main.py

# 手动测试步骤
1. 启动应用
2. 选择数据源: 全部
3. 日期范围: 近7天
4. 关键词: china, 中国, 深圳
5. 点击"开始监测"
6. 观察日志和分析结果
```

---

## 预期输出示例

### 日志输出
```
[14:30:00] 开始OFAC/BIS制裁清单监测...
[14:30:00] 数据源: all
[14:30:01] 日期范围: 2026-04-02 至 2026-04-09
[14:30:01] 关键词: china, 中国, 深圳
[14:30:02] 正在爬取OFAC制裁清单...
[14:30:05] OFAC: 发现 2 条更新
[14:30:05] 正在爬取BIS实体清单...
[14:30:08] BIS: 发现 1 条更新
[14:30:08] 发现 3 条涉及中国主体的更新
[14:30:09] 开始LLM深度分析...
[14:30:10] 分析中: Huawei Technologies...
[14:30:15] 监测任务完成
```

### 分析报告示例
```markdown
# OFAC/BIS制裁分析报告
生成时间: 2026-04-09 14:30:00

共发现 **3** 个涉及中国主体的制裁实体

---

## 1. Huawei Technologies Co., Ltd.

【LLM分析结果】- Huawei Technologies Co., Ltd.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 一、核心信息速览
| 字段名 | 原始信息 | 中文 |
|--------|----------|------|
| 公司名称 | Huawei Technologies Co., Ltd. | 华为技术有限公司 |
| 国籍/注册地 | China | 中国 |
| 注册地址 | Shenzhen, Guangdong | 广东省深圳市 |

## 二、制裁类型分析
### 2.1 OFAC制裁（美国）
| 实体名称 | 制裁类型 | 列入日期 | 状态 | 风险等级 |
|----------|----------|----------|------|----------|
| Huawei | OFAC SDN名单 | 2026-04-08 | [高风险] | 🔴 |

### 2.2 BIS实体清单（美国）
| 实体名称 | 制裁类型 | 列入日期 | 状态 | 风险等级 |
|----------|----------|----------|------|----------|
| Huawei | BIS Entity List | 2026-04-08 | [高风险] | 🔴 |

## 三、综合风险评估
该实体同时被 OFAC 和 BIS 列入制裁清单，属于最高风险等级。
```
