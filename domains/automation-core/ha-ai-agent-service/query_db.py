"""Query database for debug_id"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, text
from database import ConversationModel, get_session

async def query():
    debug_id = "753229c4-38db-47e5-be6e-337fd33cf467"
    
    async for session in get_session():
        # Query by debug_id
        stmt = select(ConversationModel).where(ConversationModel.debug_id == debug_id)
        result = await session.execute(stmt)
        conv = result.scalar_one_or_none()
        
        if conv:
            print(f"✅ Found conversation:")
            print(f"  conversation_id: {conv.conversation_id}")
            print(f"  debug_id: {conv.debug_id}")
            print(f"  created_at: {conv.created_at}")
        else:
            print(f"❌ Conversation with debug_id {debug_id} not found")
            
            # Try to find similar
            stmt2 = select(ConversationModel.conversation_id, ConversationModel.debug_id).where(
                ConversationModel.debug_id.like(f"%{debug_id[:8]}%")
            )
            result2 = await session.execute(stmt2)
            similar = result2.fetchall()
            if similar:
                print(f"\nFound {len(similar)} similar conversations:")
                for row in similar:
                    print(f"  conversation_id: {row[0]}, debug_id: {row[1]}")

if __name__ == "__main__":
    asyncio.run(query())

