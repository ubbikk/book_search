#!/usr/bin/env python3
"""
Portable Promo Video Generator

Standalone script for creating cinematic promo videos with:
- Animated text slides (Veo or zoom-out fallback)
- Quick gallery slideshows
- Vertical scroll in landscape frame
- AI-generated soundtracks (Suno)
- Segment concatenation with audio mixing

Usage:
    python promo_generator.py                    # Generate all segments + assemble
    python promo_generator.py --no-veo           # Use free zoom-out instead of Veo
    python promo_generator.py --slides-only      # Only generate slide images (no video)

Requires:
    pip install Pillow google-genai requests
    brew install ffmpeg

Extracted from BookTrailers.ai promo pipeline.
"""

import os
import subprocess
import tempfile
import time
import json
import requests
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# CONFIGURATION — Edit these for your project
# ============================================================

# Output settings
OUTPUT_DIR = "data/promo"
RESOLUTION = (1920, 1080)
FPS = 24

# Fonts (Cormorant Garamond — copy from fonts/ directory)
FONTS_DIR = Path(__file__).parent / "fonts"
FONT_MAIN = FONTS_DIR / "CormorantGaramond-SemiBold.ttf"
FONT_SUBTITLE = FONTS_DIR / "CormorantGaramond-Regular.ttf"

# Design tokens
COLOR_BACKGROUND = "#0a1628"
COLOR_GOLD = "#D4A574"
COLOR_TEXT = "#FFFFFF"
FONT_SIZE_MAIN = 100
FONT_SIZE_SUBTITLE = 48

# Veo animation prompt (floating bokeh effect)
VEO_ANIMATION_PROMPT = (
    "Subtle cinematic animation: golden bokeh particles slowly floating upward, "
    "soft light rays gently pulsing, very slight camera drift. Text remains "
    "sharp and readable. Atmospheric, premium feel. Slow, elegant movement."
)

# Background generation prompt (for Gemini)
BACKGROUND_PROMPT = """Create a premium cinematic background for a video promo:
- Dark gradient background (deep navy #0a1628 to black)
- Subtle film grain texture overlay
- Soft golden light rays emanating from top-left corner
- Abstract bokeh circles in background (subtle, out of focus)
- Aspect ratio: 16:9 (1920x1080)
- Mood: Premium, professional, Hollywood movie poster quality
- NO TEXT, NO people, NO characters, NO scenes - ONLY elegant cinematic background
"""


# ============================================================
# PROMO VIDEO GENERATOR
# ============================================================

class PromoVideoGenerator:
    """
    Generates promotional videos with cinematic text slides,
    image galleries, and AI soundtracks.
    """

    def __init__(
        self,
        output_dir: str = OUTPUT_DIR,
        resolution: Tuple[int, int] = RESOLUTION,
        fps: int = FPS
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width, self.height = resolution
        self.fps = fps

    # ----------------------------------------------------------
    # SLIDE IMAGE GENERATION (PIL)
    # ----------------------------------------------------------

    def generate_slide_image(
        self,
        main_text: str,
        output_path: str,
        subtitle: str = None,
        background_path: str = None,
        font_size_main: int = FONT_SIZE_MAIN,
        font_size_subtitle: int = FONT_SIZE_SUBTITLE,
        text_color: str = COLOR_TEXT,
        glow_color: str = COLOR_GOLD,
    ) -> Optional[str]:
        """
        Generate slide image with text on cinematic background.

        Uses Cormorant Garamond font with gold glow effect.
        """
        print(f"\nGenerating slide: '{main_text[:40]}...'")

        if not FONT_MAIN.exists() or not FONT_SUBTITLE.exists():
            print(f"  FAILED: Fonts not found at {FONTS_DIR}")
            print("  Copy from promo_video_kit/fonts/ or download from GitHub:")
            print("  https://github.com/CatharsisFonts/Cormorant")
            return None

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Get background
        if not background_path or not Path(background_path).exists():
            bg_path = str(Path(output_path).parent / "_background.png")
            if not Path(bg_path).exists():
                print("  WARNING: No background image found.")
                print(f"  Generate one with Gemini or place manually at: {bg_path}")
                print("  Creating solid color fallback...")
                img = Image.new("RGBA", (self.width, self.height), COLOR_BACKGROUND)
                img.save(bg_path)
            background_path = bg_path

        try:
            image = Image.open(background_path).convert("RGBA")
            if image.size != (self.width, self.height):
                image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)

            draw = ImageDraw.Draw(image)
            font_main = ImageFont.truetype(str(FONT_MAIN), font_size_main)
            font_sub = ImageFont.truetype(str(FONT_SUBTITLE), font_size_subtitle)

            # Calculate main text position (centered)
            bbox = draw.textbbox((0, 0), main_text, font=font_main)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            y_offset = 20 if subtitle else 0
            x_main = (self.width - text_w) // 2
            y_main = (self.height - text_h) // 2 - y_offset

            # Gold glow effect (8-directional offset)
            glow_offsets = [(2, 2), (-2, -2), (2, -2), (-2, 2),
                           (0, 2), (0, -2), (2, 0), (-2, 0)]
            for ox, oy in glow_offsets:
                draw.text((x_main + ox, y_main + oy), main_text,
                          font=font_main, fill=glow_color + "30")

            # Main text
            draw.text((x_main, y_main), main_text, font=font_main, fill=text_color)

            # Subtitle
            if subtitle:
                bbox_sub = draw.textbbox((0, 0), subtitle, font=font_sub)
                sub_w = bbox_sub[2] - bbox_sub[0]
                x_sub = (self.width - sub_w) // 2
                y_sub = y_main + text_h + 30

                for ox, oy in glow_offsets:
                    draw.text((x_sub + ox, y_sub + oy), subtitle,
                              font=font_sub, fill=glow_color + "20")
                draw.text((x_sub, y_sub), subtitle, font=font_sub, fill=text_color)

            image.convert("RGB").save(output_path, "PNG")
            print(f"  OK: {output_path}")
            return output_path

        except Exception as e:
            print(f"  FAILED: {e}")
            return None

    # ----------------------------------------------------------
    # SLIDE ANIMATION — Veo (floating bokeh, ~$0.40/slide)
    # ----------------------------------------------------------

    def animate_slide_veo(
        self,
        image_path: str,
        output_path: str,
        duration: int = 4,
        prompt: str = VEO_ANIMATION_PROMPT
    ) -> Optional[str]:
        """
        Animate a static slide image using Google Veo via Vertex AI.

        Requires: google-genai, GOOGLE_CLOUD_PROJECT env var.
        Cost: ~$0.10/second = ~$0.40 for 4s.
        """
        print(f"\nAnimating slide with Veo ({duration}s)...")

        try:
            from google import genai
            from google.genai import types

            project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("VERTEXAI_PROJECT")
            # Veo requires us-central1 (not "global" which is for Gemini/embeddings)
            client = genai.Client(
                vertexai=True,
                project=project,
                location="us-central1",
            )

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            ext = Path(image_path).suffix.lower()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
            image = types.Image(
                image_bytes=image_bytes,
                mime_type=mime.get(ext.lstrip("."), "image/png")
            )

            print(f"    Veo prompt: {prompt[:100]}...")
            operation = client.models.generate_videos(
                model="veo-3.1-fast-generate-001",
                image=image,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    number_of_videos=1,
                    duration_seconds=4,  # Veo supports 4, 6, 8
                    person_generation="allow_all",
                    generate_audio=False,
                )
            )

            # Poll for completion (must refresh operation object each time)
            start = time.time()
            while not operation.done:
                time.sleep(10)
                operation = client.operations.get(operation)
                elapsed = int(time.time() - start)
                print(f"    Veo: polling... {elapsed}s elapsed")
                if elapsed > 300:
                    print("    Veo: timeout after 300s")
                    return None

            # Ensure result is populated (may need one more fetch)
            if operation.result is None:
                operation = client.operations.get(operation)

            print(f"    Veo: completed in {int(time.time() - start)}s")

            # Download result
            video = operation.result.generated_videos[0].video
            with open(output_path, "wb") as f:
                f.write(video.video_bytes)

            print(f"  OK: {output_path}")
            return output_path

        except Exception as e:
            print(f"  FAILED: {e}")
            return None

    # ----------------------------------------------------------
    # SLIDE ANIMATION — Zoom-Out (free, FFmpeg)
    # ----------------------------------------------------------

    def animate_slide_zoom(
        self,
        image_path: str,
        output_path: str,
        duration: float = 4.0,
        zoom_start: float = 1.2,
        zoom_end: float = 1.0,
        fade_in: float = 0.5,
        fade_out: float = 0.5,
        drift_y: float = 30.0
    ) -> Optional[str]:
        """
        Create zoom-out reveal animation from static image.

        Free alternative to Veo. Uses FFmpeg zoompan filter with
        subtle upward drift to simulate floating bokeh.
        """
        print(f"\nCreating zoom-out video ({duration}s)...")

        frames = int(duration * self.fps)
        zoom_decrement = (zoom_start - zoom_end) / frames
        drift_per_frame = drift_y / frames

        zoompan_filter = (
            f"scale=8000:-1,"
            f"zoompan=z='if(eq(on,1),{zoom_start},max({zoom_end},zoom-{zoom_decrement:.8f}))':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)-{drift_per_frame:.6f}*on':"
            f"d={frames}:s={self.width}x{self.height}:fps={self.fps},"
            f"fade=t=in:st=0:d={fade_in},"
            f"fade=t=out:st={duration - fade_out}:d={fade_out}"
        )

        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", zoompan_filter,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"  OK: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {e.stderr[:500] if e.stderr else e}")
            return None

    # ----------------------------------------------------------
    # ANIMATED SLIDE (full pipeline: image → animation)
    # ----------------------------------------------------------

    def create_animated_slide(
        self,
        main_text: str,
        output_path: str,
        duration: float = 4.0,
        subtitle: str = None,
        use_veo: bool = True
    ) -> Optional[str]:
        """
        Generate a text slide and animate it.

        Pipeline:
        1. Render text on background with PIL (cached as PNG)
        2. Animate with Veo (cached as _veo.mp4) or zoom-out
        3. Trim/scale to final duration
        """
        slides_dir = self.output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)

        safe_name = "".join(c if c.isalnum() else "_" for c in main_text[:30])
        image_path = slides_dir / f"{safe_name}.png"

        # Step 1: Generate slide image (cached)
        if not image_path.exists():
            result = self.generate_slide_image(
                main_text, str(image_path), subtitle=subtitle
            )
            if not result:
                return None
        else:
            print(f"\nUsing cached slide: {image_path}")

        # Step 2: Animate
        if use_veo:
            veo_path = slides_dir / f"{safe_name}_veo.mp4"
            if not veo_path.exists():
                veo_result = self.animate_slide_veo(str(image_path), str(veo_path))
                if not veo_result:
                    use_veo = False
            else:
                print(f"  Using cached Veo animation: {veo_path}")

            if use_veo:
                # Trim/scale Veo output; slow down if duration > 4s
                fade_out_start = max(0, duration - 0.5)
                veo_duration = 4.0
                slowdown = f"setpts={duration/veo_duration}*PTS," if duration > veo_duration else ""
                vf = (
                    f"{slowdown}"
                    f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2:black,"
                    f"fps={self.fps},"
                    f"fade=t=out:st={fade_out_start}:d=0.5"
                )
                cmd = [
                    "ffmpeg", "-y", "-i", str(veo_path),
                    "-t", str(duration), "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    output_path
                ]
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    print(f"  Trimmed to {duration}s: {output_path}")
                    return output_path
                except subprocess.CalledProcessError:
                    pass  # Fall through to zoom-out

        # Fallback: zoom-out animation (free)
        return self.animate_slide_zoom(
            str(image_path), output_path, duration=duration
        )

    # ----------------------------------------------------------
    # QUICK GALLERY (crossfade slideshow)
    # ----------------------------------------------------------

    def create_quick_gallery(
        self,
        images: List[str],
        output_path: str,
        duration_per_image: float = 2.0,
        crossfade: float = 0.3
    ) -> Optional[str]:
        """
        Create crossfade slideshow from a list of images.
        """
        if not images:
            return None

        print(f"\nCreating quick gallery ({len(images)} images, {duration_per_image}s each)...")

        filter_parts = []
        inputs = []

        for i, img in enumerate(images):
            inputs.extend(["-loop", "1", "-t", str(duration_per_image), "-i", img])
            filter_parts.append(
                f"[{i}:v]scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[v{i}]"
            )

        if len(images) > 1:
            prev = "v0"
            for i in range(1, len(images)):
                offset = i * duration_per_image - (i * crossfade) - crossfade
                if offset < 0:
                    offset = (i - 1) * (duration_per_image - crossfade)
                filter_parts.append(
                    f"[{prev}][v{i}]xfade=transition=fade:duration={crossfade}:offset={offset}[xf{i}]"
                )
                prev = f"xf{i}"
            final_label = prev
        else:
            final_label = "v0"

        total_dur = len(images) * duration_per_image - (len(images) - 1) * crossfade
        filter_parts.append(
            f"[{final_label}]fade=t=in:st=0:d=0.3,fade=t=out:st={total_dur - 0.3}:d=0.3[out]"
        )

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", ";".join(filter_parts),
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"  OK: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {e.stderr[:500] if e.stderr else e}")
            return None

    # ----------------------------------------------------------
    # VERTICAL SCROLL IN LANDSCAPE FRAME
    # ----------------------------------------------------------

    def create_scroll_in_frame(
        self,
        images: List[str],
        output_path: str,
        duration: float = 12.0,
        direction: str = "down"
    ) -> Optional[str]:
        """
        Show vertical content scrolling in a 16:9 landscape frame.
        """
        if not images:
            return None

        print(f"\nCreating scroll in landscape frame ({len(images)} images)...")

        frame_w, frame_h = self.width, self.height
        viewport_h = int(frame_h * 0.95)
        viewport_w = int(viewport_h * 3 / 5)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            stacked_path = tmp.name

        try:
            # Stack images vertically
            vstack_inputs = []
            filter_parts = []
            for i, img in enumerate(images):
                vstack_inputs.extend(["-i", img])
                filter_parts.append(f"[{i}:v]scale={viewport_w}:-1[s{i}]")

            stack_labels = "".join(f"[s{i}]" for i in range(len(images)))
            filter_parts.append(f"{stack_labels}vstack=inputs={len(images)}[stacked]")

            cmd = ["ffmpeg", "-y"] + vstack_inputs + [
                "-filter_complex", ";".join(filter_parts),
                "-map", "[stacked]", stacked_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            # Get stacked dimensions
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0", stacked_path],
                capture_output=True, text=True, check=True
            )
            stacked_w, stacked_h = map(int, probe.stdout.strip().split(","))
            scroll_distance = max(0, stacked_h - viewport_h)

            vp_x = (frame_w - viewport_w) // 2
            vp_y = (frame_h - viewport_h) // 2

            if scroll_distance == 0:
                y_expr = "0"
            elif direction == "down":
                y_expr = f"({scroll_distance}*t/{duration})"
            else:
                y_expr = f"{scroll_distance}-({scroll_distance}*t/{duration})"

            filter_complex = (
                f"color=c={COLOR_BACKGROUND}:s={frame_w}x{frame_h}:d={duration}[bg];"
                f"[1:v]crop={viewport_w}:{viewport_h}:0:'{y_expr}'[scroll];"
                f"[bg][scroll]overlay={vp_x}:{vp_y}:format=auto,"
                f"vignette=angle=PI/4:mode=backward,"
                f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration - 0.5}:d=0.5"
            )

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c={COLOR_BACKGROUND}:s={frame_w}x{frame_h}:d={duration}",
                "-loop", "1", "-i", stacked_path,
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"  OK: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {e.stderr[:500] if e.stderr else e}")
            return None
        finally:
            if os.path.exists(stacked_path):
                os.unlink(stacked_path)

    # ----------------------------------------------------------
    # VIDEO EMBED (re-encode existing video)
    # ----------------------------------------------------------

    def embed_video(
        self,
        video_path: str,
        output_path: str,
        max_duration: float = 30.0
    ) -> Optional[str]:
        """Re-encode an existing video clip for embedding."""
        print(f"\nEmbedding video: {video_path} (max {max_duration}s)")

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-t", str(max_duration),
            "-c:v", "libx264", "-c:a", "aac", "-preset", "fast",
            output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"  OK: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {e}")
            return None

    # ----------------------------------------------------------
    # CONCATENATE SEGMENTS + ADD AUDIO
    # ----------------------------------------------------------

    def concatenate_segments(
        self,
        segments: List[str],
        output_path: str,
        audio_path: str = None,
        audio_fade_out: float = 2.0
    ) -> Optional[str]:
        """
        Concatenate video segments and optionally add soundtrack.
        """
        if not segments:
            return None

        print(f"\nConcatenating {len(segments)} segments...")

        # Normalize segments with mismatched resolution/fps
        normalized = []
        for seg in segments:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height,r_frame_rate",
                 "-of", "csv=p=0", seg],
                capture_output=True, text=True
            )
            needs_norm = False
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                if len(parts) >= 2:
                    w, h = int(parts[0]), int(parts[1])
                    if w != self.width or h != self.height:
                        needs_norm = True
                        print(f"  Normalizing {Path(seg).name}: {w}x{h}->{self.width}x{self.height}")

            if needs_norm:
                norm_path = str(Path(seg).with_suffix(".norm.mp4"))
                cmd = [
                    "ffmpeg", "-y", "-i", seg,
                    "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                           f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2:black,fps={self.fps}",
                    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", norm_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                normalized.append(norm_path)
            else:
                normalized.append(seg)

        # Concat
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for seg in normalized:
                f.write(f"file '{Path(seg).resolve()}'\n")

        try:
            temp_video = self.output_dir / "temp_concat.mp4"
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                str(temp_video)
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            if audio_path and os.path.exists(audio_path):
                print(f"  Adding audio: {audio_path}")
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(temp_video)],
                    capture_output=True, text=True, check=True
                )
                video_duration = float(result.stdout.strip())
                fade_start = max(0, video_duration - audio_fade_out)

                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(temp_video),
                    "-stream_loop", "-1", "-i", audio_path,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac",
                    "-af", f"atrim=0:{video_duration},afade=t=out:st={fade_start}:d={audio_fade_out}",
                    "-t", str(video_duration),
                    output_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                temp_video.unlink()
            else:
                temp_video.rename(output_path)

            print(f"  OK: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {e.stderr[:500] if e.stderr else e}")
            return None
        finally:
            if concat_file.exists():
                concat_file.unlink()
            temp = self.output_dir / "temp_concat.mp4"
            if temp.exists():
                temp.unlink()

    # ----------------------------------------------------------
    # SOUNDTRACK GENERATION (Suno AI)
    # ----------------------------------------------------------

    def generate_soundtrack(
        self,
        prompt: str,
        output_path: str,
        title: str = "Promo Soundtrack",
        api_key: str = None
    ) -> Optional[str]:
        """
        Generate instrumental soundtrack using Suno AI.

        Cost: ~$0.05 per generation (produces 2 tracks, returns first).
        """
        api_key = api_key or os.environ.get("SUNO_API_KEY")
        if not api_key:
            print("  FAILED: SUNO_API_KEY not set")
            return None

        print(f"\nGenerating soundtrack: '{prompt[:60]}...'")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "customMode": True,
            "instrumental": True,
            "model": "V4_5",
            "style": prompt[:1000],
            "title": title,
            "callBackUrl": "https://httpbin.org/post",
        }

        try:
            resp = requests.post(
                "https://api.sunoapi.org/api/v1/generate",
                headers=headers, json=payload, timeout=60
            )
            resp.raise_for_status()
            resp_data = resp.json()
            if resp_data.get("code") and resp_data["code"] != 200:
                print(f"  FAILED: API error {resp_data.get('code')}: {resp_data.get('msg')}")
                return None
            task_id = resp_data.get("data", {}).get("taskId")
            if not task_id:
                print(f"  FAILED: No taskId in response: {resp_data}")
                return None
            print(f"  Task: {task_id}")

            # Poll for completion
            for i in range(60):  # 5 min max
                time.sleep(5)
                result = requests.get(
                    f"https://api.sunoapi.org/api/v1/generate/record-info?taskId={task_id}",
                    headers=headers, timeout=30
                )
                data = result.json().get("data", {})
                status = data.get("status", "")
                if status == "SUCCESS":
                    audio_url = data["response"]["sunoData"][0]["audioUrl"]
                    print(f"  Downloading: {audio_url}")
                    audio = requests.get(audio_url, timeout=60)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(audio.content)
                    print(f"  OK: {output_path} ({len(audio.content)} bytes)")
                    return output_path
                elif "FAIL" in status.upper():
                    print(f"  FAILED: {data.get('errorMessage', status)}")
                    return None

            print("  FAILED: timeout")
            return None

        except Exception as e:
            print(f"  FAILED: {e}")
            return None


# ============================================================
# EXAMPLE: How to build a promo video
# ============================================================

def example_promo():
    """
    Example promo video structure. Customize this for your project.

    Edit the slides, images, and video paths to match your content.
    """
    generator = PromoVideoGenerator()
    segments_dir = generator.output_dir / "segments"
    segments_dir.mkdir(exist_ok=True)
    segments = []

    use_veo = "--no-veo" not in os.sys.argv

    print("=" * 60)
    print("PROMO VIDEO GENERATOR")
    print(f"  Veo: {'enabled (~$0.40/slide)' if use_veo else 'disabled (free zoom-out)'}")
    print("=" * 60)

    # --- SLIDE EXAMPLE ---
    seg = str(segments_dir / "01_intro.mp4")
    if generator.create_animated_slide("Your Headline Here", seg, 4.0, use_veo=use_veo):
        segments.append(seg)

    # --- TWO-LINE SLIDE EXAMPLE ---
    seg = str(segments_dir / "02_subtitle.mp4")
    if generator.create_animated_slide(
        "Main Title", seg, 6.0,
        subtitle="Supporting Subtitle Text",
        use_veo=use_veo
    ):
        segments.append(seg)

    # --- GALLERY EXAMPLE ---
    # gallery_images = ["path/to/img1.png", "path/to/img2.png", ...]
    # seg = str(segments_dir / "03_gallery.mp4")
    # if generator.create_quick_gallery(gallery_images, seg, duration_per_image=2.5):
    #     segments.append(seg)

    # --- VIDEO EMBED EXAMPLE ---
    # seg = str(segments_dir / "04_demo.mp4")
    # if generator.embed_video("path/to/demo.mp4", seg, max_duration=30):
    #     segments.append(seg)

    # --- CTA SLIDE ---
    seg = str(segments_dir / "03_cta.mp4")
    if generator.create_animated_slide("Try It Today", seg, 4.0, use_veo=use_veo):
        segments.append(seg)

    # --- ASSEMBLE ---
    if segments:
        # Optionally generate soundtrack
        # audio = generator.generate_soundtrack(
        #     "Epic cinematic orchestral, heroic, instrumental, no vocals",
        #     str(generator.output_dir / "soundtrack" / "promo_music.mp3")
        # )
        audio = None

        generator.concatenate_segments(
            segments,
            str(generator.output_dir / "promo_final.mp4"),
            audio_path=audio
        )

    print("\nDone!")


if __name__ == "__main__":
    if "--slides-only" in os.sys.argv:
        # Just generate slide images, no video
        gen = PromoVideoGenerator()
        slides_dir = gen.output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)
        gen.generate_slide_image("Example Slide", str(slides_dir / "example.png"),
                                 subtitle="With Subtitle")
        print("\nSlide image generated. Check slides/ directory.")
    else:
        example_promo()
