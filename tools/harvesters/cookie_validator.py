#!/usr/bin/env python3
"""
Pinterest Cookie Helper - Test and verify your Pinterest session cookie
"""

import requests
import json
import sys
import re

def test_pinterest_cookie(cookie_value, username):
    """Test if Pinterest session cookie works and get user info"""
    headers = {
        'Cookie': f'pinterest_session={cookie_value}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # Test 1: Access profile page
        profile_url = f"https://www.pinterest.com/{username}/"
        print(f"[*] Testing profile access: {profile_url}")
        
        response = requests.get(profile_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Test 2: Check if we're logged in (look for logged-in user elements)
            if 'Log out' in response.text or 'Settings' in response.text:
                print("✅ SUCCESS: Cookie works! You're logged in")
                
                # Test 3: Try to access boards
                boards_url = f"https://www.pinterest.com/{username}/boards/"
                boards_response = requests.get(boards_url, headers=headers, timeout=10)
                
                if boards_response.status_code == 200:
                    # Count boards to verify deep access
                    if 'data-test-id="board-card"' in boards_response.text:
                        board_count = boards_response.text.count('data-test-id="board-card"')
                        print(f"✅ Boards access confirmed: {board_count} boards found")
                        return True
                    else:
                        print("⚠️  Boards access may be limited")
                        return True
                else:
                    print(f"❌ Boards access failed: {boards_response.status_code}")
                    return False
            else:
                print("❌ Cookie invalid - not logged in")
                return False
        else:
            print(f"❌ Profile access failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - check internet connection")
        return False
    except Exception as e:
        print(f"❌ Error testing cookie: {e}")
        return False

def get_user_info(cookie_value):
    """Extract basic user info from Pinterest"""
    headers = {
        'Cookie': f'pinterest_session={cookie_value}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get('https://www.pinterest.com/settings/account', headers=headers, timeout=10)
        if response.status_code == 200:
            # Extract username and email (if visible in page source)
            import re
            
            username_match = re.search(r'"username":"([^"]+)"', response.text)
            email_match = re.search(r'"email":"([^"]+)"', response.text)
            
            info = {}
            if username_match:
                info['username'] = username_match.group(1)
            if email_match:
                info['email'] = email_match.group(1)
                
            return info
    except Exception as e:
        print(f"[!] Could not extract user info: {e}")
        return {}

def main():
    print("=== Pinterest Cookie Validator ===")
    print()
    
    if len(sys.argv) == 3:
        cookie_value = sys.argv[1]
        username = sys.argv[2]
    else:
        print("Usage: python cookie_validator.py <cookie_value> <username>")
        print()
        print("Example: python cookie_validator.py 'AQIDAX...your_cookie_here...' 'johndoe'")
        print()
        print("Get your cookie from:")
        print("1. Chrome: F12 → Application → Cookies → pinterest.com → pinterest_session")
        print("2. Firefox: F12 → Storage → Cookies → pinterest.com → pinterest_session")
        print()
        return
    
    print(f"Username: {username}")
    print(f"Cookie: {cookie_value[:20]}...{cookie_value[-20:]}")
    print()
    
    # Test the cookie
    if test_pinterest_cookie(cookie_value, username):
        print("\n=== USER INFO ===")
        user_info = get_user_info(cookie_value)
        for key, value in user_info.items():
            print(f"{key}: {value}")
        
        print("\n=== READY FOR HARVESTING ===")
        print("Your cookie is working! Update pinterest_scraper.py:")
        print(f'session_cookie = "{cookie_value}"')
        print(f'username = "{username}"')
        print()
        print("Then run: python tools/harvesters/pinterest_scraper.py")
    else:
        print("\n=== COOKIE INVALID ===")
        print("Please:")
        print("1. Log out of Pinterest")
        print("2. Log back in")
        print("3. Extract a fresh cookie")
        print("4. Try this validator again")

if __name__ == "__main__":
    main()
