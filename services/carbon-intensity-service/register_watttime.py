"""
WattTime Registration Helper Script
Use this to register a new WattTime account programmatically
"""

import asyncio
import sys

import aiohttp


async def register_watttime(username: str, password: str, email: str, org: str):
    """
    Register a new WattTime account
    
    Args:
        username: Desired username (must be unique)
        password: Strong password
        email: Valid email address
        org: Organization name
        
    Returns:
        bool: True if registration successful
    """

    url = "https://api.watttime.org/register"

    data = {
        "username": username,
        "password": password,
        "email": email,
        "org": org
    }

    print("\n🔐 Registering WattTime Account")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Organization: {org}")
    print(f"   API: {url}")
    print()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                response_text = await response.text()

                if response.status == 200 or response.status == 201:
                    print("✅ Registration Successful!")
                    print(f"   Response: {response_text}")
                    print()
                    print("📧 Check your email for verification (if required)")
                    print()
                    print("🔑 Testing login with new credentials...")

                    # Test login immediately
                    login_success = await test_login(username, password)

                    if login_success:
                        print("✅ Login test successful! Your credentials work.")
                        print()
                        print("📝 Add to your .env file:")
                        print(f"   WATTTIME_USERNAME={username}")
                        print("   WATTTIME_PASSWORD=your_password")
                    else:
                        print("⚠️  Registration succeeded but login test failed.")
                        print("   You may need to verify your email first.")

                    return True

                elif response.status == 400:
                    print("❌ Registration Failed (400 Bad Request)")
                    print(f"   Response: {response_text}")
                    print()
                    print("💡 Common Issues:")
                    print("   - Username already taken")
                    print("   - Invalid email format")
                    print("   - Password too weak")
                    print("   - Missing required fields")
                    return False

                else:
                    print(f"❌ Registration Failed (HTTP {response.status})")
                    print(f"   Response: {response_text}")
                    return False

    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return False


async def test_login(username: str, password: str):
    """Test login with credentials"""

    url = "https://api.watttime.org/v3/login"

    try:
        auth = aiohttp.BasicAuth(username, password)

        async with aiohttp.ClientSession() as session:
            async with session.post(url, auth=auth) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get('token', '')
                    print(f"   Token received: {token[:30]}...")
                    return True
                else:
                    print(f"   Login failed: HTTP {response.status}")
                    return False

    except Exception as e:
        print(f"   Login error: {e}")
        return False


async def check_username_available(username: str):
    """Check if username is available"""

    # Try to login with fake password - if we get 401, username exists
    url = "https://api.watttime.org/v3/login"

    try:
        auth = aiohttp.BasicAuth(username, "fake_password_12345")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, auth=auth) as response:
                if response.status == 401:
                    print(f"⚠️  Username '{username}' already exists")
                    return False
                elif response.status == 404:
                    print(f"✅ Username '{username}' appears to be available")
                    return True
                else:
                    print(f"❓ Unknown response: {response.status}")
                    return None

    except Exception as e:
        print(f"Error checking username: {e}")
        return None


def print_usage():
    """Print usage instructions"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║          WattTime Account Registration Helper               ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
    python register_watttime.py <username> <password> <email> <org>

EXAMPLE:
    python register_watttime.py myuser SecurePass123 me@email.com "Home Project"

REQUIREMENTS:
    - Username: Must be unique, alphanumeric
    - Password: Strong password (8+ characters)
    - Email: Valid email address
    - Org: Your organization name

NOTES:
    - This registers you for WattTime's FREE tier
    - Free tier includes 1-2 US regions
    - After registration, add credentials to .env file
    - Credentials are used for automatic token refresh

MANUAL REGISTRATION:
    If this script doesn't work, register manually at:
    https://watttime.org

    Then add your credentials to .env:
    WATTTIME_USERNAME=your_username
    WATTTIME_PASSWORD=your_password
""")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print_usage()
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3]
    org = sys.argv[4]

    # Run registration
    success = asyncio.run(register_watttime(username, password, email, org))

    if success:
        print()
        print("🎉 Registration Complete!")
        print()
        print("NEXT STEPS:")
        print("1. Add credentials to your .env file or docker-compose.yml")
        print("2. Restart carbon-intensity service:")
        print("   docker-compose up -d carbon-intensity")
        print("3. Verify service health:")
        print("   curl http://localhost:8010/health")
        print()
        sys.exit(0)
    else:
        print()
        print("❌ Registration failed. Please try manual registration at:")
        print("   https://watttime.org")
        print()
        sys.exit(1)

