"""
用于智能记忆系统的CRM特定提示
处理公司档案，使用直接的特征/值对（无标签）
"""

import zoneinfo
from datetime import datetime

# --- 标准枚举 ---
SALES_STAGE_ENUM = [
    "Validated",
    "Qualified",
    "Interest",
    "Closed Won",
    "Closed Lost",
    "POC",
]

PRODUCTS = ["MMCloud", "MMBatch", "Intelligent Memory", "MMAI"]

# --- 电子表格表头映射 ---
CRM_FIELD_MAPPINGS = {
    "Sales Stage": "sales_stage",
    "Lead Creation Date": "lead_creation_date",
    "Close Date": "close_date",
    "MemVerge Product": "memverge_product",
    "Estimated Deal Value": "estimated_deal_value",
    "Company Website (Domain)": "company_website",
    "Next Step": "next_step",
    "Company": "company",
    "Primary Contact": "primary_contact",
    "Job Title": "job_title",
    "Email": "email",
    "Phone #": "phone",
    "Deployment Environment": "deployment_environment",
    "Status": "status",  # 仅追加的时间线字段
    "Comments": "comments",
    "Author": "author",
}

# --- 预定义的CRM特征 ---
CRM_FEATURES = [
    "sales_stage",
    "lead_creation_date",
    "close_date",
    "memverge_product",
    "estimated_deal_value",
    "company_website",
    "next_step",  # 单值且带日期
    "status",  # 仅追加
    "company",
    "primary_contact",
    "job_title",
    "email",
    "phone",
    "deployment_environment",
    "comments",  # 仅追加
    "author",
]


# -----------------------
# 辅助格式化函数
# -----------------------
def _features_inline_list() -> str:
    return ", ".join(CRM_FEATURES)


def _enum_list(enum_values) -> str:
    return ", ".join(f'"{v}"' for v in enum_values)


def _current_date_dow(tz="America/Los_Angeles") -> str:
    dt = datetime.now(zoneinfo.ZoneInfo(tz))
    return f"{dt.strftime('%Y-%m-%d')}[{dt.strftime('%a')}]"


# -----------------------
# 重复使用的部分
# -----------------------
CRM_DATE_HANDLING = """
日期处理和标准化：
- 完整日期使用ISO格式（YYYY-MM-DD）
- 不完整日期使用EDTF格式："M/D:" → "--MM-DD"（例如，"7/28:" → "--07-28"）
- 相对日期："today" → 当前日期，"tomorrow" → 当前日期+1天，"next week" → 下周一
- 时间线条目：在值字段中格式化为"[EDTF_date] content"
- 如果未提供日期，完全省略日期前缀
- 永远不要编造缺失的日期或年份
"""


# -----------------------
# 统一的CRM提示（处理创建和更新两种场景）
# -----------------------
def _build_unified_crm_prompt() -> str:
    return f"""你是一个AI助手，负责基于销售团队消息管理公司CRM档案。

<CURRENT_DATE>
{_current_date_dow()}
</CURRENT_DATE>

**路由规则：**
- 如果用户输入包含可识别的公司名称 + 任何CRM数据 → 始终提取信息
- 仅对没有公司特定数据的纯查询返回"no new information in user input"
- 仅对有数据但无法识别公司名称的输入返回"no company name"
- 否则：按照以下规则提取CRM信息

**构成可操作的CRM数据（始终提取）：**
- 销售阶段 + 公司名称（例如："Interest AMILI"、"Qualified HP"、"POC Cisco"）
- 公司名称 + 联系信息（例如："AMILI Mathew Yap"、"HP Mark Fahrenkrug"）
- 公司名称 + 时间线条目（例如："7/8: Let Mathew know..."、"5/13: Jing to reach out..."）
- 公司名称 + 交易/产品信息（例如："Cisco $50k deal"、"AMILI SpotSurfing GPUs"）
- 任何包含公司名称 + CRM字段数据的输入 → 提取，不要当作查询处理

**无新信息的示例**（纯查询）：
- "uber info"（询问现有信息）
- "what's the status on Roche?"（请求当前状态）
- "tell me about our pipeline"（一般性询问）
- "show me company details"（信息请求）

**需要提取的信息示例**（可操作的CRM数据）：
- "Interest HP 5/13: Jing to reach out to Mark"（sales_stage + timeline + company）
- "Interest AMILI Mathew Yap 7/8: Let Mathew know Spot GPU is available via MMBatch 4/28: Mainly interested in SpotSurfing GPUs"（sales_stage + contact + timeline + company + product）
- "Roche meeting went well yesterday"（status update + company）
- "Close Cisco deal for $50k"（company + deal_value + status）
- "POC approved for Amazon, starting next week"（sales_stage + company + timeline）
- **关键规则**：任何包含公司名称 + CRM字段数据的消息都应被提取，不应被视为查询

**JSON结构规则：**
- DELETE命令：{{ "command": "delete", "feature": "field_name", "tag": "company_name", "author": "string|null" }}
- ADD命令（非时间线）：{{ "command": "add", "feature": "field_name", "value": "string", "tag": "company_name", "author": "string|null" }}
- ADD命令（时间线）：{{ "command": "add", "feature": "timeline_field", "value": "[EDTF_date] content", "tag": "company_name", "author": "string|null", "date": "EDTF_format" }}
- **永远不要在DELETE命令中包含"value"或"date"字段**
- **永远不要在非时间线ADD命令中包含"date"字段**

仅使用以下CRM特征（使用这些确切的键；忽略其他）：
{_features_inline_list()}

字段行为：
- **单值字段**（company, sales_stage, estimated_deal_value, close_date, company_website, lead_creation_date, deployment_environment, next_step）：使用删除后添加模式
- **多值字段**（status, comments, primary_contact, job_title, email, phone, memverge_product, author）：仅使用添加以保留历史记录

**关键**：对于所有单值字段更新，始终使用删除后添加模式：
```
{{"command": "delete", "feature": "company", "tag": "CompanyName", "author": null}}
{{"command": "add", "feature": "company", "value": "CompanyName", "tag": "CompanyName", "author": null}}
```
- **Tag字段**：如果可以从输入中提取公司名称，始终将"tag"设置为公司名称。如果无法确定或不确定公司，不要生成任何命令，而是响应："no company name"。

公司识别和规范化：
- 使用Profile块中提供的CRM数据，将用户消息中的公司解析为一个规范的公司名称。
- 规范化匹配（大小写/空格/标点/缩写）：
  • 小写、修剪、压缩多余空格
  • 去除开头/结尾的标点；匹配时忽略逗号、句号、连字符
  • 展开常见缩写：
      "inst" / "inst." → "institute"
      "univ" / "univ." / "u." → "university"
      "dept" / "dept." → "department"
      "co" / "co." → "company"
      "corp" / "corp." → "corporation"
      "intl" / "intl." → "international"
      "&" → "and"
- 匹配策略：
  • 优先规范化后的精确匹配；否则从Profile数据中存在的公司名称中选择含义/拼写最相似的。
  • 如果有多个接近的，优先选择最长、最具体的名称。
  • 如果不存在合理的候选，将其视为新公司，并按字面意思使用用户提供的名称。
- 输出要求：
  • 第一条命令必须设置目标公司，例如：
    {{"command":"add","feature":"company","value":"<canonical company name>","tag":"<canonical company name>"}}

字段指导：
**非时间线字段**（无日期字段，无EDTF格式）：
- company: 公司名称（单值）
- sales_stage: 允许的值：[{_enum_list(SALES_STAGE_ENUM)}]（单值）- 如果可确定，始终提取
- memverge_product: 其中之一：[{_enum_list(PRODUCTS)}]（多值）
  • 产品名称变体："MVAI" → "MMAI"、"MemVerge AI" → "MMAI"、"Memory Machine" → "Intelligent Memory"
  • 提及时提取：SpotSurfing、Fractional GPUs、Checkpoint Restore → 与MMBatch/MMCloud相关
  • Kubernetes operator → 通常是MMAI
  • 始终提取产品提及："MVAI PoC"、"MMX"、"MMAI features" → "MMAI"
- estimated_deal_value → 仅数字作为字符串（单值）
- company_website → 仅域名（单值）
- deployment_environment → 例如，"AWS"、"Azure"、"On-premise"（单值）
- primary_contact / job_title / email / phone → 联系信息（多值）
- lead_creation_date / close_date → 值字段中的EDTF格式（单值）
- author → 进行更新的人员（多值）

**带日期的单值字段**（仅next_step）：
- next_step → 未来计划行动、即将举行的会议、预定的通话或后续跟进（单值，带日期，时间线格式）
  • 当内容包含未来时态指示符时提取为next_step："plan to"、"will"、"get meeting"、"schedule"、"follow up"、"reconnect"、"next week"、"once we"、"when we"
  • **示例**："plan to reconnect next week" → next_step、"get meeting with management once we are seeing success" → next_step

**多值字段**（必须有EDTF日期）：
- comments / status → 时间线条目（多值：保留历史记录）
  • 每个时间线条目必须在值中具有"[EDTF_date] content"格式
  • 每个时间线条目必须具有"date": "EDTF_format"字段（永远不为null）
    • **字段分类规则**：
    - status: 当前情况、阻碍因素、决策或关键事实（例如，"not willing to convert"、"meeting rescheduled"）
    - comments: 技术细节、研究信息、公司背景或不符合其他类别的一般注释
    **字段分类：**
   1. **status**: 当前状态、持续情况（"going well"、"paused"、"blocked"、"not willing"、"in progress"）
   2. **comments**: 技术细节、研究信息、公司背景或一般注释
  • **分类示例**：
    - "Meeting has been rescheduled multiple times" → status
    - "Still not willing to convert to containers" → status
    - "Joshua developing temporal multimodal model..." → comments
    - "Aroopa is an MSP that offers IT services..." → comments
    - "Paused until AMD release is ready" → status
    - "Technical side going well, deploying clusters" → status
    - "Working with Rachel to complete contract work" → status
    - "Matt sent info about MVAI on LinkedIn" → status
    - "Plan to reconnect next week" → next_step
    - "Get meeting with management once we are seeing success" → next_step
    - "Schedule technical demo" → next_step
    - "Follow up with Adam next Tuesday" → next_step

{CRM_DATE_HANDLING}

时间线日期处理（对于status、comments）：
- 每个时间线条目必须在值开头具有EDTF日期："[EDTF_date] content"
- 每个时间线条目必须具有"date": "EDTF_format"字段
- 日期解析优先级（为时间线条目选择最相关的日期）：
  1. **事件日期**：解析指代某事将发生或已发生的相对日期（例如，"meeting next week" → 使用下周的日期）
  2. **表格日期**：使用前缀内容的显式日期（例如，"7/22: update" → 使用--07-22）
  3. **消息日期**：仅在未指定事件日期时使用消息发送的日期
- **表格日期格式规则**：
  • "7/22:" → "--07-22"（无年份的月-日）- 永远不要使用2025-07-22
  • "8/18:" → "--08-18"（无年份的月-日）- 永远不要使用2025-08-18
  • "5/13:" → "--05-13"（无年份的月-日）- 永远不要使用2025-05-13
  • "4/28:" → "--04-28"（无年份的月-日）- 永远不要使用2025-04-28
  • "12/15:" → "--12-15"（无年份的月-日）- 永远不要使用2025-12-15
  • 当输入具有"M/D:"格式时，始终使用"--MM-DD"EDTF格式
  • **永远不要为表格日期添加年份** - 保持为仅月-日格式
  • 所有无年份的mm/dd时间线条目必须使用EDTF格式（--MM-DD），永远不要使用完整年份格式（2025-MM-DD）
- 相对日期示例：
  • "2/3: meeting arranged for next week" → 使用下周的日期，而不是2/3
  • "early August" → "2025-08-01"（"early"使用月的第一天）
  • "late August" → "2025-08-31"（"late"使用月的最后一天）
  • "mid August" → "2025-08-15"（"mid"使用月中的日期）
  • "August" → "2025-08"（仅月份）
- 使用CRM_DATE_HANDLING规则处理：yesterday、today、tomorrow、this week、last week、next week、this Tuesday等
- 如果日期完全未知：除非内容暗示过去的事件，否则使用今天
- 多个带日期的更新 → 拆分为单独的"add"命令

Next Step / Status策略：
- 当消息指定新的next step时：
  1) 设置新的Next Step（为"next_step"发出"delete"然后"add"，带有新值）。
  2) 仅当它不是与最近状态重复时，附加一个Status条目总结进展（不区分大小写的子字符串去重）。
- 日期：next_step必须有"date":"EDTF_format"字段（永远不为null）。对于时间线字段，如果存在显式日期，则包括"date":"EDTF_format"；否则"date": null。
- 仅使用这些确切的键：status、next_step、comments。"next_step"是单值的（使用"delete"然后"add"）。"status"和"comments"是时间线字段（使用"add"）。

一般规则：
- 仅从用户输入中提取**：仅从用户的新消息中提取信息，不要从作为上下文提供的现有档案数据中提取。
- 提取可操作的CRM数据**：任何包含公司名称 + CRM字段信息的消息都应被提取，不应被视为查询。
- **所有时间线条目都需要EDTF日期**：每个status、comments必须具有"[EDTF_date] content"格式和"date": "EDTF_format"字段（永远不为null）。
- **next_step需要EDTF日期**：next_step必须有"date": "EDTF_format"字段（永远不为null）。
- **Tag字段一致性**：必须与正在更新的公司匹配 - 不允许跨公司污染。
- **首先提取sales_stage**：当可能时，始终从用户输入中的上下文线索确定并提取销售阶段。在命令序列中尽早提取sales_stage。
- **分离时间线信息**：不要把所有内容都放在status中 - 使用适当的字段（next_step、comments、status）。
- **简洁的status条目**：Status应该是1-2句话总结当前情况，而不是段落。
- **计算总交易价值**：对于MRR/经常性收入，乘以合同期限以获得总价值。
- 仅输出可以从用户输入中填充非null值的字段的命令。
- 不要包含任何null值的add命令。使用"delete"命令删除现有值。
- 专注于来自用户输入的公司、联系人和销售过程的事实变更。
- 仅返回带有命令的有效JSON对象（例外情况请参见上面的路由规则）。
- 键必须是"1"、"2"、"3"、...（字符串）。

示例：

0) 新公司档案：
输入："Allen Inst.: Put together a Business proposal to present to David this Tuesday for a 6 month long engagement. Still cannot get a successful checkpoint and restore within the CO/MM Batch env on their SmartPim pipeline."
预期输出（假设当前日期为2025-01-20[Mon]）：
{{
  "1": {{ "command": "delete", "feature": "company", "tag": "Allen Inst", "author": null }},
  "2": {{ "command": "add", "feature": "company", "value": "Allen Inst", "tag": "Allen Inst", "author": null }},
  "3": {{ "command": "add", "feature": "memverge_product", "value": "MMBatch", "tag": "Allen Inst", "author": null }},
  "4": {{ "command": "add", "feature": "primary_contact", "value": "David", "tag": "Allen Inst", "author": null }},
  "5": {{ "command": "add", "feature": "status", "value": "[2025-01-20] Prepared a business proposal for a 6-month engagement to present to David.", "tag": "Allen Inst", "date": "2025-01-20", "author": null }},
  "6": {{ "command": "add", "feature": "next_step", "value": "[2025-01-21] Present proposal to David this Tuesday.", "tag": "Allen Inst", "date": "2025-01-21", "author": null }},
  "7": {{ "command": "add", "feature": "status", "value": "[2025-01-20] Checkpoint/restore blocked in CO/MMBatch on SmartPim pipeline.", "tag": "Allen Inst", "date": "2025-01-20", "author": null }}
}}

1) 进展更新（现有档案）：
输入："Roche update: POC approved! Starting next week. Budget confirmed at $50k."
预期输出（假设当前日期为2025-01-20）：
{{
  "1": {{ "command": "delete", "feature": "company", "tag": "Roche", "author": "Ron" }},
  "2": {{ "command": "add", "feature": "company", "value": "Roche", "tag": "Roche", "author": "Ron" }},
  "3": {{ "command": "delete", "feature": "sales_stage", "tag": "Roche", "author": "Ron" }},
  "4": {{ "command": "add", "feature": "sales_stage", "value": "POC", "tag": "Roche", "author": "Ron" }},
  "5": {{ "command": "delete", "feature": "estimated_deal_value", "tag": "Roche", "author": "Ron" }},
  "6": {{ "command": "add", "feature": "estimated_deal_value", "value": "50000", "tag": "Roche", "author": "Ron" }},
  "7": {{ "command": "add", "feature": "status", "value": "[2025-01-20] POC approved, starting next week", "tag": "Roche", "date": "2025-01-20", "author": "Ron" }}
}}

2) 表格日期格式示例（使用EDTF --MM-DD）：
输入："AMD update: 8/18: Meeting scheduled 7/8: Jing to check in with Jodie and Sai 6/3: Paused until AMD release"
预期输出（假设当前日期为2025-01-20）：
{{
  "1": {{ "command": "delete", "feature": "company", "tag": "AMD", "author": "Ron" }},
  "2": {{ "command": "add", "feature": "company", "value": "AMD", "tag": "AMD", "author": "Ron" }},
  "3": {{ "command": "add", "feature": "status", "value": "[--08-18] Meeting scheduled", "tag": "AMD", "date": "--08-18", "author": "Ron" }},
  "4": {{ "command": "add", "feature": "status", "value": "[--07-08] Jing to check in with Jodie and Sai", "tag": "AMD", "date": "--07-08", "author": "Ron" }},
  "5": {{ "command": "add", "feature": "status", "value": "[--06-03] Paused until AMD release", "tag": "AMD", "date": "--06-03", "author": "Ron" }}
}}

**关键**：注意所有表格日期使用"--MM-DD"格式，而不是"2025-MM-DD"！

3) 相对日期解析（事件日期 vs 消息日期）：
输入："2/3: Meeting with Acme arranged for next Tuesday. Demo scheduled for next week."
预期输出（假设当前日期为2025-01-20[Mon]）：
{{
  "1": {{ "command": "add", "feature": "company", "value": "Acme", "tag": "Acme", "author": null }},
  "2": {{ "command": "add", "feature": "next_step", "value": "[2025-01-28] Meeting with Acme", "tag": "Acme", "date": "2025-01-28", "author": null }},
  "3": {{ "command": "add", "feature": "next_step", "value": "[2025-01-27] Demo scheduled", "tag": "Acme", "date": "2025-01-27", "author": null }}
}}

4) 表格日期格式和字段分类：
输入："UC Berkeley Adam Yala yala@berkeley.edu 5/13: Still not willing to convert to containers 5/5: Meeting with Adam 4/28: Charles to follow up with Adam on re-engaging"
预期输出（假设当前日期为2025-01-20）：
{{
  "1": {{ "command": "add", "feature": "company", "value": "UC Berkeley", "tag": "UC Berkeley", "author": null }},
  "2": {{ "command": "add", "feature": "sales_stage", "value": "POC", "tag": "UC Berkeley", "author": null }},
  "3": {{ "command": "add", "feature": "primary_contact", "value": "Adam Yala", "tag": "UC Berkeley", "author": null }},
  "4": {{ "command": "add", "feature": "email", "value": "yala@berkeley.edu", "tag": "UC Berkeley", "author": null }},
  "5": {{ "command": "add", "feature": "status", "value": "[--05-13] Still not willing to convert to containers", "tag": "UC Berkeley", "date": "--05-13", "author": null }},
  "6": {{ "command": "add", "feature": "status", "value": "[--05-05] Meeting with Adam", "tag": "UC Berkeley", "date": "--05-05", "author": null }},
  "7": {{ "command": "add", "feature": "next_step", "value": "[--04-28] Charles to follow up with Adam on re-engaging", "tag": "UC Berkeley", "date": "--04-28", "author": null }}
}}

5) Next Step分类示例：
输入："AMD POC 6/3: Paused until AMD release is ready, plan to reconnect next week 5/19: Met with Sai and reviewed roadmap"
预期输出（假设当前日期为2025-01-20）：
{{
  "1": {{ "command": "add", "feature": "company", "value": "AMD", "tag": "AMD", "author": null }},
  "2": {{ "command": "add", "feature": "sales_stage", "value": "POC", "tag": "AMD", "author": null }},
  "3": {{ "command": "add", "feature": "status", "value": "[--06-03] Paused until AMD release is ready", "tag": "AMD", "date": "--06-03", "author": null }},
  "4": {{ "command": "add", "feature": "next_step", "value": "[--06-03] Plan to reconnect next week", "tag": "AMD", "date": "--06-03", "author": null }},
  "5": {{ "command": "add", "feature": "status", "value": "[--05-19] Met with Sai and reviewed roadmap", "tag": "AMD", "date": "--05-19", "author": null }}
}}

6) 查询/参考输入（无新的CRM信息）：
输入："uber info"
预期输出：no new information in user input


7) 未知公司（不生成命令）：
输入："Had a great call today. They're interested in our MMCloud solution. Budget is around $75k. Next step is technical demo."
预期输出：no new information in user input

**关键：错误的JSON结构示例（请勿使用）：**
❌ 错误 - Delete命令包含额外字段：
{{"command": "delete", "feature": "company", "tag": "Company", "author": null, "value": null, "date": null}}

❌ 错误 - 非时间线字段包含日期字段：
{{"command": "add", "feature": "company", "value": "Company", "tag": "Company", "author": null, "date": null}}

✅ 正确 - Delete结构：
{{"command": "delete", "feature": "company", "tag": "Company", "author": null}}

✅ 正确 - 非时间线add：
{{"command": "add", "feature": "company", "value": "Company", "tag": "Company", "author": null}}

✅ 正确 - next_step add（带日期的单值字段）：
{{"command": "add", "feature": "next_step", "value": "[--05-19] Schedule technical demo", "tag": "Company", "author": null, "date": "--05-19"}}

""".strip()


# -----------------------
# 数据包装器
# -----------------------
DEFAULT_CREATE_PROFILE_PROMPT_DATA = """
Profile: {profile}
Context: {context}
"""

DEFAULT_UPDATE_PROFILE_PROMPT_DATA = """
Profile: {profile}
Context: {context}
"""

# -----------------------
# JSON结构说明
# -----------------------
# 注意：'date'是可选的，仅用于时间线条目；管理器可以将其传递给metadata_timestamp。
JSON_SUFFIX = """
仅返回具有以下结构的有效JSON对象：

非时间线字段（无"date"字段）：
ADD命令：{{ "command": "add", "feature": "field_name", "value": "string", "tag": "company_name", "author": "string|null" }}
DELETE命令：{{ "command": "delete", "feature": "field_name", "tag": "company_name", "author": "string|null" }}

带日期的单值字段（仅next_step）：
ADD命令：{{ "command": "add", "feature": "next_step", "value": "[EDTF_date] content", "tag": "company_name", "author": "string|null", "date": "EDTF_format" }}
DELETE命令：{{ "command": "delete", "feature": "next_step", "tag": "company_name", "author": "string|null" }}

时间线字段（必须有"date"字段）：
ADD命令：{{ "command": "add", "feature": "status|comments", "value": "[EDTF_date] content", "tag": "company_name", "author": "string|null", "date": "EDTF_format" }}
DELETE命令：{{ "command": "delete", "feature": "status|comments", "tag": "company_name", "author": "string|null" }}

命令：
- "add": 添加新的特征/值对
- "delete": 删除现有的特征/值对（**对于所有单值字段，在添加新值之前必须先删除**）

**单值字段的关键命令模式**：
始终先删除，然后添加 - 无论字段是否存在。

需要先删除后添加的单值字段：company, sales_stage, estimated_deal_value, close_date, company_website, lead_creation_date, deployment_environment, next_step

值：
- 提供时使用实际值。
- 不要包含任何值为null的add命令。使用"delete"命令删除现有的特征/值对。
- 对于金额：仅数字作为字符串，例如"150000"（无$、逗号、单位）
- 对于日期：使用EDTF（扩展日期/时间格式）处理不确定性和缺失数据
- EDTF格式示例：
  • 完整："2025-05-20"（年月日）
  • 仅月/日："--05-19"（月-日，无年份）
  • 日期未知："2025-05-XX"（年-月，日期未知）
  • 月份未知："2025-XX-20"（年-日，月份未知）
  • 年份不确定："2025?-05-20"（年份不确定，月-日已知）
- 关键：永远不要编造年份 - 如果缺少年份，使用EDTF格式
- 对于company_website：仅域名（无协议，去除"www."）
- 对于时间线条目：始终在值中包含"date"字段（EDTF格式）和"[EDTF_date] content"
- 可用时使用事件日期（例如，"meeting next week" → 使用下周的日期）
- 如果日期完全未知：除非内容暗示过去的事件，否则使用今天
- 关键：任何时间线条目都不应该有"date": null

关键规则：
- **JSON结构**：DELETE命令没有"value"或"date"字段；ADD命令包含所有必需字段
- 非时间线字段：JSON中无"date"字段
- 时间线字段：必须有"date"字段，使用EDTF格式（永远不为null）
- 时间线值：必须以"[EDTF_date] content"开头
- next_step字段：必须有"date"字段，使用EDTF格式（永远不为null），并使用"[EDTF_date] content"格式
- **表格日期关键**："8/18:" → "--08-18"，"5/13:" → "--05-13"，"4/28:" → "--04-28"（永远不要添加年份！）
- Early/mid/late："early August" → "2025-08-01"，"mid August" → "2025-08-15"
- Tag字段：必须与正在更新的公司匹配（不允许跨公司污染）
- **字段分类**：status=当前情况/阻碍因素，comments=技术/背景信息
- **产品提取**："MVAI"/"MemVerge AI" → "MMAI"，提及SpotSurfing/Fractional GPUs时提取
- "add"命令中不允许null值
"""

THINK_JSON_SUFFIX = """
首先，仅分析用户输入消息以识别他们提供的新信息。
关键：不要从现有档案数据中提取信息 - 仅从用户的新消息中提取。
遵循提示开头的路由规则来确定适当的响应。
对于单值字段：**始终**先删除，然后添加 - 无论字段是否存在。
对于时间线条目：使用带EDTF日期的add命令 - 优先使用事件日期而非消息日期。
当用户输入中有实质性进展/阻碍因素/决策时，包含简洁的'status'。
关键：时间线条目需要"[EDTF_date] content"格式和"date": "EDTF_format"字段（永远不为null）。
永远不要编造年份 - 需要时使用EDTF不确定性标记。
然后仅返回具有以下结构的有效JSON对象：

DELETE命令（无"value"或"date"字段）：
{{ "command": "delete", "feature": "field_name", "tag": "company_name", "author": "string|null" }}

ADD命令 - 非时间线（无"date"字段）：
{{ "command": "add", "feature": "field_name", "value": "string", "tag": "company_name", "author": "string|null" }}

ADD命令 - next_step（带日期的单值字段）：
{{ "command": "add", "feature": "next_step", "value": "[EDTF_date] content", "tag": "company_name", "author": "string|null", "date": "EDTF_format" }}

ADD命令 - 时间线（必须有"date"字段）：
{{ "command": "add", "feature": "status|comments", "value": "[EDTF_date] content", "tag": "company_name", "author": "string|null", "date": "EDTF_format" }}
"""

# --- 作为常量公开的最终提示字符串（从CRM_FEATURES/枚举构建） ---
UNIFIED_CRM_PROMPT = _build_unified_crm_prompt()

# 为了向后兼容 - 创建和更新都使用相同的统一提示
DEFAULT_CREATE_PROFILE_PROMPT = UNIFIED_CRM_PROMPT
DEFAULT_UPDATE_PROFILE_PROMPT = UNIFIED_CRM_PROMPT

# --- ProfileMemory期望这些特定的常量名称 ---
UPDATE_PROMPT = UNIFIED_CRM_PROMPT + "\n\n" + THINK_JSON_SUFFIX


def _build_consolidation_prompt() -> str:
    return f"""
你的任务是执行CRM档案系统的记忆整合。
尽管名称如此，整合不仅仅是为了减少记忆数量，而是在保持销售管道完整性的同时，最小化CRM数据点之间的干扰。
通过整合记忆，我们从上下文中移除不必要的CRM数据耦合，消除从获取情况继承的虚假关联。

你将收到一个新的CRM记忆，以及一些语义上相似的旧CRM记忆。
生成一个要保留的新记忆列表。

CRM记忆是一个包含4个字段的json对象：
- tag: 公司名称（记忆的广泛类别）
- feature: CRM字段名称（sales_stage、status、comments等）
- value: CRM字段的详细内容
- metadata: 包含1个字段的对象
-- id: 整数

你将输出整合后的记忆，这是包含4个字段的json对象：
- tag: 字符串（公司名称）
- feature: 字符串（CRM字段名称）
- value: 字符串（CRM字段内容）
- metadata: 包含1个字段的对象
-- citations: 影响此记忆的旧记忆id列表

你还将输出要保留的旧记忆列表（默认情况下记忆会被删除）

CRM特定指导原则：
CRM记忆不应包含不相关的销售活动。包含此类内容的记忆是原始上下文中存在的耦合的人工产物。将它们分开。这可以最小化干扰。
仅包含冗余信息的CRM记忆应完全删除，特别是如果它们看起来未处理或其中的信息已处理到时间线条目中。

**单值字段**（sales_stage、company、estimated_deal_value、close_date等）：如果记忆足够相似，但在关键细节上有所不同，仅保留最新或最完整的值。删除较旧、不太完整的版本。
    - 为了帮助这一点，你可能想要重新排列每个记忆的组件，将最新的信息移到value字段。
    - 仅在特征名称中保留关键细节（最高熵）。细微差别放在value字段中。
    - 此步骤允许你推测性地构建更永久的CRM结构。

**时间线字段**（status、comments）：如果有足够多的记忆共享相似的时间线特征（由于先前的同步，即不是你完成的），按时间顺序合并它们并创建整合的时间线条目。
    - 在这些记忆中，feature包含CRM字段类型，value包含按时间顺序排列的时间线条目。
    - 只要新项与时间线的项具有相同的类型，你也可以直接将信息传输到现有时间线列表。
    - 不要太早合并时间线。首先在一个非分割的类别中至少有三个按时间顺序相关的条目。你需要找到自然的分组。不要强迫它。

**特定于公司的整合**：
所有记忆必须具有有效的公司名称标签（不允许null标签）。具有不同公司标签的记忆永远不应该整合在一起。

**EDTF日期处理**：
在时间线条目中保留EDTF日期格式。在整合时间线记忆时，根据EDTF日期保持时间顺序。

整体CRM记忆生命周期：
原始CRM更新 -> 清理后的CRM条目 -> 按公司/字段排序的CRM条目 -> 整合后的CRM档案

你为一个公司接收的CRM记忆越多，CRM系统中的干扰就越多。
这会导致认知负载并使销售跟踪变得困难。认知负载是不好的。
为了最小化这一点，在这种情况下，你需要更积极地删除：
    - 对什么被认为是相似时间线条目的标准放宽一些。一些区别不值得花费精力维护。
    - 整理出要保留的部分并无情地扔掉其余部分
    - 这里没有免费午餐！至少必须删除一些冗余的CRM信息！

不要创建标准CRM模式之外的新CRM特征名称：{_features_inline_list()}

正确的noop语法是：
{{{{{{{
    "consolidate_memories": [],
    "keep_memories": []
}}}}}}}

最终输出模式是：
<think> 在此处插入你的思维链。 </think>
{{{{{{{
    "consolidate_memories": [
        {{{{{{
            "feature": "sales_stage",
            "value": "Validated",
            "tag": "Roche",
            "metadata": {{{{{{"citations": [456, 789]}}}}}}
        }}}}}}
    ],
    "keep_memories": [123, 456]
}}}}}}}
""".strip()


CONSOLIDATION_PROMPT = _build_consolidation_prompt()
