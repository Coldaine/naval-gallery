# Pinterest Session Cookie Extraction Guide (2025)

## Method 1: Chrome Developer Tools (Recommended)

### Step 1: Log into Pinterest
1. Open [https://www.pinterest.com](https://www.pinterest.com) in Chrome
2. Click "Log in" and enter your credentials
3. Wait for the page to fully load after login

### Step 2: Open Developer Tools
1. Press **F12** (or Ctrl+Shift+I) to open Developer Tools
2. Click on the **"Application"** tab
3. In the left sidebar, expand **"Storage"** → **"Cookies"** → **"https://www.pinterest.com"**

### Step 3: Find and Copy the Session Cookie
1. Scroll through the cookie list to find **"pinterest_session"**
2. Click on it to expand the details
3. Copy the **"Value"** field (this is your session cookie)
4. It will be a long alphanumeric string like: `AQIDAX...` (100+ characters)

### Step 4: Test the Cookie
```python
# Quick test script to verify your cookie works
import requests

session_cookie = "paste_your_cookie_here"
headers = {
    'Cookie': f'pinterest_session={session_cookie}',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get('https://www.pinterest.com/settings', headers=headers)
if response.status_code == 200:
    print("✅ Cookie works!")
else:
    print("❌ Cookie failed - try getting a fresh one")
```

## Method 2: Firefox Developer Tools

### Step 1: Log into Pinterest
1. Open Pinterest in Firefox and log in
2. Wait for the page to fully load

### Step 2: Open Developer Tools
1. Press **F12** (or Ctrl+Shift+I) to open Developer Tools
2. Click on the **"Storage"** tab
3. Expand **"Cookies"** → **"https://www.pinterest.com"**

### Step 3: Copy Session Cookie
1. Find **"pinterest_session"** in the cookie list
2. Right-click on it and select **"Copy Value"**
3. Paste this into your script

## Method 3: Browser Extension (Easiest)

### Install Extension
- Chrome: "EditThisCookie" or "Cookie-Editor"
- Firefox: "Cookie Quick Manager" or "EditThisCookie"

### Extract Cookie
1. Go to pinterest.com and log in
2. Click the extension icon
3. Search for "pinterest_session"
4. Copy the value field

## What the Pinterest Session Cookie Looks Like

The `pinterest_session` cookie value typically looks like:
```
AQIDAX...AbCdEf123456789...very_long_string...with_numbers_and_letters...XYZ
```
- Usually 100-500 characters long
- Contains letters, numbers, and some special characters
- **This is NOT your password** - it's a session identifier

## Visual Guide (Chrome)

```
┌─────────────────────────────────────────────────┐
│ Chrome Developer Tools                   │
│ ┌───────────────┬─────────────────────┐ │
│ │ Application    │ pinterest_session    │ │
│ │ ▼ Storage      │ ┌─────────────────┐ │ │
│ │ ▼ Cookies      │ │ Name          │ │ │
│ │ ▼ https://...  │ │ pinterest_session│ │ │
│ │               │ │ Value          │ │ │
│ │ pinterest_...  │ │ AQIDAX...      │ │ │
│ │ pinterest_...  │ │               │ │ │
│ │ pinterest_...  │ │ ← COPY THIS   │ │ │
│ │ pinterest_...  │ │ VALUE HERE     │ │ │
│ └───────────────┴─────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Quick Verification Script

Create a file `test_cookie.py`:

```python
#!/usr/bin/env python3
import requests

def test_pinterest_cookie(cookie_value):
    """Test if your Pinterest session cookie works"""
    headers = {
        'Cookie': f'pinterest_session={cookie_value}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get('https://www.pinterest.com/settings', headers=headers, timeout=10)
        if response.status_code == 200 and 'Log out' in response.text:
            print("✅ SUCCESS: Cookie is valid!")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    cookie = input("Paste your pinterest_session cookie value: ").strip()
    test_pinterest_cookie(cookie)
```

Run it:
```bash
python test_cookie.py
```

## Security Notes

✅ **Safe to use:**
- This is YOUR session cookie for YOUR account
- It's not a password or sensitive credential
- Only allows access to what you can already see

❌ **Never share:**
- Don't commit cookie to git repositories
- Don't post in public forums
- Regenerate if accidentally shared

## Cookie Lifetime

- Session cookies typically **expire after hours/days**
- If you get "session expired", just log out and log back in
- Get a fresh cookie value from the same process

## Troubleshooting

### "Can't find pinterest_session cookie"
- Make sure you're fully logged in
- Refresh the page and check Application tab again
- Try a different browser

### "Cookie doesn't work"
- Cookie may have expired - log in again
- Make sure you copied the entire value
- Check for extra spaces or line breaks

### "Access denied"
- Pinterest may have detected automation
- Wait a few minutes and try again
- Use the cookie soon after extracting

## Integration with Your Harvester

Once you have your cookie, update the scraper:

```python
# In pinterest_scraper.py, line 111
session_cookie = "paste_your_actual_cookie_here"
username = "your_pinterest_username"  # Only the part after pinterest.com/
```

Example:
```python
session_cookie = "AQIDAX7nwMwAAABaMSYwZmM3MzZhN..."
username = "johndoe"  # If your profile is pinterest.com/johndoe
```

## Testing Your Setup

1. **Extract cookie** using one of the methods above
2. **Run test script** to verify it works
3. **Update the harvester** with your values
4. **Run a small test** first to make sure everything works
5. **Scale up** to harvest all your naval boards

The cookie method gives you access to **ALL your private boards** that aren't visible to public scrapers - perfect for your curated collection!
