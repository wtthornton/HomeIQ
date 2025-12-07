"""Test Enhancer Agent with real-time progress output."""
import asyncio
import sys
from tapps_agents.agents.enhancer.agent import EnhancerAgent

async def main():
    """Run enhancement with real-time progress."""
    # Force unbuffered output
    sys.stderr.reconfigure(line_buffering=True)
    sys.stdout.reconfigure(line_buffering=True)
    
    print("Starting enhancement...", file=sys.stderr, flush=True)
    
    agent = EnhancerAgent()
    await agent.activate()
    
    try:
        prompt = "Add device health monitoring dashboard with real-time status indicators"
        print(f"\nPrompt: {prompt}\n", file=sys.stderr, flush=True)
        
        # Run quick enhancement - progress will appear in real-time
        result = await agent.run("enhance-quick", prompt=prompt, output_format="markdown")
        
        print("\n\n=== ENHANCED PROMPT ===\n", file=sys.stderr, flush=True)
        
        # Output the result
        enhanced = result.get("enhanced_prompt", {})
        if isinstance(enhanced, dict):
            content = enhanced.get("enhanced_prompt_content", "")
        else:
            content = str(enhanced)
        
        print(content)
        
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())

