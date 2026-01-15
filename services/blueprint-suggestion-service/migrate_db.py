"""Quick migration script to add missing columns."""
import asyncio
import aiosqlite

async def migrate():
    db_path = '/app/data/blueprint_suggestions.db'
    conn = await aiosqlite.connect(db_path)
    
    # Check existing columns
    cursor = await conn.execute('PRAGMA table_info(blueprint_suggestions)')
    rows = await cursor.fetchall()
    cols = [row[1] for row in rows]
    print(f'Existing columns: {cols}')
    
    has_name = 'blueprint_name' in cols
    has_desc = 'blueprint_description' in cols
    
    print(f'Has blueprint_name: {has_name}, Has blueprint_description: {has_desc}')
    
    if not has_name:
        await conn.execute('ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_name VARCHAR(255)')
        await conn.commit()
        print('✓ Added blueprint_name column')
    
    if not has_desc:
        await conn.execute('ALTER TABLE blueprint_suggestions ADD COLUMN blueprint_description TEXT')
        await conn.commit()
        print('✓ Added blueprint_description column')
    
    if has_name and has_desc:
        print('✓ All columns already exist')
    
    await conn.close()

if __name__ == '__main__':
    asyncio.run(migrate())
