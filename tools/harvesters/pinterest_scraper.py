#!/usr/bin/env python3
"""
Pinterest Harvester for Naval Gallery
Extracts ship/plans/blueprint images from user's Pinterest boards

Requires: playwright (install with `uv add playwright` then `uv run playwright install`)
"""

import os
import sys
import json
import requests
import time
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_staging_dir, get_relative_path, validate_config, DATA_DIR

@dataclass
class PinData:
    id: str
    title: str
    description: str
    url: str
    image_url: str
    board: str
    pinner: str

class PinterestHarvester:
    def __init__(self, session_cookie: str):
        self.session_cookie = session_cookie
        self.base_url = "https://www.pinterest.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    async def get_boards(self, username: str) -> List[Dict]:
        """Get all boards for a user"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Set session cookie to access private boards
            await context.add_cookies([{
                'name': 'pinterest_session',
                'value': self.session_cookie,
                'domain': '.pinterest.com',
                'path': '/'
            }])
            
            page = await context.new_page()
            await page.goto(f"{self.base_url}/{username}/boards/")
            
            # Wait for boards to load
            await page.wait_for_selector('[data-test-id="board-card"]', timeout=10000)
            
            # Extract board information
            boards = await page.evaluate('''
                () => {
                    const boardCards = document.querySelectorAll('[data-test-id="board-card"]');
                    return Array.from(boardCards).map(card => {
                        const link = card.querySelector('a');
                        const img = card.querySelector('img');
                        const title = card.querySelector('[data-test-id="board-card-name"]');
                        
                        return {
                            name: title ? title.innerText.trim() : '',
                            url: link ? link.href : '',
                            thumbnail: img ? img.src : '',
                            pin_count: card.querySelector('[data-test-id="board-card-pin-count"]')?.innerText || '0'
                        };
                    });
                }
            ''')
            
            await browser.close()
            return boards
    
    async def get_board_pins(self, board_url: str) -> List[PinData]:
        """Extract all pins from a specific board"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Set session cookie
            await context.add_cookies([{
                'name': 'pinterest_session',
                'value': self.session_cookie,
                'domain': '.pinterest.com',
                'path': '/'
            }])
            
            page = await context.new_page()
            await page.goto(board_url)
            
            pins = []
            scroll_count = 0
            max_scrolls = 50  # Prevent infinite scrolling
            
            while scroll_count < max_scrolls:
                # Extract current pins
                new_pins = await page.evaluate('''
                    () => {
                        const pinElements = document.querySelectorAll('[data-test-id="pin-visual-wrapper"]');
                        return Array.from(pinElements).map(pin => {
                            const link = pin.querySelector('a[href*="/pin/"]');
                            const img = pin.querySelector('img');
                            const title = img ? img.alt || img.title : '';
                            
                            return {
                                id: link ? link.href.split('/pin/')[1]?.split('/')[0] : '',
                                title: title,
                                description: title,
                                url: link ? link.href : '',
                                image_url: img ? img.src : '',
                                board: window.location.pathname,
                                pinner: ''
                            };
                        }).filter(pin => pin.id && pin.image_url);
                    }
                ''')
                
                # Add new pins (avoid duplicates)
                existing_ids = {pin.id for pin in pins}
                for pin_data in new_pins:
                    if pin_data['id'] not in existing_ids:
                        pins.append(PinData(**pin_data))
                
                # Scroll down for more pins
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)  # Wait for content to load
                
                # Check if we got new content
                current_pin_count = await page.evaluate('document.querySelectorAll("[data-test-id=pin-visual-wrapper]").length')
                if current_pin_count <= len(pins):
                    break
                    
                scroll_count += 1
            
            await browser.close()
            return pins
    
    def filter_naval_content(self, pins: List[PinData]) -> List[PinData]:
        """Filter pins for naval/ship/technical drawing content"""
        naval_keywords = [
            'ship', 'naval', 'boat', 'vessel', 'battleship', 'dreadnought',
            'warship', 'blueprint', 'plans', 'drawing', 'technical', 'architectural',
            'hull', 'profile', 'lines', 'section', 'deck', 'schematic', 'diagram'
        ]
        
        filtered_pins = []
        for pin in pins:
            text_to_check = f"{pin.title} {pin.description}".lower()
            
            # Check if any naval keywords are present
            if any(keyword in text_to_check for keyword in naval_keywords):
                filtered_pins.append(pin)
        
        return filtered_pins
    
    async def download_pin_images(self, pins: List[PinData], staging_dir) -> List[Dict]:
        """Download images for filtered pins"""
        manifest = []
        for pin in pins:
            try:
                # Get highest resolution image
                image_url = pin.image_url
                if '/236x/' in image_url:
                    image_url = image_url.replace('/236x/', '/originals/')
                elif '/736x/' in image_url:
                    image_url = image_url.replace('/736x/', '/originals/')
                
                filename = f"pin_{pin.id}.jpg"
                filepath = staging_dir / filename
                
                # Download image
                if not filepath.exists():
                    response = requests.get(image_url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        print(f"[+] Downloaded: {filename}")
                    else:
                        print(f"[-] Failed to download: {pin.image_url}")
                        continue
                
                # Add to manifest
                manifest.append({
                    "id": f"pinterest_{pin.id}",
                    "title": pin.title or f"Pinterest Pin {pin.id}",
                    "url": pin.url,
                    "desc": pin.description or "From Pinterest",
                    "source": "Pinterest",
                    "board": pin.board,
                    "local_path": get_relative_path("pinterest", filename),
                    "type": self.classify_image_type(pin.title, pin.description)
                })
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"[!] Error processing pin {pin.id}: {e}")
                continue
        
        return manifest
    
    def classify_image_type(self, title: str, description: str) -> str:
        """Classify the type of naval image"""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ['profile', 'side view', 'elevation']):
            return 'profile'
        elif any(word in text for word in ['plan', 'deck', 'top view']):
            return 'deck'
        elif any(word in text for word in ['section', 'cross', 'cutaway']):
            return 'section'
        elif any(word in text for word in ['lines', 'hull lines', 'body plan']):
            return 'lines'
        else:
            return 'general'
    
    async def harvest_user_boards(self, username: str, staging_dir, keywords: List[str] = None) -> Dict:
        """Main harvest function"""
        print(f"[*] Harvesting Pinterest boards for user: {username}")
        
        # Get all boards
        boards = await self.get_boards(username)
        print(f"[*] Found {len(boards)} boards")
        
        # Filter boards by naval keywords if provided
        if keywords:
            naval_boards = [board for board in boards 
                          if any(keyword.lower() in board['name'].lower() 
                                for keyword in keywords)]
        else:
            naval_boards = boards
        
        print(f"[*] Processing {len(naval_boards)} relevant boards")
        
        all_pins = []
        for board in naval_boards:
            print(f"[*] Processing board: {board['name']}")
            pins = await self.get_board_pins(board['url'])
            print(f"    -> Found {len(pins)} pins")
            all_pins.extend(pins)
        
        # Filter for naval content
        naval_pins = self.filter_naval_content(all_pins)
        print(f"[*] Filtered to {len(naval_pins)} naval pins")
        
        # Download images
        manifest = await self.download_pin_images(naval_pins, staging_dir)
        
        # Save manifest
        manifest_path = DATA_DIR / "pinterest_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return {
            'boards_processed': len(naval_boards),
            'total_pins_found': len(all_pins),
            'naval_pins_filtered': len(naval_pins),
            'images_downloaded': len(manifest),
            'manifest_path': str(manifest_path)
        }

async def main():
    # Validate config before doing anything
    validate_config()
    
    STAGING_DIR = get_staging_dir("pinterest")
    
    # You'll need to get your session cookie from browser dev tools
    session_cookie = os.environ.get("PINTEREST_SESSION_COOKIE", "")
    username = os.environ.get("PINTEREST_USERNAME", "")
    
    if not session_cookie or not username:
        print("\n" + "=" * 70)
        print("ERROR: Pinterest credentials not configured!")
        print("=" * 70)
        print()
        print("Set these environment variables:")
        print("    export PINTEREST_SESSION_COOKIE='your_session_cookie'")
        print("    export PINTEREST_USERNAME='your_username'")
        print()
        print("To get your session cookie:")
        print("    1. Log into Pinterest in your browser")
        print("    2. Open Developer Tools (F12)")
        print("    3. Go to Application -> Cookies -> pinterest.com")
        print("    4. Copy the value of '_pinterest_sess' cookie")
        print("=" * 70 + "\n")
        sys.exit(1)
    
    harvester = PinterestHarvester(session_cookie)
    
    # Optional: Filter boards by keywords
    naval_keywords = ['ship', 'naval', 'boats', 'maritime', 'warships', 'plans']
    
    results = await harvester.harvest_user_boards(username, STAGING_DIR, naval_keywords)
    
    print("\n=== PINTEREST HARVEST COMPLETE ===")
    for key, value in results.items():
        print(f"{key}: {value}")

def run():
    """Entry point for run_all.py compatibility"""
    asyncio.run(main())

if __name__ == "__main__":
    run()
