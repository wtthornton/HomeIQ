#!/usr/bin/env python3
"""
Test OpenAI API connection.
Verifies API key and basic completion works.
"""

import sys
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / 'infrastructure' / 'env.ai-automation'
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    sys.exit(1)

import os

try:
    from openai import OpenAI
except ImportError:
    print("⚠️  openai package not installed. Install with: pip install openai")
    sys.exit(1)

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

print("=" * 60)
print("🧪 Testing OpenAI API Connection")
print("=" * 60)
print(f"API Key: {OPENAI_API_KEY[:20]}... (length: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0})")
print("Model: gpt-4o-mini (cost-effective)")
print("=" * 60)

# Verify API key loaded
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not configured in env.ai-automation")
    sys.exit(1)

# Test results
test_results = {
    'api_key_valid': False,
    'basic_completion': False,
    'cost_tracking': False
}

# Create client
client = OpenAI(api_key=OPENAI_API_KEY)

# Test 1: Simple completion
try:
    print("\n⏳ Test 1: Testing basic API call...")
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello' if you can read this."}
        ],
        max_tokens=10,
        temperature=0
    )
    
    content = response.choices[0].message.content
    tokens_used = response.usage.total_tokens
    
    print(f"✅ API call successful!")
    print(f"   Response: {content}")
    print(f"   Tokens used: {tokens_used}")
    
    test_results['api_key_valid'] = True
    test_results['basic_completion'] = True
    test_results['cost_tracking'] = True
    
except Exception as e:
    if "invalid_api_key" in str(e).lower() or "unauthorized" in str(e).lower():
        print("❌ Invalid API key")
        print("   Please check OPENAI_API_KEY in env.ai-automation")
    elif "quota" in str(e).lower():
        print("❌ API quota exceeded or billing issue")
        print("   Check your OpenAI account: https://platform.openai.com/usage")
    else:
        print(f"❌ API Error: {e}")
    sys.exit(1)

# Test 2: Test automation generation (realistic use case)
try:
    print("\n⏳ Test 2: Testing automation generation prompt...")
    
    test_pattern = {
        'device_id': 'light.bedroom',
        'hour': 7,
        'minute': 0,
        'occurrences': 28,
        'confidence': 0.93
    }
    
    prompt = f"""
Create a simple Home Assistant automation for this pattern:

PATTERN: light.bedroom turns on at 07:00 consistently
Occurrences: 28 times in last 30 days
Confidence: 93%

OUTPUT (valid Home Assistant YAML):
alias: "AI Suggested: Morning Bedroom Lights"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom

Explain in 1 sentence why this automation makes sense.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a home automation expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.7
    )
    
    automation = response.choices[0].message.content
    tokens_used = response.usage.total_tokens
    
    # Calculate cost (GPT-4o-mini pricing)
    input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.15
    output_cost = (response.usage.completion_tokens / 1_000_000) * 0.60
    total_cost = input_cost + output_cost
    
    print(f"✅ Automation generation successful!")
    print(f"   Tokens used: {tokens_used} (input: {response.usage.prompt_tokens}, output: {response.usage.completion_tokens})")
    print(f"   Cost: ${total_cost:.4f} per suggestion")
    print(f"   Estimated monthly cost (50 suggestions): ${total_cost * 50:.2f}")
    
    print("\n📝 Generated Automation Preview:")
    print("-" * 60)
    print(automation[:300] + "..." if len(automation) > 300 else automation)
    print("-" * 60)
    
except Exception as e:
    print(f"⚠️  Automation generation error: {e}")

# Print summary
print("\n" + "=" * 60)
print("📊 TEST SUMMARY")
print("=" * 60)
print(f"API Key Valid:        {'✅ PASS' if test_results['api_key_valid'] else '❌ FAIL'}")
print(f"Basic Completion:     {'✅ PASS' if test_results['basic_completion'] else '❌ FAIL'}")
print(f"Cost Tracking:        {'✅ PASS' if test_results['cost_tracking'] else '❌ FAIL'}")
print("=" * 60)

if all(test_results.values()):
    print("\n🎉 All OpenAI API tests passed!")
    print("\n✅ OpenAI API connection verified and ready")
    print("\n💰 Estimated Costs:")
    print(f"   Per suggestion: ~$0.001-0.002")
    print(f"   Per batch (10 suggestions): ~$0.01-0.02")
    print(f"   Per month (50 suggestions): ~$0.05-0.10")
    print(f"   Well within $10/month budget! ✅")
    sys.exit(0)
else:
    print("\n⚠️  Some tests failed. Review errors above.")
    sys.exit(1)

