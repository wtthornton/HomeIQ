"""
Target prompts for Ask AI continuous improvement testing.
Extracted from ask-ai-continuous-improvement.py.
"""

# 15 Prompts of Increasing Complexity
# All prompts use device-friendly names that the system can resolve to actual entity IDs
# Devices used: Office WLED (light.wled_office), Living Room lights (various light.lr_* entities)
TARGET_PROMPTS = [
    # Simple Prompts (1-3)
    {
        "id": "prompt-1-simple",
        "name": "Simple Time-Based Light",
        "prompt": "Turn on the Office WLED every day at 7:00 AM",
        "complexity": "Simple"
    },
    {
        "id": "prompt-2-simple",
        "name": "Simple Light Control",
        "prompt": "Turn off all living room lights at 11:00 PM every night",
        "complexity": "Simple"
    },
    {
        "id": "prompt-3-simple",
        "name": "Basic Schedule",
        "prompt": "Turn on the Office WLED at 8:00 AM on weekdays only",
        "complexity": "Simple"
    },
    # Medium Prompts (4-7)
    {
        "id": "prompt-4-medium",
        "name": "Time-Based Conditional Lighting",
        "prompt": "Between 6 PM and 11 PM every day, turn on the living room lights to 80% brightness",
        "complexity": "Medium"
    },
    {
        "id": "prompt-5-medium",
        "name": "Time-Based Multi-Light",
        "prompt": "At sunset, turn on the Office WLED to 60% brightness and set it to a warm white color",
        "complexity": "Medium"
    },
    {
        "id": "prompt-6-medium",
        "name": "Conditional Brightness",
        "prompt": "When the living room lights are turned on after 8 PM, automatically dim them to 40% brightness",
        "complexity": "Medium"
    },
    {
        "id": "prompt-7-medium",
        "name": "Multi-Area Lighting",
        "prompt": "At 6:00 AM, turn on the Office WLED to 50% and turn on all living room lights to 30%",
        "complexity": "Medium"
    },
    # Complex Prompts (8-11)
    {
        "id": "prompt-8-complex",
        "name": "Sunset-Based Multi-Device Sequence",
        "prompt": "After sunset every day, turn on the living room lights for 5 minutes, then turn on the Office WLED, wait 30 seconds, and turn off the living room lights",
        "complexity": "Complex"
    },
    {
        "id": "prompt-9-complex",
        "name": "Time-Based Conditional Sequence",
        "prompt": "At 7:00 AM on weekdays, if the Office WLED is off, turn it on to 75% brightness. On weekends, turn it on to 50% brightness at 9:00 AM",
        "complexity": "Complex"
    },
    {
        "id": "prompt-10-complex",
        "name": "Multi-Trigger Conditional",
        "prompt": "When the living room lights are turned on between 6 PM and 10 PM, automatically set the Office WLED to match their brightness level",
        "complexity": "Complex"
    },
    {
        "id": "prompt-11-complex",
        "name": "Time-Range Multi-Device",
        "prompt": "Between 5 PM and 11 PM, every 30 minutes, cycle through the living room lights: turn one on, wait 2 minutes, turn it off, and turn the next one on",
        "complexity": "Complex"
    },
    # Very Complex Prompts (12-14)
    {
        "id": "prompt-12-very-complex",
        "name": "WLED State Restoration",
        "prompt": "Every 15 mins choose a random effect on the Office WLED device. Play the effect for 15 secs. Choose random effect, random colors and brightness to 100%. At the end of the 15 sec the WLED light needs to return to exactly what it was before it started.",
        "complexity": "Very Complex"
    },
    {
        "id": "prompt-13-very-complex",
        "name": "Multi-Device Time-Based Sequence",
        "prompt": "At 6:00 AM, turn on the Office WLED to 40% with a warm white color. At 6:15 AM, increase it to 60%. At 6:30 AM, turn on all living room lights to 30%. At 7:00 AM, turn off the Office WLED and increase living room lights to 80%",
        "complexity": "Very Complex"
    },
    {
        "id": "prompt-14-extremely-complex",
        "name": "Complex Conditional Logic",
        "prompt": "If the Office WLED is on and it's after 8 PM, turn it off. If it's between 6 AM and 8 AM and the Office WLED is off, turn it on to 50%. If the living room lights are on and it's after 10 PM, dim them to 20% over 5 minutes. If it's before 6 AM and any lights are on, turn them all off",
        "complexity": "Extremely Complex"
    },
    # Extremely Complex (15)
    {
        "id": "prompt-15-extremely-complex",
        "name": "Ultra Complex Multi-Device Logic",
        "prompt": "Create a morning routine: At 6:00 AM, if it's a weekday, turn on the Office WLED to 30% with a cool white color. Wait 10 minutes, then increase to 60%. At 6:30 AM, turn on living room lights to 40%. At 7:00 AM, if the Office WLED is still on, turn it off and increase living room lights to 70%. On weekends, start this routine at 8:00 AM instead",
        "complexity": "Extremely Complex"
    },
]

