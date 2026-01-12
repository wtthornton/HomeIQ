#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automate Pattern Analysis Re-run and Validation

Hybrid approach: API for execution, Playwright for UI validation.

This script:
1. Triggers pattern analysis via API
2. Waits for completion via API polling
3. Validates results via API (synergy types)
4. Validates UI with Playwright (user experience)
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import httpx
from playwright.async_api import async_playwright, Page, Browser

# Service URLs
PATTERN_SERVICE_URL = "http://localhost:8034"
UI_URL = "http://localhost:3001"
PATTERNS_PAGE = f"{UI_URL}/patterns"

# Timeouts
ANALYSIS_TIMEOUT_MINUTES = 15
POLL_INTERVAL_SECONDS = 15
MAX_POLL_ATTEMPTS = (ANALYSIS_TIMEOUT_MINUTES * 60) // POLL_INTERVAL_SECONDS  # 60 attempts


class PatternAnalysisAutomation:
    """Automate pattern analysis re-run and validation."""
    
    def __init__(self):
        self.pattern_service_url = PATTERN_SERVICE_URL
        self.ui_url = UI_URL
        self.results: Dict[str, Any] = {
            "triggered": False,
            "completed": False,
            "success": False,
            "errors": [],
            "validation_results": {}
        }
    
    async def check_service_health(self) -> bool:
        """Check if pattern service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.pattern_service_url}/health")
                if response.status_code == 200:
                    print("✅ Pattern service is healthy")
                    return True
                else:
                    print(f"❌ Pattern service health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Failed to check service health: {e}")
            return False
    
    async def trigger_analysis(self) -> bool:
        """Trigger pattern analysis via API."""
        try:
            print("\n📋 Step 1: Triggering pattern analysis...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.pattern_service_url}/api/analysis/trigger")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("status") == "running":
                        print("✅ Analysis triggered successfully")
                        self.results["triggered"] = True
                        return True
                    else:
                        print(f"⚠️ Unexpected response: {result}")
                        return False
                else:
                    print(f"❌ Failed to trigger analysis: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Error triggering analysis: {e}")
            self.results["errors"].append(f"Trigger error: {str(e)}")
            return False
    
    async def wait_for_completion(self) -> bool:
        """Wait for analysis to complete via API polling."""
        print("\n📋 Step 2: Waiting for analysis to complete...")
        print(f"   Polling every {POLL_INTERVAL_SECONDS} seconds (max {ANALYSIS_TIMEOUT_MINUTES} minutes)")
        
        for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.pattern_service_url}/api/analysis/status")
                    
                    if response.status_code == 200:
                        status_data = response.json()
                        status = status_data.get("status", "unknown")
                        
                        print(f"   Attempt {attempt}/{MAX_POLL_ATTEMPTS}: Status = {status}")
                        
                        if status == "ready":
                            print("✅ Analysis completed successfully")
                            self.results["completed"] = True
                            self.results["validation_results"]["analysis_status"] = status_data
                            return True
                        elif status == "error":
                            print("❌ Analysis failed with error status")
                            self.results["errors"].append("Analysis status: error")
                            return False
                        elif status == "running":
                            # Continue polling
                            await asyncio.sleep(POLL_INTERVAL_SECONDS)
                            continue
                        else:
                            print(f"⚠️ Unknown status: {status}")
                            await asyncio.sleep(POLL_INTERVAL_SECONDS)
                            continue
                    else:
                        print(f"⚠️ Status check failed: {response.status_code}")
                        await asyncio.sleep(POLL_INTERVAL_SECONDS)
                        continue
                        
            except Exception as e:
                print(f"⚠️ Error checking status (attempt {attempt}): {e}")
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
        
        print(f"❌ Analysis did not complete within {ANALYSIS_TIMEOUT_MINUTES} minutes")
        self.results["errors"].append(f"Timeout after {ANALYSIS_TIMEOUT_MINUTES} minutes")
        return False
    
    async def validate_synergy_types(self) -> bool:
        """Validate that multiple synergy types are detected."""
        print("\n📋 Step 3: Validating synergy types...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.pattern_service_url}/api/v1/synergies/statistics")
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    # Extract by_type counts (handle both data wrapper and direct response)
                    data = stats.get("data", stats)
                    by_type = data.get("by_type", {})
                    total = data.get("total_synergies", data.get("total", 0))
                    
                    device_pair_count = by_type.get("device_pair", 0)
                    device_chain_count = by_type.get("device_chain", 0)
                    event_context_count = by_type.get("event_context", 0)
                    
                    print(f"   Total synergies: {total}")
                    print(f"   device_pair: {device_pair_count}")
                    print(f"   device_chain: {device_chain_count}")
                    print(f"   event_context: {event_context_count}")
                    
                    self.results["validation_results"]["synergy_stats"] = {
                        "total": total,
                        "by_type": by_type
                    }
                    
                    # Success criteria
                    has_device_pair = device_pair_count > 0
                    has_device_chain = device_chain_count > 0
                    has_multiple_types = len([c for c in [device_pair_count, device_chain_count, event_context_count] if c > 0]) >= 2
                    
                    if has_device_pair:
                        print("✅ device_pair synergies detected")
                    else:
                        print("⚠️ No device_pair synergies detected")
                    
                    if has_device_chain:
                        print("✅ device_chain synergies detected")
                    else:
                        print("⚠️ No device_chain synergies detected")
                    
                    if has_multiple_types:
                        print("✅ Multiple synergy types detected")
                    else:
                        print("⚠️ Only one synergy type detected")
                    
                    success = has_multiple_types and (has_device_pair or has_device_chain)
                    
                    if success:
                        print("✅ Synergy type validation PASSED")
                    else:
                        print("❌ Synergy type validation FAILED")
                        self.results["errors"].append("Synergy type validation failed")
                    
                    return success
                else:
                    print(f"❌ Failed to get synergy stats: {response.status_code}")
                    print(f"Response: {response.text}")
                    self.results["errors"].append(f"Stats API error: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error validating synergy types: {e}")
            self.results["errors"].append(f"Validation error: {str(e)}")
            return False
    
    async def validate_ui(self, page: Page) -> bool:
        """Validate UI displays results correctly."""
        print("\n📋 Step 4: Validating UI...")
        
        try:
            # Navigate to patterns page
            print(f"   Navigating to {PATTERNS_PAGE}")
            await page.goto(PATTERNS_PAGE, wait_until="networkidle", timeout=30000)
            
            # Wait for page to load
            await page.wait_for_timeout(2000)
            
            # Check for error messages
            error_selectors = [
                '[role="alert"]',
                '.error',
                '[class*="error"]',
                'text=/error/i'
            ]
            
            errors_found = []
            for selector in error_selectors:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        for element in elements:
                            text = await element.text_content()
                            if text and "error" in text.lower():
                                errors_found.append(text)
                except:
                    pass
            
            if errors_found:
                print(f"⚠️ Errors found in UI: {errors_found}")
                self.results["errors"].extend([f"UI error: {err}" for err in errors_found])
            else:
                print("✅ No error messages in UI")
            
            # Take screenshot
            screenshot_path = Path("implementation/pattern_analysis_ui_validation.png")
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"✅ Screenshot saved: {screenshot_path}")
            
            # Check if patterns/synergies are displayed (basic check)
            page_content = await page.content()
            has_patterns = "pattern" in page_content.lower()
            has_synergies = "synergy" in page_content.lower()
            
            if has_patterns or has_synergies:
                print("✅ Patterns/Synergies content visible in UI")
            else:
                print("⚠️ Patterns/Synergies content not clearly visible")
            
            ui_success = len(errors_found) == 0 and (has_patterns or has_synergies)
            
            if ui_success:
                print("✅ UI validation PASSED")
            else:
                print("❌ UI validation FAILED")
            
            self.results["validation_results"]["ui"] = {
                "errors_found": errors_found,
                "has_patterns": has_patterns,
                "has_synergies": has_synergies,
                "screenshot": str(screenshot_path)
            }
            
            return ui_success
            
        except Exception as e:
            print(f"❌ Error validating UI: {e}")
            self.results["errors"].append(f"UI validation error: {str(e)}")
            return False
    
    async def run(self) -> bool:
        """Run complete automation workflow."""
        print("=" * 80)
        print("Pattern Analysis Re-run Automation")
        print("=" * 80)
        
        # Phase 1: API Execution
        if not await self.check_service_health():
            return False
        
        if not await self.trigger_analysis():
            return False
        
        if not await self.wait_for_completion():
            return False
        
        # Phase 2: API Validation
        synergy_validation = await self.validate_synergy_types()
        
        # Phase 3: UI Validation
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                ui_validation = await self.validate_ui(page)
                
                await browser.close()
            except Exception as e:
                print(f"⚠️ Playwright UI validation failed: {e}")
                self.results["errors"].append(f"Playwright error: {str(e)}")
                ui_validation = False
        
        # Final results
        self.results["success"] = synergy_validation and ui_validation and len(self.results["errors"]) == 0
        
        print("\n" + "=" * 80)
        print("Automation Results")
        print("=" * 80)
        print(f"Success: {self.results['success']}")
        print(f"Triggered: {self.results['triggered']}")
        print(f"Completed: {self.results['completed']}")
        print(f"Synergy Validation: {synergy_validation}")
        print(f"UI Validation: {ui_validation}")
        
        if self.results["errors"]:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        # Save results
        results_path = Path("implementation/pattern_analysis_automation_results.json")
        with open(results_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n✅ Results saved to: {results_path}")
        
        return self.results["success"]


async def main():
    """Main entry point."""
    automation = PatternAnalysisAutomation()
    success = await automation.run()
    
    if success:
        print("\n✅ Automation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Automation completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
