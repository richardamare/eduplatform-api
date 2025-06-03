#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from app.database import async_session

async def check_schema():
    async with async_session() as db:
        result = await db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'vectors' ORDER BY ordinal_position;"))
        columns = [row[0] for row in result.fetchall()]
        print('Vectors table columns:', columns)
        
        # Also check if the table exists
        result = await db.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'vectors');"))
        exists = result.scalar()
        print('Vectors table exists:', exists)
        
asyncio.run(check_schema()) 