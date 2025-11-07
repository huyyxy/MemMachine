"""同步 Profile Memory 数据库 schema 的实用脚本。

本文件提供两个主要能力：

1. 删除目标数据库中的所有 `public` schema 数据表；
2. 将项目内最新的 SQL schema 应用到目标数据库。

脚本同时支持通过命令行参数覆盖默认环境变量，方便在不同环境
（本地、测试、生产等）中重用。如果你正在学习如何与 PostgreSQL
进行异步交互或如何封装数据库运维脚本，可以把这个文件当作参考。
"""

import argparse
import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from pgvector.asyncpg import register_vector

script_dir = str(Path(__file__).parent)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def get_base() -> str:
    """读取同目录下的 `baseschema.sql` 文件。

    我们将数据库 schema 写在独立 SQL 文件中，方便被其他工具
    （例如迁移脚本、数据库 IDE）复用。本函数简单地读文件内容，
    调用方负责将其执行到数据库里。
    """

    # 这里直接用 `open(...).read()`：脚本运行频率较低，不必额外封装。
    # 若项目需要频繁读取，可考虑缓存，避免重复打开文件。
    return open(f"{script_dir}/baseschema.sql", "r").read()


async def delete_data(database: str, host: str, port: str, user: str, password: str):
    """删除指定数据库 `public` schema 下的所有表。

    参数均为数据库连接信息。函数内部创建一个连接池，并遍历
    `pg_catalog.pg_tables` 中的表记录，逐个执行 `DROP TABLE ... CASCADE`。

    注意：`CASCADE` 会连带删除依赖对象，请谨慎在生产环境使用。
    """

    d: dict[str, str] = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }
    print(
        f"Deleting tables in {
            {
                'host': host,
                'port': port,
                'user': user,
                'password': '****',
                'database': database,
            }
        }"
    )
    # 使用连接池（pool）提升效率，同时注册 pgvector 扩展，保证后续
    # 删除表时能够正确识别可能存在的向量列。
    pool = await asyncpg.create_pool(init=register_vector, **d)
    table_records = await pool.fetch(
        """
        SELECT tablename FROM pg_catalog.pg_tables
        WHERE schemaname = 'public';
        """
    )
    tables = [table_record[0] for table_record in table_records]

    for table in tables:
        print(f"Dropping table: {table}")
        await pool.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')


async def sync_to(database: str, host: str, port: str, user: str, password: str):
    """将 `baseschema.sql` 中的最新 schema 应用到目标数据库。

    实现方式：建立一次性连接，执行整个 SQL 文件内容。通常 SQL 中
    包含创建表、索引、扩展等操作。执行完成后在终端打印提示。
    """

    d: dict[str, str] = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }
    print(
        f"Syncing schema to {
            {
                'host': host,
                'port': port,
                'user': user,
                'database': database,
            }
        }"
    )
    # 为确保环境干净，可以先调用 `delete_data`。这里仅负责执行 schema。
    connection = await asyncpg.connect(**d)
    await connection.execute(get_base())
    print("Re-initializing ...")


def main():
    """脚本入口：解析命令行参数并转交给异步主函数。"""

    # 先加载环境变量，确保默认值可用，例如 `.env` 文件中的数据库配置。
    load_dotenv()

    # argparse 负责构建命令行界面，便于用户快速指定目标数据库信息。
    parser = argparse.ArgumentParser(
        prog="memmachine-sync-profile-schema",
        description="sync latest schema to db. By default syncs to the cluster specified by the environment variables",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("POSTGRES_DB"),
        help="the default database name is read from the environment variable POSTGRES_DB",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("POSTGRES_HOST"),
        help="the default host is read from the environment variable POSTGRES_HOST",
    )
    parser.add_argument(
        "--port",
        default=os.getenv("POSTGRES_PORT"),
        help="the default port is read from the environment variable POSTGRES_PORT",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("POSTGRES_USER"),
        help="the default user is read from the environment variable POSTGRES_USER",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("POSTGRES_PASSWORD"),
        help="the default password is read from the environement variable POSTGRES_PASSWORD",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="delete and recreate the database with new schema.",
    )
    args = parser.parse_args()

    asyncio.run(main_async(args))


async def main_async(args):
    """根据命令行参数决定执行流程。

    如果传入 `--delete`，会先删除所有旧表，再执行 schema 初始化。
    这样可以确保数据库结构完全与 `baseschema.sql` 保持一致。
    """

    if args.delete:
        await delete_data(args.database, args.host, args.port, args.user, args.password)
    await sync_to(args.database, args.host, args.port, args.user, args.password)


if __name__ == "__main__":
    main()
