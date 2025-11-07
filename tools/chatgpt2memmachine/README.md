# chatgpt2memmachine

将其他来源的记忆导入到 MemMachine。
支持 ChatGPT 和 locomo。

要从 ChatGPT 导入，请从 ChatGPT 导出聊天历史记录。然后运行 migration.py 进行导入。
例如：
uv run python3 migration.py --chat_type=openai --chat_history=conversations.json

要从 locomo 作为测试导入，请在项目目录中运行 test_migration.py。
例如：
uv run python3 test_migration.py
