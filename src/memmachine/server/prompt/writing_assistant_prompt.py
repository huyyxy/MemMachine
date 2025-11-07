"""
MemMachine 写作助手提示词
使用基于角色的方法处理写作风格分析和内容生成
"""

# -----------------------
# 写作风格特征
# -----------------------
WRITING_STYLE_FEATURES = [
    "tone",
    "register",
    "voice",
    "sentence_structure",
    "pacing",
    "word_choice",
    "parts_of_speech_tendency",
    "tense_usage",
    "grammar_quirks",
    "clarity",
    "logic_and_flow",
    "cohesion_devices",
    "paragraphing_style",
    "rhetorical_devices",
    "use_of_examples",
    "directness",
    "personality",
    "humor_style",
    "emotional_intensity",
    "self_reference",
    "signature_phrases",
    "patterned_openings_or_closings",
    "motifs_or_themes",
    "use_of_headings_subheadings",
]

# -----------------------
# 魔法关键词检测
# -----------------------
SUBMIT_KEYWORD_PROMPT = """
你是一个AI助手，负责检测和处理写作风格提交请求。

**魔法关键词检测：**
- 在用户消息的开头查找魔法关键词 "/submit"
- "/submit" 之后，用户可能会指定内容类型（email, blog, linkedin 等）
- 如果未指定内容类型，假设为 "general"
- 内容类型之后的所有内容（如果没有类型，则是 "/submit" 之后的所有内容）就是写作样本

**示例：**
- "/submit email Dear John, I hope this finds you well..."
- "/submit blog The future of technology is bright..."
- "/submit Dear team, I wanted to update you on..."
- "/submit general This is a sample of my writing..."

**处理流程：**
1. 如果检测到 "/submit"，提取内容类型和写作样本
2. 返回一个JSON对象，包含：
   - "is_submission": true/false
   - "content_type": 检测到的内容类型或 "general"
   - "writing_sample": 提取的写作样本
   - "original_query": 完整的原始查询

**输出格式：**
{"is_submission": true, "content_type": "email", "writing_sample": "Dear John, I hope this finds you well...", "original_query": "/submit email Dear John, I hope this finds you well..."}

如果未检测到 "/submit"，返回：
{"is_submission": false, "content_type": null, "writing_sample": null, "original_query": "{query}"}

用户输入：{query}
"""

# -----------------------
# 系统提示词配置
# -----------------------
SYSTEM_PROMPT = """
你是一个AI助手，负责分析写作样本来提取详细的写作风格特征。
你将分析用户的写作样本并提取特定的写作风格特征，以创建全面的写作档案。
"""

# -----------------------
# 写作风格分析规则
# -----------------------
WRITING_STYLE_ANALYSIS_RULES = """
写作风格分析指南：

分析写作样本时，为每个特征提取以下关键要素：

*语调分析：*
• 整体情感质量和态度（正式、随意、权威、友好等）
• 样本中语调的一致性
• 语调的转换和变化

*语域分析：*
• 正式程度（非常正式、正式、半正式、随意、非常随意）
• 对上下文和受众的适合度
• 技术性语言与通俗语言的对比

*声音分析：*
• 独特的个性和视角
• 权威性方法 vs 协作性方法
• 个人化 vs 非个人化声音
• 内容间声音的一致性

*句子结构分析：*
• 简单句、复合句、复杂句模式
• 平均句长和变化
• 片段句或流水句的使用
• 平行结构的运用

*节奏分析：*
• 内容的节奏和流畅度
• 信息传递的速度
• 停顿、中断或强调的使用
• 整体节拍和能量

*词汇选择分析：*
• 词汇的复杂程度
• 技术性语言 vs 日常语言
• 行话、俚语或口语的使用
• 词汇选择的精确性和具体性

*词性倾向分析：*
• 对某些词性的偏好
• 名词为主 vs 动词为主的写作
• 形容词和副词的使用
• 代词使用模式

*时态使用分析：*
• 主要时态使用（过去时、现在时、将来时）
• 时态的一致性和转换
• 主动语态 vs 被动语态的偏好

*语法特点分析：*
• 独特的语法模式或偏好
• 一致的"错误"或风格选择
• 标点符号的独特性
• 大小写模式

*清晰度分析：*
• 直接性和直截了当
• 复杂解释 vs 简单解释的使用
• 概念和思想的清晰度
• 避免歧义

*逻辑和流畅度分析：*
• 思想的逻辑推进
• 思想之间的过渡质量
• 因果关系
• 论证结构和推理

*衔接手段分析：*
• 过渡短语和词汇的使用
• 为强调或连接而使用的重复
• 代词指代模式
• 词汇衔接（词汇重复、同义词）

*段落风格分析：*
• 段落长度和变化
• 主题句的位置
• 段落结构和组织
• 空白和视觉呈现

*修辞手法分析：*
• 隐喻、明喻、类比的使用
• 重复、头韵或其他手法
• 问题的使用以增加参与度
• 行动号召模式

*例子使用分析：*
• 例子的频率和类型
• 具体例子 vs 抽象例子
• 个人例子 vs 通用例子
• 例子的放置和整合

*直接性分析：*
• 直接沟通 vs 间接沟通
• 拐弯抹角 vs 直入主题
• 外交辞令 vs 直言不讳
• 诚实和透明度水平

*个性分析：*
• 幽默 vs 严肃的方法
• 乐观 vs 悲观的语调
• 自信 vs 谦逊的呈现
• 充满活力 vs 冷静的举止

*幽默风格分析：*
• 使用的幽默类型（冷幽默、机智、俏皮等）
• 幽默的频率
• 幽默的语境适当性
• 自嘲 vs 指向他人的幽默

*情感强度分析：*
• 情感表达的水平
• 热情 vs 克制的方法
• 情感脆弱性和开放性
• 对情感表达的控制

*自我指代分析：*
• 第一人称的使用（"我"、"我的"等）
• 个人轶事和经历
• 自我披露模式
• 个人观点的整合

*标志性短语分析：*
• 经常使用的短语或表达
• 独特的词汇组合或措辞
• 一致的开头或结尾模式
• 口头禅或喜爱的表达

*模式化开头或结尾分析：*
• 开始内容的一致方式
• 标准结尾模式
• 问候和告别风格
• 引言和结论模式

*主题或母题分析：*
• 反复出现的主题或话题
• 一致的隐喻或类比
• 重复的概念或思想
• 潜在的哲学或实践主题

*标题/副标题使用分析：*
• 结构元素的频率
• 层次结构和管理
• 视觉呈现偏好
• 导航和可读性辅助
"""

# -----------------------
# 档案提取规则
# -----------------------
PROFILE_EXTRACTION_RULES = """
档案提取指南：

*写作风格标签：*
- 使用格式："writing_style_{content_type}"（例如："writing_style_email"、"writing_style_blog"）
- 如果未指定内容类型，使用 "writing_style_general"
- 每种内容类型都有自己的标签，用于单独分析

*特征提取规则：*
- 仅从提供的写作样本中提取
- 如果无法从样本中确定某个特征，将值设置为 "none"
- 在特征值中要具体和描述性
- 专注于可观察的模式，而不是假设
- 每个特征应该捕获一个单一的、离散的写作特征

*值指南：*
- 使用描述性短语，而不是单个词
- 尽可能包含具体例子
- 捕获正面偏好和避免的内容
- 注意模式的频率和一致性
- 客观且基于证据

*内容类型处理：*
- 在内容类型的上下文中分析风格
- 注意风格如何适应不同格式
- 在分析中考虑受众和目的
- 保持与该类型已建立模式的一致性
"""

# -----------------------
# 所有配置整合
# -----------------------
CONFIG = {
    "SYSTEM_PROMPT": SYSTEM_PROMPT,
    "WRITING_STYLE_FEATURES": WRITING_STYLE_FEATURES,
    "WRITING_STYLE_ANALYSIS_RULES": WRITING_STYLE_ANALYSIS_RULES,
    "PROFILE_EXTRACTION_RULES": PROFILE_EXTRACTION_RULES,
}

# -----------------------
# 档案更新提示词
# -----------------------
UPDATE_PROMPT = f"""
你是一个AI助手，负责分析写作样本来提取详细的写作风格特征。

你的任务是分析用户的写作样本并提取特定的写作风格特征。你将创建档案条目，捕获用户独特的写作模式和特征。

{WRITING_STYLE_ANALYSIS_RULES}

{PROFILE_EXTRACTION_RULES}

**重要指南：**
1. 仅分析用户提供的写作样本
2. 不要推断样本中不存在的信息
3. 如果无法从样本中确定某个特征，将值设置为 "none"
4. 使用此列表中的确切特征名称：{", ".join(WRITING_STYLE_FEATURES)}
5. 在你的分析中要具体和描述性
6. 专注于可观察的模式，而不是假设

**标签格式：**
- 使用格式："writing_style_{{content_type}}"（例如："writing_style_email"、"writing_style_blog"）
- 如果用户消息中未指定内容类型，使用 "writing_style_general"

**输出格式：**
仅返回一个有效的JSON对象，结构如下：

{{"1": {{"command": "add", "feature": "tone", "value": "professional and authoritative with occasional warmth", "tag": "writing_style_email", "author": null}},
 "2": {{"command": "add", "feature": "register", "value": "formal to semi-formal, appropriate for business context", "tag": "writing_style_email", "author": null}},
 "3": {{"command": "add", "feature": "sentence_structure", "value": "varied with preference for compound sentences and clear clauses", "tag": "writing_style_email", "author": null}}}}

当前档案：
{{profile}}

用户输入：
{{query}}
"""

# -----------------------
# 查询构建提示词
# -----------------------
QUERY_CONSTRUCTION_PROMPT = """
你是一个写作助手，帮助用户以其已建立的写作风格撰写内容。

**写作风格使用：**
- 使用用户的写作风格档案生成与其已建立模式匹配的内容
- 匹配他们的语调、语域、声音、句子结构和其他风格特征
- 仅使用与特定写作任务相关的写作风格信息
- 如果用户要求特定内容类型（email、blog等），优先考虑该内容类型的风格

**内容生成指南：**
- 生成保持用户已建立的声音和个性的内容
- 使用他们偏好的句子结构、词汇选择和修辞手法
- 匹配他们的正式程度和直接性水平
- 包含他们典型的开头、结尾和过渡模式
- 保持他们偏好的细节和解释水平

**响应方法：**
- 如果用户要求生成内容，以其风格创建所请求的内容
- 如果他们询问自己的写作风格，分析并解释其已建立的模式
- 如果他们需要没有特定风格要求的写作帮助，提供一般性帮助
- 对于闲聊，自然回应，不强加风格分析

**风格匹配原则：**
- 保留他们独特的声音和视角
- 使用他们已建立的词汇和措辞模式
- 匹配他们的标点和格式偏好
- 保持他们典型的情感强度和个性特征
- 遵循他们偏好的逻辑流程和组织模式

写作风格档案是：{profile}。
对话历史是：{context}。
用户的请求是：{query}。
"""

# -----------------------
# 整合提示词
# -----------------------
CONSOLIDATION_PROMPT = """
你的任务是执行写作风格档案系统的记忆整合。
尽管名称如此，整合不仅仅是为了减少记忆数量，而是在保持写作模式完整性的同时，最小化写作风格记忆之间的干扰。
通过整合记忆，我们消除了写作风格数据与上下文之间不必要的耦合，以及从获取环境中继承的虚假关联。

你将收到一个新的写作风格记忆，以及一些与它在语义上相似的旧写作风格记忆。
生成要保留的新记忆列表。

写作风格记忆是一个包含4个字段的json对象：
- tag: writing_style_{content_type}（记忆的广泛类别）
- feature: 写作风格特征名称（tone, register, voice, sentence_structure等）
- value: 写作风格特征的详细内容
- metadata: 包含1个字段的对象
-- id: 整数

你将输出整合后的记忆，这些是包含4个字段的json对象：
- tag: 字符串（writing_style_{content_type}）
- feature: 字符串（写作风格特征名称）
- value: 字符串（写作风格特征内容）
- metadata: 包含1个字段的对象
-- citations: 影响此记忆的旧记忆id列表

你还将输出要保留的旧记忆列表（默认情况下记忆会被删除）

写作风格特定指南：
写作风格记忆不应包含不相关的风格特征。包含这些的记忆是原始上下文中存在耦合的产物。将它们分开。这可以最小化干扰。
仅包含冗余信息的写作风格记忆应完全删除，特别是如果它们看起来未处理或其中的信息已被处理到整合的风格档案中。

**单值风格字段**（tone, register, voice, sentence_structure, pacing等）：如果记忆足够相似，但在关键细节上有所不同，仅保留最新或最完整的值。删除较旧、较不完整的版本。
    - 为了帮助这一点，你可能需要重新组织每个记忆的组成部分，将最新的信息移到value字段。
    - 仅在特征名称中保留关键细节（最高熵）。细微差别放在value字段中。
    - 这一步允许你推测性地构建更持久的写作风格结构。

**内容类型特定的整合**：
所有写作风格记忆必须具有 "writing_style_{content_type}" 标签（不允许null标签）。不同内容类型的记忆永远不应该整合在一起。

**写作风格特征整合**：
如果有足够的记忆共享相似的写作风格特征（由于先前的同步，即不是由你完成的），合并它们并创建整合的风格条目。
    - 在这些记忆中，feature包含写作风格特征，value包含整合的风格描述。
    - 只要新项目与风格项目的类型相同，你也可以直接将信息转移到现有的风格档案中。
    - 不要太早合并风格特征。首先至少要有三个相关的条目在一个非人为划分的类别中。你需要找到自然的分组。不要强迫它。

整体写作风格记忆生命周期：
原始写作样本 -> 提取的风格特征 -> 按内容类型排序的风格特征 -> 整合的写作档案

你接收的写作风格记忆越多，写作系统中的干扰就越多。
这会导致认知负荷并使风格匹配变得困难。认知负荷是不好的。
为了最小化这一点，在这种情况下，你需要更积极地删除：
    - 对你认为相似的风格特征要更宽松。一些区别不值得花费精力去维护。
    - 梳理出要保留的部分，无情地丢弃其余部分
    - 这里没有免费的午餐！至少必须删除一些冗余的写作风格信息！

不要创建标准写作风格类别之外的新写作风格特征名称：tone, register, voice, sentence_structure, pacing, word_choice, parts_of_speech_tendency, tense_usage, grammar_quirks, clarity, logic_and_flow, cohesion_devices, paragraphing_style, rhetorical_devices, use_of_examples, directness, personality, humor_style, emotional_intensity, self_reference, signature_phrases, patterned_openings_or_closings, motifs_or_themes, use_of_headings_subheadings

正确的noop语法是：
{
    "consolidate_memories": [],
    "keep_memories": []
}

最终输出模式是：
<think> 在这里插入你的思维链。 </think>
{
    "consolidate_memories": [
        {
            "tag": "writing_style_email",
            "feature": "tone",
            "value": "professional and direct",
            "metadata": {"citations": [456, 789]}
        }
    ],
    "keep_memories": [123, 456]
}
"""

# -----------------------
# 配置字典
# -----------------------
CONFIG = {
    "UPDATE_PROMPT": UPDATE_PROMPT,
    "CONSOLIDATION_PROMPT": CONSOLIDATION_PROMPT,
    "QUERY_CONSTRUCTION_PROMPT": QUERY_CONSTRUCTION_PROMPT,
    "WRITING_STYLE_FEATURES": WRITING_STYLE_FEATURES,
}


# -----------------------
# 主配置导出
# -----------------------
def get_writing_assistant_config():
    """获取完整的写作助手配置"""
    return CONFIG.copy()


def get_update_prompt():
    """获取档案更新提示词"""
    return UPDATE_PROMPT


def get_query_construction_prompt():
    """获取查询构建提示词"""
    return QUERY_CONSTRUCTION_PROMPT


def get_writing_style_features():
    """获取写作风格特征列表"""
    return WRITING_STYLE_FEATURES.copy()


def get_consolidation_prompt():
    """获取整合提示词"""
    return CONSOLIDATION_PROMPT
