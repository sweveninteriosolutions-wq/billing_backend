import asyncio, asyncpg, ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

async def test():
    conn = await asyncpg.connect(
        "postgresql://postgres.ulvrwyvpdnuzlwvtfwtl:Sweven@2025@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
        ssl=ssl_ctx,
        statement_cache_size=0,
        server_settings={"prepareThreshold": "0"}
    )
    print("✅ Connected successfully!")
    await conn.close()

asyncio.run(test())
