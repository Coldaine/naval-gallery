#!/usr/bin/env python3
"""
Naval Gallery Image Classifier

Uses LLM vision to analyze naval ship images and extract structured metadata.
Aligned with ProjectBroadsideStudio Stage 1 schema for future integration.
"""

import os
import sys
import asyncio
import json
import argparse
import signal
from pathlib import Path

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_absolute_path, validate_config
from vision import MCPVisionClient
import db

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# VISION PROMPTS (BroadsideStudio-aligned)
# ============================================================================

PHASE_1_PROMPT = """
You are analyzing a naval ship blueprint or illustration for an automated processing pipeline.

Examine this image carefully and provide a structured analysis.

## TASK 1: Image Classification
- Is this a single view or multiple views? (single_view, multi_view_stacked, multi_view_grid, photograph, painting)
- For the PRIMARY view, identify:
  - View type: side_profile, plan_view, bow_view, stern_view, cross_section, detail, unknown
  - Style: line_drawing_bw, line_drawing_color, filled_color, shaded, photograph, painting
  - Orientation: bow_left, bow_right, bow_up, bow_down (which direction is the bow facing?)

## TASK 2: Ship Identification
- Ship type: battleship, cruiser, destroyer, submarine, carrier, auxiliary, unknown
- Ship class if recognizable (e.g., "Iowa-class", "Yamato-class")
- Ship name if labeled
- Nation of origin (e.g., "USN", "Royal Navy", "IJN", "Kriegsmarine", "Marine Nationale")
- Era: pre_dreadnought, dreadnought, interwar, wwii, post_war
- Is this a historical ship or hypothetical/fictional design?
- Note any artist/designer attribution visible

## TASK 3: Quality Assessment
- Silhouette clarity: clean (crisp edges), moderate (some noise/blur), noisy (hard to trace)
- Annotation density: none (clean), light (labels only), heavy (dimension callouts, lots of text)
- Resolution: high (detailed), medium (adequate), low (pixelated/blurry)
- Extraction tier (1-5):
  1 = Digital flat-color, clean edges (ideal for extraction)
  2 = Clean scanned line drawings
  3 = Archival documents, paper texture
  4 = Heavy annotations that corrupt geometry
  5 = Photographs/paintings (unsuitable for extraction)
- Is this suitable for automated silhouette extraction?
- List any quality issues: watermark, low_contrast, cropped, damaged, mixed_content

## OUTPUT FORMAT (JSON only, no markdown)
{
  "image_type": "single_view",
  "view_type": "side_profile",
  "view_style": "filled_color",
  "orientation": "bow_left",
  "ship_type": "battleship",
  "ship_class": "Iowa-class",
  "ship_name": "USS Iowa",
  "navy": "USN",
  "era": "wwii",
  "is_historical": true,
  "designer": null,
  "silhouette_clarity": "clean",
  "annotation_density": "light",
  "resolution_quality": "high",
  "extraction_tier": 1,
  "suitable_for_extraction": true,
  "quality_issues": [],
  "reasoning": "Identified by distinctive triple 16-inch turrets and modern superstructure...",
  "confidence": 0.9,
  "notes": "..."
}

Be precise. If uncertain about any field, provide your best guess with lower confidence.
Return ONLY valid JSON, no markdown code blocks.
"""

PHASE_2_PROMPT = """
Examine this naval technical drawing in extreme detail. Extract ALL visible technical information.

This image has already been identified as a naval vessel. Now extract detailed specifications.

## SPECIFICATIONS TO EXTRACT
1. Identification: Ship name, class, hull number, shipyard
2. Physical: Length (LOA/LPP), beam, draft, displacement (standard/full/light)
3. Performance: Propulsion type, horsepower, shafts, max speed (knots)
4. Protection: Belt armor, deck, turrets, conning tower (in mm or inches)
5. Armament: Main battery, secondary, AA, torpedoes, aircraft
6. History: Launch date, commission date
7. Crew: Complement (officers + enlisted)

## OUTPUT FORMAT (JSON only)
{
  "ship_name": "...",
  "ship_class": "...",
  "hull_number": "...",
  "shipyard": "...",
  "dimensions": "LOA 270m, Beam 38m, Draft 10m",
  "displacement": "65,000 tons standard",
  "propulsion": "4 steam turbines, 150,000 SHP, 4 shafts",
  "speed": "27 knots",
  "armor": "Belt: 410mm, Deck: 200mm, Turrets: 650mm",
  "armament": "9x 460mm/45, 12x 155mm, 24x 127mm AA",
  "complement": "2,800",
  "launch_date": "1940-08-08",
  "commission_date": "1941-12-16",
  "reasoning": "Specifications visible in technical annotations...",
  "confidence": 0.8,
  "notes": "..."
}

Extract only what is VISIBLE or clearly labeled. Use null for unavailable fields.
Return ONLY valid JSON, no markdown code blocks.
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
        # Validate config first
        validate_config()
        
        # Get pending work
        if self.phase == 1:
            if retry_failed:
                pending = db.get_failed(limit=limit)
            else:
                pending = db.get_pending(limit=limit)
        else:
            pending = db.get_phase2_pending(limit=limit)
            
        if not pending:
            logger.info("[*] No pending images found.")
            return

        logger.info(f"[*] Starting Phase {self.phase} classification for {len(pending)} images.")

        # Start Vision Client
        async with MCPVisionClient() as client:
            for item in pending:
                if not self.running:
                    break
                
                img_id = item['id']
                local_path = item['local_path']
                
                # Resolve to absolute path
                img_path = get_absolute_path(local_path)
                
                # Check if file exists
                if not img_path.exists():
                    logger.warning(f"[-] Image not found: {img_path}")
                    db.save_analysis(img_id, {}, error=f"File not found: {img_path}")
                    continue

                logger.info(f"[+] Analyzing: {img_id}")
                
                try:
                    result = await client.analyze_image(str(img_path), self.prompt)
                    
                    if result.success:
                        # Extract JSON from LLM response
                        try:
                            # Strip any markdown backticks if present
                            clean_content = result.content.strip()
                            if clean_content.startswith("```"):
                                # Extract content between backticks
                                lines = clean_content.split("\n")
                                json_lines = []
                                in_block = False
                                for line in lines:
                                    if line.startswith("```"):
                                        in_block = not in_block
                                        continue
                                    if in_block or not line.startswith("```"):
                                        json_lines.append(line)
                                clean_content = "\n".join(json_lines)
                            
                            classification = json.loads(clean_content)
                            classification['raw_response'] = result.raw_response
                            
                            # Save to DB
                            db.save_analysis(img_id, classification)
                            
                            # Log summary
                            ship_type = classification.get('ship_type', 'unknown')
                            navy = classification.get('navy', 'unknown')
                            tier = classification.get('extraction_tier', '?')
                            logger.info(f"    -> {ship_type} | {navy} | Tier {tier}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"    -> JSON parse error: {e}")
                            logger.debug(f"    -> Raw content: {result.content[:500]}")
                            db.save_analysis(img_id, {}, error=f"JSON Parse Error: {e}")
                    else:
                        logger.error(f"    -> Vision API error: {result.error}")
                        db.save_analysis(img_id, {}, error=result.error)
                
                except Exception as e:
                    logger.exception(f"    -> Unexpected error: {e}")
                    db.save_analysis(img_id, {}, error=str(e))
                
                # Rate limiting
                await asyncio.sleep(0.5)


async def main():
    parser = argparse.ArgumentParser(description="Naval Gallery Image Classifier")
    parser.add_argument("--phase", type=int, default=1, choices=[1, 2], help="Analysis phase (1=classify, 2=enrich)")
    parser.add_argument("--limit", type=int, default=None, help="Max images to process")
    parser.add_argument("--retry-failed", action="store_true", help="Retry images that failed previously")
    parser.add_argument("--export", type=str, help="Export database to JSON manifest")
    parser.add_argument("--import-manifest", type=str, help="Import JSON manifest into database")
    parser.add_argument("--migrate", action="store_true", help="Run database migration for new columns")
    parser.add_argument("--sync", action="store_true", help="Sync database to frontend (images.js)")
    
    args = parser.parse_args()

    if args.migrate:
        db.init_db()
        db.migrate_db()
        return

    if args.import_manifest:
        db.init_db()
        db.migrate_db()
        db.import_manifest(args.import_manifest)
        return

    if args.export:
        db.export_manifest(args.export)
        return

    if args.sync:
        db.sync_frontend()
        return

    # Normal execution
    db.init_db()
    db.migrate_db()  # Ensure new columns exist
    
    classifier = Classifier(phase=args.phase)
    await classifier.run(limit=args.limit, retry_failed=args.retry_failed)
    
    # Auto-sync after classification run
    db.sync_frontend()


if __name__ == "__main__":
    asyncio.run(main())
