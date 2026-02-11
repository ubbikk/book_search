# BookSearch Promo Video — Production Guide

## Overview

The BookSearch promo video is a 2:16 cinematic piece showcasing the AI book discovery assistant through 3 pre-scripted demo journeys. It combines Veo-animated text slides with Playwright-captured screenshots of actual chat interactions.

**Final output:** `data/promo/booksearch_promo.mp4` (14.5 MB, 1920x1080, 24fps)

## Architecture

```
promo/
├── README.md                  # This file
├── promo_generator.py         # Core engine (PIL + Veo + FFmpeg)
├── capture_journeys.py        # Playwright screenshot automation
├── build_promo.py             # Orchestrator (storyboard + assembly)
├── fonts/
│   ├── CormorantGaramond-SemiBold.ttf   # Main text
│   └── CormorantGaramond-Regular.ttf    # Subtitles
└── screenshots/               # Captured chat screenshots (19 PNGs)

data/promo/
├── booksearch_promo.mp4       # Final assembled video
├── slides/
│   ├── _background.png        # Cinematic bokeh background (shared)
│   ├── *_veo.mp4              # Veo-animated clips (11 cached)
│   └── *.png                  # Rendered text slide images (11 cached)
└── segments/
    └── *.mp4                  # Individual video segments (17 total)
```

## Pipeline

### Step 1: Capture Screenshots

```bash
# Requires Flask server running:
python app.py

# Capture all 3 demo journeys:
python promo/capture_journeys.py
```

Opens `http://localhost:5000/store?demo=1` in headless Chromium (1920x1080, 2x Retina) and walks through each scripted journey, taking screenshots at key moments.

**19 screenshots produced:**

| File | Content |
|------|---------|
| `00_bookstore_with_chat.png` | Bookstore grid with chat panel open |
| `j1_01_ai_question.png` | Journey 1: AI asks first question |
| `j1_02_conversation.png` | Journey 1: User says "The Martian" |
| `j1_03_conversation.png` | Journey 1: AI asks what hooked them |
| `j1_04_conversation.png` | Journey 1: User says humor + fast pace |
| `j1_recs_full.png` | Journey 1: Full page with recommendations |
| `j1_recs_closeup.png` | Journey 1: Chat panel crop of rec cards |
| `j2_01..04, recs_*` | Journey 2: "It's a gift" (same pattern) |
| `j3_01..04, recs_*` | Journey 3: "Surprise me" with button clicks |

### Step 2: Generate Text Slides

Text slides are rendered with PIL (Pillow) onto a cinematic background, then animated with Google Veo 3.1 Fast.

**Background:** `data/promo/slides/_background.png` — deep navy gradient with golden bokeh particles and soft light rays. Copied from the BookTrailer project's `promo_video_kit/`.

**Text rendering:**
- Main text: Cormorant Garamond SemiBold, 100px, white (#FFFFFF)
- Subtitles: Cormorant Garamond Regular, 48px, white
- Gold glow: 8-directional offset at #D4A574 with 19% opacity
- Centered vertically and horizontally

**Animation:** Veo 3.1 Fast (`veo-3.1-fast-generate-001`) via Vertex AI
- Input: Static slide PNG
- Prompt: "Subtle cinematic animation: golden bokeh particles slowly floating upward, soft light rays gently pulsing, very slight camera drift. Text remains sharp and readable. Atmospheric, premium feel. Slow, elegant movement."
- Config: 16:9, 4 seconds, `generate_audio=False`
- Cost: ~$0.40 per slide, ~$4.40 for all 11
- Generation time: ~60-130s per slide

### Step 3: Build Promo Video

```bash
# Full build with Veo animation:
source .envrc && python promo/build_promo.py

# Free fallback (FFmpeg zoom-out instead of Veo):
python promo/build_promo.py --no-veo

# Test single slide:
python promo/build_promo.py --test-slide
```

## Storyboard

17 segments, 136 seconds total:

| # | Segment | Type | Duration |
|---|---------|------|----------|
| 1 | "56% of your customers don't know what they want." | Veo slide | 4.0s |
| 2 | "And they can't tell you — even if you ask." | Veo slide | 4.0s |
| 3 | "They browse. They hesitate. They leave." | Veo slide | 4.0s |
| 4 | "But the right questions can." | Veo slide | 4.0s |
| 5 | "BookSearch doesn't wait for the perfect query." | Veo slide | 4.0s |
| 6 | "A book I loved" — Journey 1 of 3 | Veo slide | 4.0s |
| 7 | Journey 1 conversation (5 screenshots) | Gallery | 22.6s |
| 8 | Journey 1 recommendations (close-up) | Gallery | 8.1s |
| 9 | "It's a gift" — Journey 2 of 3 | Veo slide | 4.0s |
| 10 | Journey 2 conversation (5 screenshots) | Gallery | 22.6s |
| 11 | Journey 2 recommendations (close-up) | Gallery | 8.1s |
| 12 | "Surprise me" — Journey 3 of 3 | Veo slide | 4.0s |
| 13 | Journey 3 conversation (5 screenshots) | Gallery | 22.6s |
| 14 | Journey 3 recommendations (close-up) | Gallery | 8.1s |
| 15 | "3 smart questions. 3 perfect books." | Veo slide | 4.0s |
| 16 | "Turn browsers into buyers." | Veo slide | 4.0s |
| 17 | "BookSearch — Discovery that sells." | Veo slide | 4.0s |

**Text slides (11):** 44.0s total
**Screenshot galleries (6):** 92.0s total

## Slide Text Reference

Full slide copy is maintained in `docs/Booksearch video slides.md`. The `SLIDES` array in `build_promo.py` is the source of truth for what gets rendered.

## Caching

The build script caches aggressively — only missing segments are regenerated:

- **Slide PNGs** (`data/promo/slides/*.png`): Cached after first render. Delete to re-render with different text/styling.
- **Veo clips** (`data/promo/slides/*_veo.mp4`): Cached after Veo generation. Delete to re-animate (~$0.40 each).
- **Segments** (`data/promo/segments/*.mp4`): Cached after creation. Delete specific segments to regenerate only those.
- **Final video** (`data/promo/booksearch_promo.mp4`): Always reassembled from segments. Delete to trigger reassembly.

To do a full clean rebuild:

```bash
rm -rf data/promo/slides data/promo/segments data/promo/booksearch_promo.mp4
source .envrc && python promo/build_promo.py
```

## Environment Setup

### Required

```bash
pip install Pillow google-genai playwright
playwright install chromium
brew install ffmpeg
```

### Environment Variables

Set in `.envrc` (loaded by direnv) or export manually:

```bash
export VERTEXAI_PROJECT=gen-lang-client-0463729029   # GCP project ID
export CLOUDSDK_ACTIVE_CONFIG_NAME=personal          # gcloud config
```

Authentication:

```bash
gcloud auth application-default login
```

Note: `VERTEXAI_LOCATION` in `.envrc` is set to `global` for Gemini/embeddings. The promo generator hardcodes `us-central1` for Veo, which requires that specific region.

## Technical Notes

### Veo API (google-genai SDK)

The Veo video generation API returns a long-running operation that must be polled:

```python
operation = client.models.generate_videos(model="veo-3.1-fast-generate-001", ...)

# Must refresh operation object to get updated status
while not operation.done:
    time.sleep(10)
    operation = client.operations.get(operation)

# Result may need one more fetch after done=True
if operation.result is None:
    operation = client.operations.get(operation)

# Video bytes are returned directly (no GCS URI)
video = operation.result.generated_videos[0].video
video.video_bytes  # raw MP4 bytes
```

Key gotchas:
- `operation.done` is `None` (not `False`) until the first `operations.get()` refresh
- The result can be `None` even when `done=True` — one more `get()` resolves it
- `client.files.download()` only works with Gemini API, not Vertex AI — use `video.video_bytes` directly
- Veo requires `location="us-central1"`, not `"global"`

### FFmpeg Gallery Assembly

Screenshot galleries use FFmpeg crossfade transitions:

- **Conversation galleries:** 5.0s per image, 0.5s crossfade
- **Recommendation close-ups:** 8.0s per image, 0.5s crossfade
- Final concatenation normalizes all segments to 1920x1080 @ 24fps

### Playwright Capture

- Viewport: 1920x1080 with `device_scale_factor=2` (Retina)
- Headless Chromium
- Demo mode URL: `/store?demo=1`
- Waits for `.msg-assistant` count changes to detect new AI messages
- Waits for `.rec-card` elements for recommendation cards
- Scrolls to first rec-card before screenshots (cards can be below fold)

### CSS Fix: rec-card flex collapse

The `.rec-card` elements required `flex-shrink: 0` in CSS to prevent collapsing to 2px height inside the `.chat-messages` flex column container. Without this, `overflow: hidden` on the cards combined with the flex layout caused them to shrink to just their border height in headless browsers.

### Suno AI Soundtrack (sunoapi.org)

Background music is generated via the Suno AI API through sunoapi.org:

- **Generate:** `POST https://api.sunoapi.org/api/v1/generate`
- **Poll:** `GET https://api.sunoapi.org/api/v1/generate/record-info?taskId={taskId}`
- **Auth:** `Authorization: Bearer {SUNO_API_KEY}` header (NOT `api-key`)
- **Model:** `V4_5` (instrumental, custom mode)
- **Cost:** ~$0.05 per generation (produces 2 tracks, uses first)
- **`callBackUrl` is required** even when using polling — use `https://httpbin.org/post` as a no-op sink
- Audio is mixed into the final video via FFmpeg with a 3-second fade-out at the end

## Porting from BookTrailer

The `promo_generator.py` and fonts were copied from `/Users/dmytropetrovskyi/projects/book_trailer/promo_video_kit/`. The Veo API fixes (polling, download, location) were applied to both projects. If updating the generator, sync changes between both copies.
