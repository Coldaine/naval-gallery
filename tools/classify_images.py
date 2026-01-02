#!/usr/bin/env python3
import os
import asyncio
import json
import argparse
import signal
import sys
from pathlib import Path
from vision import MCPVisionClient
import db

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Prompts ---

PHASE_1_PROMPT = """
Analyze this naval technical drawing or photograph. Identify:
1. Ship type (battleship, cruiser, destroyer, submarine, carrier, auxiliary)
2. View type (plan view, profile/side view, lines drawing, photograph, cutaway, other)
3. Navy of origin if identifiable (e.g., USN, Royal Navy, IJN, Kriegsmarine)
4. Era (pre-dreadnought, dreadnought, interwar, WWII, post-war)

Respond ONLY in JSON format:
{
  "ship_type": "...",
  "view_type": "...",
  "navy": "...",
  "era": "...",
  "confidence": "low|medium|high",
  "notes": "..."
}
"""

PHASE_2_PROMPT = """
Examine this naval technical drawing in detail. Extract ALL visible technical information:

1. Ship identification: Individual ship name, class, hull number.
2. Dimensions: Length, beam, draft (if labeled).
3. Armament: Main battery, secondary guns, torpedo tubes, etc.
4. Displacement: Standard and full load tonnage (if labeled).
5. Technical features: Propulsion, armor notes, specific design dates.
6. Attribution: Artist name, source collection, or archive labels.

Respond ONLY in detailed JSON format:
{
  "ship_name": "...",
  "ship_class": "...",
  "hull_number": "...",
  "dimensions": "...",
  "armament": "...",
  "displacement": "...",
  "technical_features": "...",
  "attribution": "...",
  "confidence": "low|medium|high",
  "notes": "..."
}
"""

class Classifier:
    def __init__(self, phase=1):
        self.phase = phase
        self.prompt = PHASE_1_PROMPT if phase == 1 else PHASE_2_PROMPT
        self.running = True
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def stop(self, signum, frame):
        logger.info("[!] Stopping classification...")
        self.running = False

    async def run(self, limit=None, retry_failed=False):
        # 1. Get pending work
        pending = db.get_pending(limit=limit)
        if not pending:
            logger.info("[*] No pending images found.")
            return

        logger.info(f"[*] Starting Phase {self.phase} classification for {len(pending)} images.")

        # 2. Start Vision Client
        async with MCPVisionClient() as client:
            for item in pending:
                if not self.running:
                    break
                
                img_id = item['id']
                img_path = item['local_path']
                
                # Check if file exists
                if not os.path.exists(img_path):
                    logger.warning(f"[-] Image not found: {img_path}")
                    db.save_analysis(img_id, {}, error="File not found")
                    continue

                logger.info(f"[+] Analyzing: {img_id} ({img_path})")
                
                try:
                    result = await client.analyze_image(img_path, self.prompt)
                    
                    if result.success:
                        # Extract JSON from LLM response
                        try:
                            # Strip any markdown backticks if present
                            clean_content = result.content.strip()
                            if clean_content.startswith("```"):
                                clean_content = clean_content.split("```")[1]
                                if clean_content.startswith("json"):
                                    clean_content = clean_content[4:]
                            
                            classification = json.loads(clean_content)
                            classification['raw_response'] = result.raw_response
                            
                            # Save to DB
                            db.save_analysis(img_id, classification)
                            logger.info(f"    -> Success: {classification.get('ship_type', 'Unknown')} | {classification.get('navy', 'Unknown')}")
                        except json.JSONDecodeError:
                            logger.error(f"    -> Failed to parse LLM Response: {result.content}")
                            db.save_analysis(img_id, {}, error="JSON Parse Error")
                    else:
                        logger.error(f"    -> Vision API error: {result.error}")
                        db.save_analysis(img_id, {}, error=result.error)
                
                except Exception as e:
                    logger.exception(f"    -> Unexpected error: {e}")
                    db.save_analysis(img_id, {}, error=str(e))
                
                # Small sleep to be kind to the API/Subprocess
                await asyncio.sleep(0.5)

async def main():
    parser = argparse.ArgumentParser(description="Naval Gallery Image Classifier (Z.ai Vision)")
    parser.add_argument("--phase", type=int, default=1, choices=[1, 2], help="Analysis phase")
    parser.add_argument("--limit", type=int, default=None, help="Max images to process")
    parser.add_argument("--retry-failed", action="store_true", help="Retry images that failed previously")
    parser.add_argument("--export", type=str, help="Export database to JSON manifest")
    parser.add_argument("--import-manifest", type=str, help="Import JSON manifest into database")
    
    args = parser.parse_args()

    # db relative path handling
    base_dir = Path(__file__).parent.parent
    if args.import_manifest:
        db.init_db()
        db.import_manifest(args.import_manifest)
        return

    if args.export:
        db.export_manifest(args.export)
        return

    # Normal execution
    db.init_db() # Ensure DB exists
    classifier = Classifier(phase=args.phase)
    await classifier.run(limit=args.limit, retry_failed=args.retry_failed)

if __name__ == "__main__":
    asyncio.run(main())
