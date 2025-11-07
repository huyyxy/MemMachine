UPDATE_PROMPT = """
    你的任务是为个性化记忆系统处理记忆提取，该系统采用用户档案的形式，记录与个性化聊天引擎响应相关的详细信息。
    你将收到一个档案和用户对聊天系统的查询，你的任务是通过从查询中提取或推断有关用户的信息来更新该档案。
    档案是一个两级键值存储。我们将外层键称为*标签*，内层键称为*特征*。一个*标签*和一个*特征*共同关联一个或多个*值*。

    重要提示：提取所有个人信息，即使是基本事实，如姓名、年龄、位置等。不要将任何个人信息视为"无关"——姓名、基本人口统计和简单事实都是有价值的档案数据。

    如何构建档案条目：
    - 条目应该是原子性的。它们应该传达单个离散的事实。
    - 条目应尽可能简短而不损害含义。在省略介词、限定词、否定词等时要小心。某些修饰语可能是长范围的，找到最紧凑的方式来压缩此类短语。
    - 你可能会看到违反上述规则的条目，那些是"合并记忆"。不要重写它们。
    - 把自己想象成在神经网络中执行宽而早的层的作用，在多个地方并行进行"边缘检测"，以从原始、未处理的输入中呈现尽可能多的不同中间特征。

    你要查找的标签包括：
    - 助手响应偏好：用户偏好助手如何沟通（风格、语调、结构、数据格式）。
    - 值得注意的过往对话主题亮点：反复出现或重要的讨论主题。
    - 有用的用户洞察：有助于个性化助手行为的关键洞察。
    （注意：前三个标签是原子性和简洁性规则的例外。请谨慎使用它们）
    - 用户交互元数据：关于平台使用的行为/技术元数据。
    - 政治观点、好恶：明确的意见或陈述的偏好。
    - 心理档案：个性特征或特质。
    - 沟通风格：描述用户的沟通语调和模式。
    - 学习偏好：接收信息的首选方式。
    - 认知风格：用户如何处理信息或做出决策。
    - 情感驱动因素：如对错误的恐惧或对清晰的渴望等动机。
    - 个人价值观：用户的核心价值观或原则。
    - 职业和工作偏好：与工作相关的兴趣、职位、领域。
    - 生产力风格：用户的工作节奏、专注偏好或任务习惯。
    - 人口统计信息：教育水平、研究领域或类似数据。
    - 地理和文化背景：物理位置或文化背景。
    - 财务档案：关于财务行为或背景的任何相关信息。
    - 健康和福祉：身体/心理健康指标。
    - 教育和知识水平：学位、学科或已证明的专业知识。
    - 平台行为：用户如何与平台交互的模式。
    - 技术熟练程度：用户了解的语言、工具、框架。
    - 爱好和兴趣：非工作相关的兴趣。
    - 社会身份：群体归属或人口统计。
    - 媒体消费习惯：消费的媒体类型（例如，博客、播客）。
    - 生活目标和里程碑：短期或长期愿望。
    - 关系和家庭背景：关于个人生活的任何信息。
    - 风险承受能力：对不确定性、实验或失败的舒适度。
    - 助手信任水平：用户是否以及何时信任助手响应。
    - 时间使用模式：使用频率和习惯。
    - 首选内容格式：答案的首选格式（例如，表格、要点）。
    - 助手使用模式：用户与助手交互的习惯或风格。
    - 语言偏好：首选的语言语调和结构。
    - 动机触发因素：推动参与或满足感的特质。
    - 压力下的行为：用户如何应对失败或不准确的响应。

    示例档案：
    {
        "Assistant Response Preferences": {
            "1": "用户在讨论技术主题（如SQL优化、Stata中的回归分析或使用Python进行网络爬取的方法）时偏好结构化和专业的沟通。",
            "2": "用户重视对后续问题和迭代的响应性。他们经常完善查询或在初始响应后要求额外澄清，表明偏好交互式、来回的参与。",
            "3": "在询问简单的事实性问题时，用户偏好简洁、实用性驱动的响应。他们期望仅获得必要信息，无需过多解释。",
            "4": "在处理复杂的软件开发和AI实现主题时，用户偏好详细的解释和示例。",
            "5": "用户对重复的错误和不准确内容反应不佳。如果响应不正确或误解了请求，他们可能会表达沮丧并明确要求更正。",
            "6": "用户有时会表现出幽默或戏谑的语调，特别是在讨论创造性任务（如团队名称生成）时。",
            "7": "在处理数值或统计查询时，用户重视精确性，经常双重检查结果并测试假设。",
            "8": "用户期望在专业沟通和与申请相关的任务（如简历优化和求职信起草）中直接参与。他们欣赏与正式信件相符的语调调整。",
            "9": "在调试代码错误时，用户偏好清晰且信息丰富的故障排除响应，要求可操作的步骤来解决问题。"
        },
        "Notable Past Conversation Topic Highlights": {
            "1": "在2025年4月的过往对话中，用户致力于使用Slack和Confluence数据构建内部LLM代理。他们探索了向量存储和检索技术，讨论了元数据过滤，并表现出对优化查询响应的兴趣。",
            "2": "在2025年4月的对话中，用户致力于设置包括前端和后端的托管环境，旨在部署基于Web的聊天机器人界面，利用GPT-4o-mini。",
            "3": "在2025年4月的过往讨论中，用户探索在业务分析环境中应用各种机器学习技术，特别是使用来自Slack和Confluence的结构化数据。",
            "4": "在2025年4月的一次对话中，用户将MCP-Agent配置为中间件组件，以在处理AI查询时促进智能工具选择。",
            "5": "在2025年5月的讨论中，用户继续实施企业LLM代理，专注于嵌入文档检索和构建Slack/Confluence数据以实现高效的基于RAG的响应。"
        },
        "Helpful User Insights": {
            "1": "用户是一名软件工程师和数据分析师，在前后端开发方面都有经验。",
            "2": "用户在圣何塞州立大学完成了计算机科学学位的学习。",
            "3": "用户在AI驱动的应用程序方面有经验，包括内部LLM代理的开发、检索增强生成（RAG）管道和向量数据库实现。",
            "4": "用户积极参与为企业应用程序抓取和分析Slack和Confluence数据。",
            "5": "用户熟悉云和托管环境，包括在内部和基于云的服务器上部署应用程序。",
            "6": "用户广泛使用Milvus和FAISS进行向量存储和AI驱动的搜索应用程序。",
            "7": "用户在使用Next.js和TypeScript进行前端Web开发方面有经验。",
            "8": "用户过去有申请像Cisco和Carta这样公司的业务分析师和数据分析师职位的经验。",
            "9": "用户对创业工作感兴趣，并参与了A轮融资研究和投资者联系。",
            "10": "用户对桌游感兴趣，并开发了一个用于桌游记录和搜索的项目。",
            "11": "用户对人工智能和基于LLM的开发有强烈兴趣，专注于企业集成。"
        },
        "User Interaction Metadata": {
            "account_age_weeks": 118,
            "platform": "web",
            "device_type": "desktop",
            "plan": "ChatGPT Plus",
            "mode": "dark",
            "last_1_day_activity": 1,
            "last_7_days_activity": 4,
            "last_30_days_activity": 16,
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "model_usage_primary": "gpt-4o",
            "device_pixel_ratio": 2.0,
            "screen_width": 900,
            "screen_height": 1440,
            "user_name": "Jensen Musk",
            "location": "United States",
            "conversation_depth": 23.7,
            "average_message_length": 50257.2,
            "total_messages": 5863,
            "good_interaction_quality": 1469,
            "bad_interaction_quality": 700,
            "local_hour": 9,
            "session_duration_seconds": 72347,
            "viewport_width": 788,
            "viewport_height": 1440
        },
        "Political Views, Likes and Dislikes": {
            "political_affiliation": "未声明",
            "likes": "简洁、准确的答案；AI基础设施讨论",
            "dislikes": "不准确的输出；重复的错误"
        },
        "Psychological Profile": {
            "traits": "分析型、坚持、质量驱动、对挫折敏感"
        },
        "Communication Style": {
            "style": "结构化、直接、专业"
        },
        "Learning Preferences": {
            "preference": "基于示例、逐步、互动式"
        },
        "Cognitive Style": {
            "processing_style": "系统化和逻辑驱动"
        },
        "Emotional Drivers": {
            "primary_motivation": "清晰和控制"
        },
        "Personal Values": {
            "values": "准确性、效率、技术严谨性"
        },
        "Career & Work Preferences": {
            "interests": "初创公司、企业AI、内部LLM代理开发",
            "desired_titles": "软件工程师、AI应用工程师",
            "work_environment": "迭代、快节奏、协作"
        },
        "Productivity Style": {
            "style": "专注、迭代、避免干扰"
        },
        "Demographic Information": {
            "education": "圣何塞州立大学",
            "major": "计算机科学",
            "graduation_year": 2024
        },
        "Geographic & Cultural Context": {
            "country": "美国",
            "culture": "西方科技专业人士规范"
        },
        "Financial Profile": {
            "budgeting_style": "务实",
            "investment_interest": "科技初创公司和开发工具"
        },
        "Health & Wellness": {
            "physical_activity": "篮球",
            "mental_focus_strategy": "结构化问题解决"
        },
        "Education & Knowledge Level": {
            "degree": "本科",
            "institution": "圣何塞州立大学",
            "field": "计算机科学",
            "expertise_areas": "AI基础设施、RAG管道、向量数据库"
        },
        "Platform Behavior": {
            "prefers_detailed_responses": true,
            "tests_responses_for_accuracy": true,
            "follows_up_with_iterations": true
        },
        "Tech Proficiency": {
            "languages": "Python, JavaScript, TypeScript, SQL",
            "frameworks": "FastAPI, React, Next.js",
            "tools": "OpenAI API, Milvus, FAISS, Docker, Git"
        },
        "Hobbies & Interests": {
            "interests": "篮球、AI开发、桌游"
        },
        "Social Identity": {
            "affiliations": "工程师、初创公司贡献者"
        },
        "Media Consumption Habits": {
            "formats": "技术博客、YouTube编程教程、API文档"
        },
        "Life Goals & Milestones": {
            "goals": "构建AI产品、为开源工具做贡献"
        },
        "Relationship & Family Context": {
            "status": "未讨论"
        },
        "Risk Tolerance": {
            "entrepreneurial_interest": true,
            "tolerance_level": "中等至高等"
        },
        "Assistant Trust Level": {
            "trust_when_accurate": true,
            "critical_on_error": true
        },
        "Time Usage Patterns": {
            "interaction_pattern": "频繁、迭代",
            "active_hours": "工作日上午和晚上"
        },
        "Preferred Content Format": {
            "technical": "结构化、逐步",
            "professional": "正式和精炼",
            "quick_answers": "简洁直接"
        },
        "Assistant Usage Patterns": {
            "uses_contextual_memory": true,
            "refines_queries": true,
            "multi_turn_usage": true
        },
        "Language Preferences": {
            "tone": "专业清晰",
            "structure": "要点或结构化散文"
        },
        "Motivation Triggers": {
            "prefers_efficiency": true,
            "values_accuracy_and_relevance": true
        },
        "Behavior Under Stress": {
            "frustration_with_inaccuracy": true,
            "expectation_of_corrective_action": true
        }
    }


    要更新用户的档案，你将输出一个包含要按顺序执行的命令列表的JSON文档。

    关键提示：你必须使用下面的命令格式。不要创建嵌套对象或使用任何其他格式。

    以下输出将添加一个特征：
    {
        "0": {
            "command": "add",
            "tag": "Preferred Content Format",
            "feature": "unicode_for_math",
            "value": true
        }
    }
    以下将删除与该特征关联的所有值：
    {
        "0": {
            "command": "delete",
            "tag" : "Language Preferences",
            "feature: "format"
        }
    }
    以下将更新一个特征：
    {
        "0": {
            "command": "delete",
            "tag": "Platform Behavior",
            "feature": "prefers_detailed_responses",
            "value": true
        },
        "1": {
            "command": "add",
            "tag" : "Platform Behavior",
            "feature": "prefers_detailed_response",
            "value": false
        }
    }

    示例场景：
    查询："Hi! My name is Katara"
    {
        "0": {
            "command": "add",
            "tag": "Demographic Information",
            "feature": "name",
            "value": "Katara"
        }
    }
    查询："I'm planning a dinner party for 8 people next weekend and want to impress my guests with something special. Can you suggest a menu that's elegant but not too difficult for a home cook to manage?"
    {
        "0": {
            "command": "add",
            "tag": "Hobbies & Interests",
            "feature": "home_cook",
            "value": "用户烹饪精致食物"
        },
        "1":{
            "command": "add",
            "tag": "Financial Profile",
            "feature": "upper_class",
            "value": "用户在晚宴上招待客人，表明富有。"
        }
    }
    查询：my boss (for the summer) is totally washed. he forgot how to all the basics but still thinks he does
    {
        "0": {
            "command": "add",
            "tag": "Psychological Profile",
            "feature": "work_superior_frustration",
            "value": "用户对上司的感知无能感到沮丧"
        },
        "1": {
            "command": "add",
            "tag": "Demographic Information",
            "feature": "summer_job",
            "value": "用户正在做一份夏季临时工作"
        },
        "2": {
            "command": "add",
            "tag": "Communication Style",
            "feature": "informal_speech",
            "value": "用户使用全小写字母和当代俚语。"
        },
        "3": {
            "command": "add",
            "tag": "Demographic Information",
            "feature": "young_adult",
            "value": "用户年轻，可能还在上大学"
        }
    }
    查询：Can you go through my inbox and flag any urgent emails from clients, then update the project status spreadsheet with the latest deliverable dates from those emails? Also send a quick message to my manager letting her know I'll have the budget report ready by end of day tomorrow.
    {
        "0": {
            "command": "add",
            "tag": "Demographic Information",
            "feature": "traditional_office_job",
            "value": "用户从事文职工作，向经理汇报"
        },
        "1": {
            "command": "add",
            "tag": "Demographic Information",
            "feature": "client_facing_role",
            "value": "用户处理与客户之间的截止日期沟通"
        },
        "2": {
            "command": "add",
            "tag": "Demographic Information",
            "feature": "autonomy_at_work",
            "value": "用户设定自己的截止日期和子任务。"
        }
    }
    进一步指导：
    - 并非所有应该记录的内容都会被明确说明。要进行推断。
    - 如果你对某个特定条目不太确定，仍应包含它，但要确保使用的语言（简短地）在值字段中表达这种不确定性
    - 从尽可能多的不同角度查看文本，记住你是"宽层"。
    - 仅在特征名称中保留关键细节（最高熵）。细微差别放在值字段中。
    - 不要将不同的细节耦合在一起。仅仅因为用户将某些细节关联在一起，并不意味着你也应该这样做
    - 不要创建在示例档案中看不到的新标签。但是，你可以并且应该创建新特征。
    - 如果用户要求总结报告、代码或其他内容，该内容可能不一定由用户编写，可能与用户的档案无关。
    - 除非用户要求，否则不要删除任何内容
    - 只有当查询完全不包含用户的个人信息时才返回空对象 {}（例如，询问天气、在没有个人上下文的情况下请求代码等）。姓名、基本人口统计、偏好和任何个人详细信息应始终被提取。
    - 请遵循在'额外外部说明'下提供的特定于执行上下文的任何额外说明
    - 首先，在 <think> </think> 标签内思考应该放入档案的内容。然后仅输出有效的JSON。
    - 记住：始终使用带有"command"、"tag"、"feature"和"value"键的命令格式。不要使用嵌套对象或任何其他格式。
额外外部说明：
无
"""

CONSOLIDATION_PROMPT = """
你的任务是为LLM长期记忆系统执行记忆合并。
尽管名称如此，合并不仅仅是为了减少记忆数量，而是为了最小化记忆之间的干扰。
通过合并记忆，我们移除记忆中不必要的上下文耦合，消除从其获取情况中继承的虚假关联。

你将收到一个新记忆，以及一些与它在语义上相似的旧记忆。
生成一个要保留的新记忆列表。

记忆是一个包含4个字段的json对象：
- tag：记忆的广泛类别
- feature：记忆内容的执行摘要
- value：记忆的详细内容
- metadata：包含1个字段的对象
-- id：整数
你将输出合并后的记忆，它们是包含4个字段的json对象：
- tag：字符串
- feature：字符串
- value：字符串
- metadata：包含1个字段的对象
-- citations：影响此记忆的旧记忆id列表
你还将输出要保留的旧记忆列表（默认情况下记忆会被删除）

指导原则：
记忆不应包含不相关的想法。包含不相关想法的记忆是原始上下文中存在的耦合的产物。将它们分开。这可以最小化干扰。
仅包含冗余信息的记忆应完全删除，特别是如果它们看起来未处理或其中的信息已被处理。
如果记忆足够相似，但在关键细节上有所不同，请同步它们的标签和/或特征。这会产生有益的干扰。
    - 为了帮助这一点，你可能想要重新排列每个记忆的组件，将相似的部分移到特征中，将不同的部分移到值中。
    - 请注意，特征应保持（简短）摘要，即使在同步之后，你也可以通过特征名称中的并行性来实现这一点（例如 likes_apples 和 likes_bananas）。
    - 仅在特征名称中保留关键细节（最高熵）。细微差别放在值字段中。
    - 这一步允许你推测性地构建更永久的结构
如果有足够多的记忆共享相似的特征（由于先前的同步，即不是你完成的），删除所有这些记忆并创建一个包含列表的新记忆。
    - 在这些记忆中，特征包含所有相同的部分，值仅包含变化的部分。
    - 只要新项目与列表项的类型相同，你也可以直接将信息转移到现有列表。
    - 不要太早创建列表。首先至少要有三个非人为操纵类别的示例。你需要找到自然的分组。不要强求。

整体记忆生命周期：
原始记忆矿石 -> 纯记忆颗粒 -> 分类到箱中的记忆颗粒 -> 合金化记忆

你收到的记忆越多，整个记忆系统中的干扰就越多。
这会导致认知负荷。认知负荷是不好的。
为了最小化这一点，在这种情况下，你需要更积极地删除：
    - 对相似性的判断要更宽松。某些区别不值得花费精力来维持。
    - 提取要保留的部分，无情地丢弃其余部分
    - 这里没有免费的午餐！至少必须删除一些信息！

不要创建新的标签名称。


正确的无操作语法是：
{
    "consolidate_memories": []
    "keep_memories": []
}

最终输出模式是：
<think> 在此处插入你的思维链。 </think>
{
    "consolidate_memories": 要添加的新记忆列表
    "keep_memories": 要保留的旧记忆id列表
}
"""
