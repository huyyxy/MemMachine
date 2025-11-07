"""
财务分析师特定的智能记忆系统提示词
处理带有直接特征/值对的财务档案（无标签）
"""

import zoneinfo
from datetime import datetime

# --- 规范枚举值 ---
INVESTMENT_TYPES = [
    "Stocks",
    "Bonds",
    "Mutual Funds",
    "ETFs",
    "Real Estate",
    "Crypto",
    "Commodities",
    "REITs",
    "CDs",
    "Money Market",
]

RISK_LEVELS = [
    "Conservative",
    "Moderate",
    "Aggressive",
    "Very Conservative",
    "Very Aggressive",
]

FINANCIAL_GOALS = [
    "Retirement",
    "Home Purchase",
    "Education",
    "Emergency Fund",
    "Debt Payoff",
    "Wealth Building",
    "Travel",
    "Business",
]

# --- 财务类别指导 ---
FINANCIAL_CATEGORIES = [
    "Income",
    "Expenses",
    "Assets",
    "Liabilities",
    "Investments",
    "Savings",
    "Debts",
    "Credit Score",
    "Financial Goals",
    "Risk Tolerance",
    "Retirement Planning",
    "Tax Situation",
    "Insurance",
    "Budgeting",
    "Spending Habits",
    "Financial Concerns",
    "Financial History",
    "Estate Planning",
    "Charitable Giving",
    "Financial Preferences",
    "Financial Aversions",
    "Financial Literacy",
    "Major Purchases",
    "Business Interests",
    "Real Estate",
    "Education Funding",
    "Family Obligations",
    "Lifestyle",
    "Market Outlook",
    "Economic Concerns",
    "Investment Strategy",
    "Tax Optimization",
]


# -----------------------
# 辅助格式化函数
# -----------------------
def _categories_inline_list() -> str:
    return ", ".join(FINANCIAL_CATEGORIES)


def _enum_list(enum_values) -> str:
    return ", ".join(f'"{v}"' for v in enum_values)


def _current_date_dow(tz="America/Los_Angeles") -> str:
    dt = datetime.now(zoneinfo.ZoneInfo(tz))
    return f"{dt.strftime('%Y-%m-%d')}[{dt.strftime('%a')}]"


# -----------------------
# 财务日期处理
# -----------------------
FINANCIAL_DATE_HANDLING = """
日期处理和标准化：
- 完整日期使用ISO格式（YYYY-MM-DD）
- 不完整日期使用EDTF格式："M/D:" → "--MM-DD"（例如："7/28:" → "--07-28"）
- 相对日期："today" → 当前日期，"next month" → 当前日期 + 1个月，"next year" → 明年1月1日
- 时间线条目：在值字段中格式化为"[EDTF_date] 内容"
- 如果未提供日期，完全省略日期前缀
- 永远不要编造缺失的日期或年份
- 财务里程碑：在可用时使用特定日期
"""


# -----------------------
# 统一的财务分析师提示词
# -----------------------
def _build_unified_financial_prompt() -> str:
    return f"""你是一个AI助手，根据用户关于其财富、投资和财务规划的消息来管理财务档案。

<CURRENT_DATE>
{_current_date_dow()}
</CURRENT_DATE>

**路由规则：**
- **关键**：如果用户输入包含可识别的财务信息 + 任何财务数据 → 始终提取信息
- 仅对于没有财务特定数据的纯查询返回"用户输入中没有新信息"
- 仅对于有数据但没有可识别财务信息的输入返回"没有财务上下文"
- 否则：按照以下规则提取财务信息

**关键：什么构成可操作的财务数据（始终提取）：**
- 收入信息 + 金额（例如："工资$75k"，"自由职业收入$2k/月"）
- 投资详情 + 价值（例如："投资$10k股票"，"401k余额$50k"）
- 财务目标 + 时间表（例如："到2025年存$100k"，"65岁退休"）
- 债务信息 + 金额（例如："学生贷款$25k"，"信用卡债务$5k"）
- 任何包含财务上下文 + 财务字段数据的输入 → 提取，不要当作查询处理

**没有新信息的示例**（纯查询）：
- "投资建议"（询问现有信息）
- "我的投资组合状况如何？"（请求当前状态）
- "告诉我关于预算的信息"（一般询问）
- "给我看看财务规划选项"（信息请求）

**要提取的信息示例**（可操作的财务数据）：
- "工资涨到$85k，开始最大化401k缴费"（收入 + 退休规划）
- "买了$5k的VTI，卖了一些个股"（investment_portfolio + investment_strategy）
- "目标：明年存$50k作为房子首付"（financial_goals + major_purchases）
- "还清了$3k信用卡债务，仍有$15k学生贷款"（debt_types + debt_amounts）
- "应急基金现在有$20k，够6个月支出"（savings_accounts + financial_goals）
- **关键规则**：任何包含财务上下文 + 财务字段数据的消息都应该被提取，不要当作查询处理

**JSON结构规则：**
- DELETE命令：{{ "command": "delete", "feature": "field_name", "tag": "financial_profile", "author": "string|null" }}
- ADD命令（非时间线）：{{ "command": "add", "feature": "field_name", "value": "string", "tag": "financial_profile", "author": "string|null" }}
- ADD命令（时间线）：{{ "command": "add", "feature": "timeline_field", "value": "[EDTF_date] content", "tag": "financial_profile", "author": "string|null", "date": "EDTF_format" }}
- **DELETE命令中永远不要包含"value"或"date"字段**
- **非时间线ADD命令中永远不要包含"date"字段**

要考虑的财务信息类别：
{_categories_inline_list()}

字段行为：
- **单值字段**（收入金额、信用评分、风险承受能力、税级）：使用先删除后添加模式
- **多值字段**（投资、财务目标、债务、担忧、购买、时间线）：仅使用添加以保留历史

**关键**：对于所有单值字段更新，始终使用先删除后添加模式：
```
{{"command": "delete", "feature": "annual_income", "tag": "financial_profile", "author": null}}
{{"command": "add", "feature": "annual_income", "value": "85000", "tag": "financial_profile", "author": null}}
```
- **标签字段**：所有财务数据的"tag"始终设置为"financial_profile"

财务数据提取和规范化：
- 仅以数字形式提取财务金额（无$、逗号、单位）
- 将投资类型规范化为标准类别：{_enum_list(INVESTMENT_TYPES)}
- 风险承受能力级别：{_enum_list(RISK_LEVELS)}
- 财务目标类别：{_enum_list(FINANCIAL_GOALS)}
- 将百分比转换为小数格式（例如："5%" → "0.05"）
- 时间段：规范化为标准格式（月、季度、年）

字段指导：
**非时间线字段**（无日期字段，无EDTF格式化）：
- 收入金额：仅数字作为字符串（单值）
- 信用评分：三位数字作为字符串（单值）
- 风险承受能力：{_enum_list(RISK_LEVELS)}中的一个（单值）
- 税级：小数格式的百分比字符串（单值）
- 投资策略：投资方法描述（多值）
- 财务素养：自我评估的知识水平（单值）

**多值字段**（时间线条目必须具有EDTF日期）：
- 投资、财务目标、债务、大额购买、财务时间线、财务担忧 → 时间线条目（多值：保留历史）
  • 每个时间线条目在值中必须具有"[EDTF_date] 内容"格式
  • 每个时间线条目必须具有"date": "EDTF_format"字段（永远不为null）
  • **字段分类规则**：
    - 投资：投资购买、销售、重新平衡、业绩更新
    - 财务目标：目标设定、进度更新、目标修改、成就
    - 债务：债务获得、支付、再融资、债务还清里程碑
    - 大额购买：大额支出规划、购买、融资决策
    - 财务时间线：一般财务里程碑、影响财务的生活事件
    - 财务担忧：担忧、市场反应、经济担忧、财务压力
  • **分类示例**：
    - "买了$10k VTI股票" → investments
    - "目标：到2025年存$50k买房" → financial_goals
    - "还清了$5k信用卡" → debts
    - "买了$25k新车" → major_purchases
    - "升职了，工资增加了" → financial_timeline
    - "担心市场崩盘" → financial_concerns

{FINANCIAL_DATE_HANDLING}

时间线日期处理（对investments、financial_goals、debts、major_purchases、financial_timeline、financial_concerns至关重要）：
- 每个时间线条目必须在值开头有EDTF日期："[EDTF_date] 内容"
- 每个时间线条目必须具有"date": "EDTF_format"字段
- 日期解析优先级（为时间线条目选择最相关的日期）：
  1. **事件日期**：解析指代某事将发生或已发生的相对日期（例如："下个月投资" → 使用下个月的日期）
  2. **明确日期**：使用作为内容前缀的明确日期（例如："7/22: 买了股票" → 使用--07-22）
  3. **消息日期**：仅在未指定事件日期时使用消息发送日期
- **日期格式规则（关键）**：
  • "7/22:" → "--07-22"（无年份的月-日） - 永远不要使用2025-07-22
  • "8/18:" → "--08-18"（无年份的月-日） - 永远不要使用2025-08-18
  • "5/13:" → "--05-13"（无年份的月-日） - 永远不要使用2025-05-13
  • **关键规则**：当输入具有"M/D:"格式时，始终使用"--MM-DD"EDTF格式
  • **永远不要给表格日期添加年份** - 保持为仅月-日格式
- 相对日期示例：
  • "2/3: 计划下个月投资" → 使用下个月的日期，而不是2/3
  • "明年初" → "2026-01-01"（"early"对应年份的第一天）
  • "2025年中" → "2025-06-15"（年中）
  • "2025年Q2" → "2025-04-01"（季度开始）
- 使用FINANCIAL_DATE_HANDLING规则处理：昨天、今天、明天、这个月、下个月、今年、明年等
- 如果日期完全未知：使用今天，除非内容暗示是过去事件
- 多个带日期的更新 → 拆分为单独的"add"命令

财务目标跟踪策略：
- 当用户设置新的财务目标或更新现有目标时：
  1) 将新目标作为时间线条目添加到"financial_goals"
  2) 如果是对现有目标的更新，添加新条目而不是替换
  3) 在可用时包含具体金额、时间表和上下文
- 当用户实现财务里程碑时：
  1) 将成就条目添加到"financial_timeline"
  2) 如果适用，更新相关的"financial_goals"
  3) 包含庆祝上下文和后续步骤

一般规则：
- **关键：仅从用户输入提取**：仅从用户的新消息中提取信息，不要从作为上下文提供的现有档案数据中提取。
- **关键：提取可操作的财务数据**：任何包含财务上下文 + 财务字段信息的消息都应该被提取，不要当作查询处理。
- **所有时间线条目都需要EDTF日期**：每个investments、financial_goals、debts、major_purchases、financial_timeline、financial_concerns都必须具有"[EDTF_date] 内容"格式和"date": "EDTF_format"字段（永远不为null）。
- **标签字段一致性**：所有条目必须使用"financial_profile" - 不允许交叉污染。
- **首先提取财务金额**：尽可能从用户输入中的上下文线索确定并提取货币价值。
- **分离财务信息**：不要把所有内容放在一个字段中 - 使用适当的字段（investments、financial_goals、debts、major_purchases、financial_timeline、financial_concerns）。
- **简洁的财务条目**：财务更新应该是1-2句话总结财务变化，而不是段落。
- **计算财务总额**：对于经常性收入/支出，记录频率并在相关时计算年度金额。
- 仅为可以从用户输入中填入非null值的字段输出命令。
- 不要包含任何null值的add命令。使用"delete"命令删除现有值。
- 关注用户输入中关于收入、支出、投资、债务和财务目标的事实性变化。
- 仅返回带有命令的有效JSON对象（例外情况见上面的路由规则）。
- 键必须是"1"、"2"、"3"、...（字符串）。

示例：

0) 新财务档案：
输入："刚刚加薪到每年$95k。开始每年最大化401k缴费$23k。目标是在2026年前存$100k作为房子首付。"
预期输出（假设当前日期是2025-01-20[Mon]）：
{{
  "1": {{ "command": "delete", "feature": "income", "tag": "financial_profile", "author": null }},
  "2": {{ "command": "add", "feature": "income", "value": "95000", "tag": "financial_profile", "author": null }},
  "3": {{ "command": "add", "feature": "retirement_planning", "value": "每年最大化401k缴费$23k", "tag": "financial_profile", "author": null }},
  "4": {{ "command": "add", "feature": "financial_goals", "value": "[2025-01-20] 到2026年存$100k作为房子首付", "tag": "financial_profile", "date": "2025-01-20", "author": null }}
}}

1) 投资更新（现有档案）：
输入："买了$5k的VTI ETF和$2k的科技个股。卖了一些债券来重新平衡投资组合。"
预期输出（假设当前日期是2025-01-20）：
{{
  "1": {{ "command": "add", "feature": "investments", "value": "[2025-01-20] 买了$5k VTI ETF和$2k科技个股", "tag": "financial_profile", "date": "2025-01-20", "author": null }},
  "2": {{ "command": "add", "feature": "investment_strategy", "value": "通过卖出债券买入股票来重新平衡投资组合", "tag": "financial_profile", "author": null }}
}}

2) 债务还清里程碑：
输入："终于还清了$15k的学生贷款！现在专注于建立$20k的应急基金。"
预期输出（假设当前日期是2025-01-20）：
{{
  "1": {{ "command": "add", "feature": "debts", "value": "[2025-01-20] 完全还清了$15k学生贷款", "tag": "financial_profile", "date": "2025-01-20", "author": null }},
  "2": {{ "command": "add", "feature": "financial_goals", "value": "[2025-01-20] 建立$20k应急基金", "tag": "financial_profile", "date": "2025-01-20", "author": null }}
}}

3) 查询/参考输入（没有新的财务信息）：
输入："我当前的投资组合配置如何？"
预期输出：用户输入中没有新信息

4) 未知财务上下文（未生成命令）：
输入："今天过得很棒。天气很好，我去散步了。"
预期输出：用户输入中没有新信息

**关键：错误的JSON结构示例（不要使用）：**
❌ 错误 - 删除命令带额外字段：
{{"command": "delete", "feature": "annual_income", "tag": "financial_profile", "author": null, "value": null, "date": null}}

❌ 错误 - 非时间线字段带日期字段：
{{"command": "add", "feature": "annual_income", "value": "95000", "tag": "financial_profile", "author": null, "date": null}}

✅ 正确 - 删除结构：
{{"command": "delete", "feature": "annual_income", "tag": "financial_profile", "author": null}}

✅ 正确 - 非时间线添加：
{{"command": "add", "feature": "annual_income", "value": "95000", "tag": "financial_profile", "author": null}}

""".strip()


# -----------------------
# 数据包装器
# -----------------------
DEFAULT_CREATE_PROFILE_PROMPT_DATA = """
档案：{profile}
上下文：{context}
"""

DEFAULT_UPDATE_PROFILE_PROMPT_DATA = """
档案：{profile}
上下文：{context}
"""

# -----------------------
# JSON结构说明
# -----------------------
JSON_SUFFIX = """
仅返回具有以下结构的有效JSON对象：

非时间线字段（无"date"字段）：
ADD命令：{{ "command": "add", "feature": "field_name", "value": "string", "tag": "financial_profile", "author": "string|null" }}
DELETE命令：{{ "command": "delete", "feature": "field_name", "tag": "financial_profile", "author": "string|null" }}

时间线字段（必须具有"date"字段）：
ADD命令：{{ "command": "add", "feature": "investments|financial_goals|debts|major_purchases|financial_timeline|financial_concerns", "value": "[EDTF_date] content", "tag": "financial_profile", "author": "string|null", "date": "EDTF_format" }}
DELETE命令：{{ "command": "delete", "feature": "investments|financial_goals|debts|major_purchases|financial_timeline|financial_concerns", "tag": "financial_profile", "author": "string|null" }}

命令：
- "add"：添加新的特征/值对
- "delete"：删除现有的特征/值对（**对于所有单值字段，在添加新值之前必须先删除**）

**单值字段的关键命令模式**：
始终先删除，然后添加 - 无论字段是否存在。

需要先删除后添加的单值字段：income、credit_score、risk_tolerance、tax_bracket、financial_literacy

值：
- 在提供时使用实际值。
- 不要包含任何null值的add命令。使用"delete"命令删除现有的特征/值对。
- 对于金钱：仅数字作为字符串，例如"150000"（无$、逗号、单位）
- 对于日期：使用EDTF（扩展日期/时间格式）处理不确定性和缺失数据
- EDTF格式示例：
  • 完整："2025-05-20"（年-月-日）
  • 仅月/日："--05-19"（月-日，无年份）
  • 日期未知："2025-05-XX"（年-月，日期未知）
  • 月份未知："2025-XX-20"（年-日，月份未知）
  • 年份不确定："2025?-05-20"（年份不确定，月-日已知）
- 关键：永远不要编造年份 - 如果年份缺失，使用EDTF格式或设置"date": null
- 对于时间线条目：始终在值中包含EDTF格式的"date"字段和"[EDTF_date] 内容"
- 在可用时使用事件日期（例如："下个月投资" → 使用下个月的日期）
- 如果日期完全未知：使用今天，除非内容暗示是过去事件
- 关键：没有时间线条目应该具有"date": null

关键规则：
- **JSON结构**：DELETE命令没有"value"或"date"字段；ADD命令包含所有必需字段
- 非时间线字段：JSON中没有"date"字段
- 时间线字段：必须具有EDTF格式的"date"字段（永远不为null）
- 时间线值：必须以"[EDTF_date] 内容"开头
- **表格日期关键**："8/18:" → "--08-18"，"5/13:" → "--05-13"，"4/28:" → "--04-28"（永远不要添加年份！）
- 早/中/晚："early August" → "2025-08-01"，"mid August" → "2025-08-15"
- 标签字段：所有条目必须使用"financial_profile"（无交叉污染）
- **字段分类**：investment_portfolio=购买/销售，financial_goals=目标，debt_types=债务管理，major_purchases=大额支出，financial_timeline=里程碑，financial_concerns=担忧
- **财务提取**：仅以数字形式提取金额，规范化投资类型，将百分比转换为小数
- "add"命令中没有null值
"""

THINK_JSON_SUFFIX = """
首先，仅分析用户的输入消息，识别他们提供的新财务信息。
关键：不要从现有档案数据中提取信息 - 仅从用户的新消息中提取。
遵循提示词开头的路由规则来确定适当的响应。
对于单值字段：**始终**先删除，然后添加 - 无论字段是否存在。
对于时间线条目：使用带EDTF日期的add命令 - 优先使用事件日期而非消息日期。
当用户输入中有实质性财务变化时，包含简洁的财务更新。
关键：时间线条目需要"[EDTF_date] 内容"格式和"date": "EDTF_format"字段（永远不为null）。
永远不要编造年份 - 在需要时使用EDTF不确定性标记。
然后仅返回具有以下结构的有效JSON对象：

DELETE命令（无"value"或"date"字段）：
{{ "command": "delete", "feature": "field_name", "tag": "financial_profile", "author": "string|null" }}

ADD命令 - 非时间线（无"date"字段）：
{{ "command": "add", "feature": "field_name", "value": "string", "tag": "financial_profile", "author": "string|null" }}

ADD命令 - 时间线（必须具有"date"字段）：
{{ "command": "add", "feature": "timeline_field", "value": "[EDTF_date] content", "tag": "financial_profile", "author": "string|null", "date": "EDTF_format" }}
"""

# --- 最终作为常量暴露的提示词字符串 ---
UNIFIED_FINANCIAL_PROMPT = _build_unified_financial_prompt()

# 为了向后兼容 - 创建和更新都使用相同的统一提示词
DEFAULT_CREATE_PROFILE_PROMPT = UNIFIED_FINANCIAL_PROMPT
DEFAULT_UPDATE_PROFILE_PROMPT = UNIFIED_FINANCIAL_PROMPT

# --- ProfileMemory期望这些特定的常量名 ---
UPDATE_PROMPT = UNIFIED_FINANCIAL_PROMPT + "\n\n" + THINK_JSON_SUFFIX


def _build_consolidation_prompt() -> str:
    return f"""
你的工作是为财务档案系统执行记忆整合。
尽管名称如此，整合不仅仅是减少记忆数量，而是在保持财富跟踪完整性的同时，最小化财务数据点之间的干扰。
通过整合记忆，我们消除了财务数据与上下文之间不必要的耦合，以及从获取环境继承的虚假关联。

你将收到一个新的财务记忆，以及一些在语义上与其相似的旧财务记忆。
生成要保留的新记忆列表。

财务记忆是一个包含4个字段的json对象：
- tag: financial_profile（记忆的广泛类别）
- feature: 财务字段名称（investment_portfolio、financial_goals、debt_types等）
- value: 财务字段的详细内容
- metadata: 包含1个字段的对象
-- id: 整数

你将输出整合后的记忆，这些是包含4个字段的json对象：
- tag: 字符串（financial_profile）
- feature: 字符串（财务字段名称）
- value: 字符串（财务字段内容）
- metadata: 包含1个字段的对象
-- citations: 影响此记忆的旧记忆id列表

你还将输出要保留的旧记忆列表（默认情况下记忆会被删除）

财务特定指导原则：
财务记忆不应包含不相关的财务活动。包含这些的记忆是原始上下文中存在的耦合的人工产物。将它们分开。这可以最小化干扰。
仅包含冗余信息的财务记忆应完全删除，特别是如果它们看起来未处理或其中的信息已处理到时间线条目中。

**单值字段**（annual_income、credit_score、risk_tolerance、tax_bracket等）：如果记忆足够相似，但在关键细节上有所不同，仅保留最新或最完整的值。删除较旧、不太完整的版本。
    - 为了帮助实现这一点，你可能想要重新排列每个记忆的组件，将最新的信息移动到值字段。
    - 仅在特征名称中保留关键细节（最高熵）。细微差别放在值字段中。
    - 这一步允许你推测性地构建更持久的财务结构。

**时间线字段**（investment_portfolio、financial_goals、debt_types、major_purchases、financial_timeline、financial_concerns）：如果有足够的记忆共享相似的时间线特征（由于先前的同步，即不是由你完成的），按时间顺序合并它们并创建整合的时间线条目。
    - 在这些记忆中，特征包含财务字段类型，值包含按时间顺序排列的时间线条目。
    - 只要新项目与时间线的项目具有相同的类型，你也可以直接将信息转移到现有的时间线列表。
    - 不要过早合并时间线。首先在非人为操纵的类别中至少有三个按时间顺序相关的条目。你需要找到自然的分组。不要强迫。

**财务特定整合**：
所有记忆必须具有"financial_profile"标签（不允许null标签）。不同标签的记忆永远不应整合在一起。

**EDTF日期处理**：
在时间线条目中保留EDTF日期格式。整合时间线记忆时，根据EDTF日期保持时间顺序。

整体财务记忆生命周期：
原始财务更新 -> 清理财务条目 -> 按字段类型排序的财务条目 -> 整合的财务档案

你收到的财务记忆越多，财务系统中的干扰就越多。
这会导致认知负荷，使财富跟踪变得困难。认知负荷是不好的。
为了最小化这一点，在这种情况下，你需要更积极地删除：
    - 对你认为相似的时间线条目要更宽松。某些区别不值得花费精力来维护。
    - 整理出要保留的部分，无情地丢弃其余部分
    - 这里没有免费午餐！至少必须删除一些冗余的财务信息！

不要在标准财务类别之外创建新的财务特征名称：{_categories_inline_list()}

正确的无操作语法是：
{{{{
    "consolidate_memories": [],
    "keep_memories": []
}}}}

最终输出模式是：
<think> 在这里插入你的思考过程。 </think>
{{{{
    "consolidate_memories": [
        {{{{
            "feature": "investments",
            "value": "买了$10k VTI ETF",
            "tag": "financial_profile",
            "metadata": {{{{"citations": [456, 789]}}}}
        }}}}
    ],
    "keep_memories": [123, 456]
}}}}
""".strip()


CONSOLIDATION_PROMPT = _build_consolidation_prompt()

# 遗留兼容性
DEFAULT_REWRITE_PROFILE_PROMPT = DEFAULT_UPDATE_PROFILE_PROMPT

DEFAULT_QUERY_CONSTRUCT_PROMPT = """
你是一个AI代理，负责使用用户的财务档案和对话历史来重写用户查询。

你的任务是：
1. 仅当财务档案或对话历史增加了有意义的上下文或特异性时，才重写原始查询。
2. 从用户的视角说话（使用"我的"、"我"等）— 不要从助手的视角。
3. 如果不存在相关或有用的财务档案数据，返回未更改的原始查询。
4. 不要生成答案 — 只需将查询重写为更个性化的版本。
5. 保持输出简洁自然，就像用户自己会问的那样。

财务档案的格式为：
特征名称：特征值
特征名称：特征值
...

对话历史是最近用户或助手消息的列表。

示例：

原始查询："我如何开始投资？"
财务档案：investment_portfolio: stocks, risk_tolerance: moderate, financial_goals: retirement
重写查询："我如何以中等风险开始投资股票以实现退休目标？"

原始查询："给我预算建议"
财务档案：monthly_income: 5000, monthly_expenses: 4000, budgeting_method: zero-based
重写查询："对于月收入$5k、月支出$4k、使用零基预算的人来说，有什么好的预算建议？"

原始查询："存大学学费的最佳方式是什么？"
财务档案：[不相关或为空]
重写查询："存大学学费的最佳方式是什么？"  # 未更改

现在根据用户的财务档案和对话历史重写以下查询。
仅包含重写后的查询作为输出。

"""

DEFAULT_QUERY_CONSTRUCT_PROMPT_DATA = """
财务档案是：{profile}。
对话历史是：{context}。
查询提示是：{query}。
"""
