"""Get prompt context by debug_id"""
import asyncio
import json
import sys

sys.path.insert(0, '/app/src')

from services.context_builder import ContextBuilder
from services.conversation_persistence import get_conversation_by_debug_id
from database import get_session
from config import Settings

async def get_prompt(debug_id):
    settings = Settings()
    
    # Get conversation by debug_id
    async for session in get_session():
        conversation = await get_conversation_by_debug_id(session, debug_id)
        if not conversation:
            print(f"❌ Conversation with debug_id {debug_id} not found")
            return
        
        print(f"✅ Found conversation:")
        print(f"  conversation_id: {conversation.conversation_id}")
        print(f"  debug_id: {conversation.debug_id}")
        
        # Build context
        from services.context_builder import ContextBuilder
        cb = ContextBuilder(settings)
        await cb.initialize()
        
        try:
            context = await cb.build_context(skip_truncation=True)
            print(f"\n📊 Context ({len(context)} chars):")
            print(context[:2000])
            
            if "DEVICES:" in context:
                print("\n✅ DEVICES section found!")
                devices_start = context.index("DEVICES:")
                devices_end = context.find("\n\n", devices_start)
                if devices_end == -1:
                    devices_end = len(context)
                print(f"\nDEVICES section ({devices_end - devices_start} chars):")
                print(context[devices_start:min(devices_start + 1000, devices_end)])
            else:
                print("\n❌ DEVICES section NOT found")
        finally:
            await cb.close()

if __name__ == "__main__":
    debug_id = sys.argv[1] if len(sys.argv) > 1 else "753229c4-38db-47e5-be6e-337fd33cf467"
    asyncio.run(get_prompt(debug_id))

