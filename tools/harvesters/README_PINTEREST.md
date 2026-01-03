# Pinterest Integration Setup Guide

## Getting Your Pinterest Session Cookie

### Method 1: Browser Developer Tools (Recommended)
1. **Open Pinterest** in your browser and log in
2. **Open Developer Tools** (F12 or Ctrl+Shift+I)
3. **Go to Application/Storage tab**
4. **Find Cookies** → pinterest.com
5. **Locate `pinterest_session` cookie**
6. **Copy the value** (long alphanumeric string)

### Method 2: Browser Extension
1. Install "EditThisCookie" or similar extension
2. Go to pinterest.com
3. Click the extension icon
4. Find `pinterest_session` and copy its value

## Configuration

### Edit `pinterest_scraper.py`
```python
# Replace these with your actual values:
session_cookie = "paste_your_session_cookie_here"
username = "your_pinterest_username"
```

### Optional: Board Filtering
```python
# Filter to only boards with these keywords in the name:
naval_keywords = ['ship', 'naval', 'boats', 'maritime', 'warships', 'plans', 'blueprints']
```

## Running the Harvester

```bash
# Install dependencies first
pip install playwright requests asyncio
playwright install chromium

# Run the Pinterest scraper
python tools/harvesters/pinterest_scraper.py

# Or run all harvesters including Pinterest
python tools/run_all.py
```

## What It Does

1. **Accesses your private boards** using the session cookie
2. **Scrolls through all pins** on each board (handles infinite scroll)
3. **Filters for naval content** using keyword matching
4. **Downloads high-res images** (converts thumbnail URLs to original size)
5. **Generates manifest** compatible with your existing system
6. **Integrates automatically** with `run_all.py`

## Features

- ✅ **Private board access** (requires your session cookie)
- ✅ **Smart content filtering** for naval/technical content
- ✅ **High-resolution downloads** (original image URLs)
- ✅ **Rate limiting** to be respectful to Pinterest
- ✅ **Duplicate detection** across boards
- ✅ **Type classification** (profile, deck, section, lines, general)
- ✅ **Seamless integration** with existing pipeline

## Expected Output

```
[*] Harvesting Pinterest boards for user: your_username
[*] Found 15 boards
[*] Processing 5 relevant boards
[*] Processing board: Naval Blueprints
    -> Found 234 pins
[*] Processing board: Ship Plans
    -> Found 156 pins
[*] Filtered to 89 naval pins
[+] Downloaded: pin_1234567890.jpg
[+] Downloaded: pin_9876543210.jpg
...
[*] Filtered to 89 naval pins
[*] Downloaded 85 images

=== PINTEREST HARVEST COMPLETE ===
boards_processed: 5
total_pins_found: 890
naval_pins_filtered: 89
images_downloaded: 85
manifest_path: ../data/pinterest_manifest.json
```

## Integration Results

The Pinterest harvester will create:
- `img/pinterest/` - Downloaded images
- `data/pinterest_manifest.json` - Metadata for integration
- Automatically appears in your master manifest and gallery

## Legal Considerations

- ✅ Uses your **own private content** that you pinned
- ✅ Respects Pinterest's **rate limits**
- ✅ Downloads only **publicly available** images
- ✅ For **personal/research use** only

## Troubleshooting

### "Session expired"
- Your session cookie has expired
- Log back into Pinterest and get a fresh cookie

### "No boards found"
- Check that the username is correct
- Ensure the session cookie is valid

### "Rate limited"
- Pinterest is limiting requests
- Increase delays in the script
- Try again later

## Advanced Options

### Alternative: Pinterest API
If you prefer the official API route:
1. Create app at [developers.pinterest.com](https://developers.pinterest.com/)
2. Get OAuth tokens
3. Use `pinterest-api-sdk` package
4. More reliable but requires app approval

### Alternative: Apify Services
For no-maintenance solution:
- Use Apify Pinterest Board Downloader
- $2.50 per 1,000 results
- No coding required
