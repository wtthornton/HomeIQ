"""Test script to check context building"""
import asyncio
import sys
from src.services.context_builder import ContextBuilder
from src.config import Settings

async def test():
    s = Settings()
    cb = ContextBuilder(s)
    await cb.initialize()
    
    try:
        ctx = await cb.build_context(skip_truncation=True)
        print(f"Context length: {len(ctx)}")
        print(f"DEVICES in context: {'DEVICES:' in ctx}")
        
        if 'DEVICES:' in ctx:
            dev_start = ctx.index('DEVICES:')
            dev_end = ctx.find('AREAS:', dev_start)
            if dev_end == -1:
                dev_end = len(ctx)
            
            dev_section = ctx[dev_start:dev_end]
            print(f"\nDEVICES section ({len(dev_section)} chars):")
            print(dev_section[:1000])
        else:
            print("\n❌ DEVICES section NOT found!")
            # Show what sections are present
            sections = []
            if 'AREAS:' in ctx:
                sections.append('AREAS')
            if 'AVAILABLE SERVICES:' in ctx:
                sections.append('AVAILABLE SERVICES')
            if 'HELPERS & SCENES:' in ctx:
                sections.append('HELPERS & SCENES')
            print(f"Found sections: {', '.join(sections)}")
    finally:
        await cb.close()

if __name__ == "__main__":
    asyncio.run(test())

