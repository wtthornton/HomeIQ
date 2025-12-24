#!/usr/bin/env python3
"""
Direct Weather API Test

This script tests the weather API key directly to diagnose issues.
"""

import requests
import os
from dotenv import load_dotenv

def test_weather_api():
    """Test the weather API key directly"""
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('WEATHER_API_KEY')
    
    if not api_key:
        print("[ERROR] No weather API key found in environment variables")
        return False
    
    print(f"[INFO] Testing Weather API Key: {api_key[:10]}...")
    print(f"[INFO] Full Key: {api_key}")
    
    # Test with a simple request
    url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': 'London,UK',
        'appid': api_key,
        'units': 'metric'
    }
    
    print(f"[INFO] Making request to: {url}")
    print(f"[INFO] Parameters: q=London,UK, units=metric")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"[INFO] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("[SUCCESS] Weather API key is valid!")
            print(f"[INFO] Location: {data.get('name', 'Unknown')}")
            print(f"[INFO] Temperature: {data.get('main', {}).get('temp', 'Unknown')}°C")
            print(f"[INFO] Weather: {data.get('weather', [{}])[0].get('main', 'Unknown')}")
            return True
            
        elif response.status_code == 401:
            print("[ERROR] Invalid API key")
            print("[SOLUTION] Get a new API key from https://openweathermap.org/api")
            print(f"[RESPONSE] {response.text}")
            return False
            
        elif response.status_code == 403:
            print("[ERROR] API key valid but access forbidden")
            print("[SOLUTION] Check your OpenWeatherMap subscription/plan")
            print(f"[RESPONSE] {response.text}")
            return False
            
        elif response.status_code == 429:
            print("[WARNING] Rate limit exceeded")
            print("[SOLUTION] Wait before making more requests")
            print(f"[RESPONSE] {response.text}")
            return False
            
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            print(f"[RESPONSE] {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("[ERROR] Request timeout")
        print("[SOLUTION] Check your internet connection")
        return False
        
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection error")
        print("[SOLUTION] Check your internet connection")
        return False
        
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def test_multiple_locations():
    """Test the API with multiple locations to check quota"""
    
    load_dotenv()
    api_key = os.getenv('WEATHER_API_KEY')
    
    if not api_key:
        return False
    
    print("\n[INFO] Testing multiple locations to check API quota...")
    
    locations = ['London,UK', 'Paris,FR', 'Tokyo,JP']
    successful = 0
    
    for location in locations:
        try:
            url = 'https://api.openweathermap.org/data/2.5/weather'
            params = {
                'q': location,
                'appid': api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                temp = data.get('main', {}).get('temp', 'Unknown')
                print(f"  [PASS] {location}: {temp}°C")
                successful += 1
            elif response.status_code == 429:
                print(f"  [WARN] {location}: Rate limit exceeded")
                break
            else:
                print(f"  [FAIL] {location}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [ERROR] {location}: Error - {e}")
    
    print(f"\n[INFO] Quota Test Results: {successful}/{len(locations)} successful")
    return successful > 0

if __name__ == "__main__":
    print("=" * 60)
    print("WEATHER API DIRECT TEST")
    print("=" * 60)
    
    # Test basic API functionality
    success = test_weather_api()
    
    # Test quota if basic test worked
    if success:
        test_multiple_locations()
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Weather API is working correctly!")
    else:
        print("[INFO] Weather API needs attention - check the errors above")
    print("=" * 60)
