#!/usr/bin/env python3
"""
Build the BookSearch promo video.

Assembles text slides (Veo-animated) and screenshot galleries
into the final promo video.

Usage:
    python data/promo/build_promo.py                # Full build with Veo
    python data/promo/build_promo.py --no-veo       # Free zoom-out fallback
    python data/promo/build_promo.py --test-slide   # Generate only first slide (for testing)

Requires:
    - Screenshots captured first: python data/promo/capture_journeys.py
    - pip install Pillow google-genai
    - brew install ffmpeg
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Add promo dir to path for import
sys.path.insert(0, str(Path(__file__).parent))
from promo_generator import PromoVideoGenerator

PROMO_DIR = Path(__file__).parent
OUTPUT_DIR = PROMO_DIR
SCREENSHOTS_DIR = PROMO_DIR / "screenshots"
SOUNDTRACK_DIR = PROMO_DIR / "soundtrack"
FINAL_VIDEO = PROMO_DIR / "booksearch_promo.mp4"

SOUNDTRACK_PROMPT = (
    "Modern cinematic tech promo instrumental, driving synth pulses "
    "with crisp percussive elements, confident and bold, "
    "building momentum from start, sleek digital production, "
    "premium SaaS product launch feel, sharp transitions, "
    "energetic but polished, no vocals"
)


# ============================================================
# STORYBOARD (from docs/Booksearch video slides.md)
# ============================================================

SLIDES = [
    # --- Opening: Problem statement ---
    {
        "id": "01_stat_punch",
        "main": "56% of your customers\ndon't know what they want",
        "subtitle": None,
        "duration": 4.0,
    },
    {
        "id": "02_deeper_problem",
        "main": "And they can't tell you\neven if you ask",
        "subtitle": '"Something good." "A page-turner." "Not too long."',
        "duration": 4.0,
    },
    {
        "id": "03_what_this_means",
        "main": "They browse. They hesitate. They leave",
        "subtitle": "Your search bar can't help them",
        "duration": 4.0,
    },
    {
        "id": "04_the_shift",
        "main": "But the right questions can",
        "subtitle": None,
        "duration": 4.0,
    },
    {
        "id": "05_how_it_works",
        "main": "BookSearch doesn't wait\nfor the perfect query",
        "subtitle": "It asks. It narrows. It finds.",
        "duration": 4.0,
    },
    # --- Journey labels ---
    {
        "id": "06_j1_label",
        "main": "\"A book I loved\"",
        "subtitle": "Journey 1 of 3",
        "duration": 4.0,
    },
    {
        "id": "08_j2_label",
        "main": "\"It's a gift\"",
        "subtitle": "Journey 2 of 3",
        "duration": 4.0,
    },
    {
        "id": "10_j3_label",
        "main": "\"Surprise me\"",
        "subtitle": "Journey 3 of 3",
        "duration": 4.0,
    },
    # --- Closing ---
    {
        "id": "12_mechanism",
        "main": "3 smart questions.\n3 perfect books",
        "subtitle": "From \"surprise me\" to \"I'll take it\"",
        "duration": 4.0,
    },
    {
        "id": "13_result",
        "main": "Turn browsers into buyers",
        "subtitle": None,
        "duration": 4.0,
    },
    {
        "id": "14_cta",
        "main": "BookSearch",
        "subtitle": "Discovery that sells",
        "duration": 4.0,
    },
]


def find_conversation_screenshots(prefix):
    """Find conversation screenshots (excluding recs closeup)."""
    shots = sorted(SCREENSHOTS_DIR.glob(f"{prefix}_*.png"))
    return [str(s) for s in shots if "closeup" not in s.name]


def find_recs_closeup(prefix):
    """Find the recommendation close-up screenshot."""
    shots = list(SCREENSHOTS_DIR.glob(f"{prefix}_recs_closeup.png"))
    return [str(s) for s in shots]


def make_slide(gen, slide, segments_dir, use_veo):
    """Generate a single animated text slide, return path."""
    path = str(segments_dir / f"{slide['id']}.mp4")
    if not Path(path).exists():
        gen.create_animated_slide(
            slide["main"], path, duration=slide["duration"],
            subtitle=slide["subtitle"], use_veo=use_veo
        )
    return path


def test_first_slide(use_veo=True):
    """Generate only the first slide for testing styling."""
    gen = PromoVideoGenerator(output_dir=str(OUTPUT_DIR))
    segments_dir = OUTPUT_DIR / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    slide = SLIDES[0]
    # Override to 2s for quick test
    path = str(segments_dir / "test_slide.mp4")
    if Path(path).exists():
        Path(path).unlink()

    gen.create_animated_slide(
        slide["main"], path, duration=2.0,
        subtitle=slide["subtitle"], use_veo=use_veo
    )

    if Path(path).exists():
        size_kb = Path(path).stat().st_size / 1024
        print(f"\n✅ Test slide ready: {path} ({size_kb:.0f} KB)")
    else:
        print("\n❌ Failed to generate test slide")


def build_promo(use_veo=True, use_music=True):
    """Build the complete promo video."""
    gen = PromoVideoGenerator(output_dir=str(OUTPUT_DIR))
    segments_dir = OUTPUT_DIR / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    # Verify screenshots exist
    all_screenshots = list(SCREENSHOTS_DIR.glob("*.png"))
    if not all_screenshots:
        print("❌ No screenshots found!")
        print("   Run first: python promo/capture_journeys.py")
        return

    print(f"Found {len(all_screenshots)} screenshots in {SCREENSHOTS_DIR}")
    segments = []

    # ----------------------------------------------------------
    # Slides 1-5: Opening problem statement
    # ----------------------------------------------------------
    for slide in SLIDES[:5]:
        segments.append(make_slide(gen, slide, segments_dir, use_veo))

    # ----------------------------------------------------------
    # Journey 1: label → conversation → recs closeup
    # ----------------------------------------------------------
    segments.append(make_slide(gen, SLIDES[5], segments_dir, use_veo))

    conv_shots = find_conversation_screenshots("j1")
    if conv_shots:
        path = str(segments_dir / "j1_conversation.mp4")
        if not Path(path).exists():
            gen.create_quick_gallery(
                conv_shots, path, duration_per_image=10.0, crossfade=0.5
            )
        segments.append(path)

    recs_shots = find_recs_closeup("j1")
    if recs_shots:
        path = str(segments_dir / "j1_recs_closeup.mp4")
        if not Path(path).exists():
            gen.create_quick_gallery(
                recs_shots, path, duration_per_image=16.0, crossfade=0.5
            )
        segments.append(path)

    # ----------------------------------------------------------
    # Journey 2: label → conversation → recs closeup
    # ----------------------------------------------------------
    segments.append(make_slide(gen, SLIDES[6], segments_dir, use_veo))

    conv_shots = find_conversation_screenshots("j2")
    if conv_shots:
        path = str(segments_dir / "j2_conversation.mp4")
        if not Path(path).exists():
            gen.create_quick_gallery(
                conv_shots, path, duration_per_image=10.0, crossfade=0.5
            )
        segments.append(path)

    recs_shots = find_recs_closeup("j2")
    if recs_shots:
        path = str(segments_dir / "j2_recs_closeup.mp4")
        if not Path(path).exists():
            gen.create_quick_gallery(
                recs_shots, path, duration_per_image=16.0, crossfade=0.5
            )
        segments.append(path)

    # ----------------------------------------------------------
    # Journey 3: label → conversation → recs closeup
    # ----------------------------------------------------------
    segments.append(make_slide(gen, SLIDES[7], segments_dir, use_veo))

    conv_shots = find_conversation_screenshots("j3")
    if conv_shots:
        path = str(segments_dir / "j3_conversation.mp4")
        if not Path(path).exists():
            gen.create_quick_gallery(
                conv_shots, path, duration_per_image=10.0, crossfade=0.5
            )
        segments.append(path)

    recs_shots = find_recs_closeup("j3")
    if recs_shots:
        path = str(segments_dir / "j3_recs_closeup.mp4")
        if not Path(path).exists():
            gen.create_quick_gallery(
                recs_shots, path, duration_per_image=16.0, crossfade=0.5
            )
        segments.append(path)

    # ----------------------------------------------------------
    # Slides 9-11: Closing (mechanism, result, CTA)
    # ----------------------------------------------------------
    for slide in SLIDES[8:]:
        segments.append(make_slide(gen, slide, segments_dir, use_veo))

    # ----------------------------------------------------------
    # Final assembly
    # ----------------------------------------------------------
    segments = [s for s in segments if Path(s).exists()]

    if not segments:
        print("❌ No segments generated!")
        return

    print(f"\n{'='*60}")
    print(f"Assembling {len(segments)} segments into final video...")
    print(f"{'='*60}")

    for i, seg in enumerate(segments):
        print(f"  {i+1:2d}. {Path(seg).name}")

    # ----------------------------------------------------------
    # Soundtrack
    # ----------------------------------------------------------
    audio_file = None
    if use_music:
        soundtrack_path = SOUNDTRACK_DIR / "booksearch_music.mp3"
        if not soundtrack_path.exists():
            gen.generate_soundtrack(
                SOUNDTRACK_PROMPT,
                str(soundtrack_path),
                title="BookSearch Promo"
            )
        else:
            print(f"\nUsing cached soundtrack: {soundtrack_path}")

        if soundtrack_path.exists():
            audio_file = str(soundtrack_path)

    gen.concatenate_segments(
        segments, str(FINAL_VIDEO),
        audio_path=audio_file,
        audio_fade_out=3.0
    )

    if FINAL_VIDEO.exists():
        size_mb = FINAL_VIDEO.stat().st_size / (1024 * 1024)
        print(f"\n✅ Promo video ready: {FINAL_VIDEO} ({size_mb:.1f} MB)")
    else:
        print("\n❌ Failed to generate final video")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build BookSearch promo video")
    parser.add_argument("--no-veo", action="store_true",
                        help="Use free zoom-out instead of Veo animation")
    parser.add_argument("--no-music", action="store_true",
                        help="Skip soundtrack generation")
    parser.add_argument("--test-slide", action="store_true",
                        help="Generate only the first slide for testing")
    args = parser.parse_args()

    if args.test_slide:
        test_first_slide(use_veo=not args.no_veo)
    else:
        build_promo(use_veo=not args.no_veo, use_music=not args.no_music)
