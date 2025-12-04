#!/usr/bin/env python3
"""
Verification script for HA AI Agent Service fix.
Tests context injection, prompt assembly, and system prompt enhancements.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Service URL
SERVICE_URL = "http://localhost:8030"

# Expected patterns in system prompt
EXPECTED_PROMPT_PATTERNS = [
    "immediately process their request",
    "Do not respond with generic welcome messages",
    "you MUST use the available tools",
    "actually create the automation",
]

# Expected context sections
EXPECTED_CONTEXT_SECTIONS = [
    "ENTITY INVENTORY",
    "AREAS/ROOMS",
    "AVAILABLE SERVICES",
    "DEVICE CAPABILITY PATTERNS",
    "HELPERS & SCENES",
]


async def test_health_check():
    """Test service health endpoint"""
    console.print("\n[bold cyan]1. Testing Health Check...[/bold cyan]")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICE_URL}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                console.print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
                
                # Check context builder status
                checks = health_data.get("checks", {})
                context_check = checks.get("context_builder", {})
                if context_check.get("status") == "healthy":
                    console.print("✅ Context builder is healthy")
                    components = context_check.get("components", {})
                    for component, available in components.items():
                        status = "✅" if available else "❌"
                        console.print(f"   {status} {component}: {available}")
                else:
                    console.print(f"⚠️  Context builder status: {context_check.get('status', 'unknown')}")
                
                return True
            else:
                console.print(f"❌ Health check failed: {response.status_code}")
                console.print(f"   Response: {response.text}")
                return False
                
    except httpx.ConnectError:
        console.print(f"❌ Cannot connect to service at {SERVICE_URL}")
        console.print("   Make sure the service is running: docker-compose up ha-ai-agent-service")
        return False
    except Exception as e:
        console.print(f"❌ Health check error: {e}")
        return False


async def test_system_prompt():
    """Test system prompt endpoint and verify enhancements"""
    console.print("\n[bold cyan]2. Testing System Prompt (Base)...[/bold cyan]")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICE_URL}/api/v1/system-prompt")
            
            if response.status_code == 200:
                data = response.json()
                system_prompt = data.get("system_prompt", "")
                token_count = data.get("token_count", 0)
                
                console.print(f"✅ System prompt retrieved ({token_count} tokens)")
                
                # Check for expected patterns
                found_patterns = []
                missing_patterns = []
                
                for pattern in EXPECTED_PROMPT_PATTERNS:
                    if pattern.lower() in system_prompt.lower():
                        found_patterns.append(pattern)
                    else:
                        missing_patterns.append(pattern)
                
                if found_patterns:
                    console.print(f"✅ Found {len(found_patterns)}/{len(EXPECTED_PROMPT_PATTERNS)} expected patterns:")
                    for pattern in found_patterns:
                        console.print(f"   ✓ {pattern}")
                
                if missing_patterns:
                    console.print(f"⚠️  Missing {len(missing_patterns)} expected patterns:")
                    for pattern in missing_patterns:
                        console.print(f"   ✗ {pattern}")
                
                # Show first 200 chars
                console.print("\n[dim]First 200 characters:[/dim]")
                console.print(Panel(system_prompt[:200] + "...", title="System Prompt Preview"))
                
                return len(found_patterns) > 0
            else:
                console.print(f"❌ System prompt request failed: {response.status_code}")
                console.print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        console.print(f"❌ System prompt test error: {e}")
        return False


async def test_context():
    """Test context endpoint"""
    console.print("\n[bold cyan]3. Testing Context Building...[/bold cyan]")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SERVICE_URL}/api/v1/context")
            
            if response.status_code == 200:
                data = response.json()
                context = data.get("context", "")
                token_count = data.get("token_count", 0)
                
                console.print(f"✅ Context retrieved ({token_count} tokens)")
                
                # Check for expected sections
                found_sections = []
                missing_sections = []
                
                for section in EXPECTED_CONTEXT_SECTIONS:
                    if section in context:
                        found_sections.append(section)
                    else:
                        missing_sections.append(section)
                
                if found_sections:
                    console.print(f"✅ Found {len(found_sections)}/{len(EXPECTED_CONTEXT_SECTIONS)} context sections:")
                    for section in found_sections:
                        console.print(f"   ✓ {section}")
                
                if missing_sections:
                    console.print(f"⚠️  Missing {len(missing_sections)} context sections:")
                    for section in missing_sections:
                        console.print(f"   ✗ {section}")
                
                # Show first 300 chars
                console.print("\n[dim]First 300 characters:[/dim]")
                console.print(Panel(context[:300] + "...", title="Context Preview"))
                
                return len(found_sections) > 0
            else:
                console.print(f"❌ Context request failed: {response.status_code}")
                console.print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        console.print(f"❌ Context test error: {e}")
        return False


async def test_complete_prompt():
    """Test complete prompt (system + context)"""
    console.print("\n[bold cyan]4. Testing Complete Prompt (System + Context)...[/bold cyan]")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SERVICE_URL}/api/v1/complete-prompt")
            
            if response.status_code == 200:
                data = response.json()
                complete_prompt = data.get("system_prompt", "")  # Note: API returns it as "system_prompt"
                token_count = data.get("token_count", 0)
                
                console.print(f"✅ Complete prompt retrieved ({token_count} tokens)")
                
                # Verify it contains both system prompt and context
                has_system_prompt = any(pattern.lower() in complete_prompt.lower() for pattern in EXPECTED_PROMPT_PATTERNS)
                has_context = any(section in complete_prompt for section in EXPECTED_CONTEXT_SECTIONS)
                
                if has_system_prompt:
                    console.print("✅ Contains enhanced system prompt")
                else:
                    console.print("⚠️  System prompt patterns not found")
                
                if has_context:
                    console.print("✅ Contains Tier 1 context")
                else:
                    console.print("⚠️  Context sections not found")
                
                # Check for context injection marker
                if "HOME ASSISTANT CONTEXT:" in complete_prompt:
                    console.print("✅ Context injection marker found")
                else:
                    console.print("⚠️  Context injection marker not found")
                
                # Show structure
                console.print("\n[dim]Prompt structure:[/dim]")
                if "HOME ASSISTANT CONTEXT:" in complete_prompt:
                    parts = complete_prompt.split("HOME ASSISTANT CONTEXT:")
                    system_part = parts[0]
                    context_part = "HOME ASSISTANT CONTEXT:" + parts[1] if len(parts) > 1 else ""
                    console.print(f"   System prompt: ~{len(system_part)} chars")
                    console.print(f"   Context: ~{len(context_part)} chars")
                
                return has_system_prompt and has_context
            else:
                console.print(f"❌ Complete prompt request failed: {response.status_code}")
                console.print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        console.print(f"❌ Complete prompt test error: {e}")
        return False


async def main():
    """Run all verification tests"""
    console.print(Panel.fit(
        "[bold green]HA AI Agent Service Fix Verification[/bold green]\n"
        "Testing context injection, prompt assembly, and system prompt enhancements",
        border_style="green"
    ))
    
    results = {}
    
    # Run tests
    results["health"] = await test_health_check()
    results["system_prompt"] = await test_system_prompt()
    results["context"] = await test_context()
    results["complete_prompt"] = await test_complete_prompt()
    
    # Summary
    console.print("\n[bold cyan]Verification Summary[/bold cyan]")
    table = Table(title="Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", justify="center")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        table.add_row(test_name.replace("_", " ").title(), status)
    
    console.print(table)
    
    # Overall result
    all_passed = all(results.values())
    if all_passed:
        console.print("\n[bold green]✅ All tests passed! Context injection is working correctly.[/bold green]")
        console.print("\n[dim]Next steps:[/dim]")
        console.print("1. Test the chat endpoint via browser: http://localhost:3000/ai-agent")
        console.print("2. Check service logs: docker-compose logs -f ha-ai-agent-service")
        console.print("3. Look for [Context Builder], [Prompt Assembly], and [OpenAI API] log entries")
        return 0
    else:
        console.print("\n[bold red]❌ Some tests failed. Please check the service logs.[/bold red]")
        console.print("\n[dim]Troubleshooting:[/dim]")
        console.print("1. Ensure service is running: docker-compose ps ha-ai-agent-service")
        console.print("2. Check service logs: docker-compose logs ha-ai-agent-service")
        console.print("3. Verify service was restarted after code changes")
        console.print("4. Check environment variables are set correctly")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

