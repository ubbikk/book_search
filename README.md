# BookSearch — AI Shopping Assistant for Bookstores

An AI-powered book discovery assistant that eliminates the "I don't know what I want" problem in bookstores. Through a short conversational exchange, the AI helps customers articulate their reading preferences and finds the perfect books using semantic search and intelligent filtering.

## The Problem

A customer walks into a bookstore (or opens an online one). They want something to read but can't articulate what. They browse aimlessly, get overwhelmed by choice, and leave empty-handed — or worse, buy something they won't enjoy.

## The Solution

An AI assistant that meets customers where they are:

> **AI:** "Tell me about the last book you couldn't put down. Or — is this for you, or a gift?"
>
> **Customer:** "It's for my wife, she loved that Swedish mystery series..."
>
> **AI:** "Got it — Nordic noir, strong female leads? Does she prefer psychological tension or action-driven plots?"
>
> **Customer:** "Definitely psychological, slow burn..."
>
> **AI:** *runs semantic search + AI filtering* → 3 curated picks with covers and descriptions

In 2-3 turns, the assistant understands intent better than a keyword search ever could.

## How It Works

**Two-layer recommendation engine:**

1. **Semantic Search** — Query embeddings matched against 1500+ pre-computed book embeddings using cosine similarity. Finds books by meaning, not keywords.
2. **AI Filtering** — Gemini analyzes the top candidates against the full conversation context, selecting the 3 best matches with personalized explanations.

## Roadmap

### Phase 1: Landing Page *(current)*
A promo landing page with a video showcasing the AI assistant in action on a pre-recorded user journey through a fake bookstore.

### Phase 2: Interactive Demo *(in progress)*
A working fake bookstore with a live AI assistant. Visitors can chat with the AI and get real recommendations from the book catalog.

**Demo Mode** — For video recording, a scripted demo is available at `/store?demo=1` with 3 pre-built user journeys:
- **"A book I loved"** — User mentions The Martian → gets similar witty sci-fi recommendations
- **"It's a gift"** — Gift for mom who loved Crawdads → atmospheric literary fiction
- **"Surprise me"** — Interactive buttons → mind-game thrillers with satisfying twists

### Phase 3: BookTrailer Integration
After the AI recommends books, users can press **"Visualize"** to watch a 30-60s AI-generated video trailer with key plot elements — powered by [BookTrailer](https://github.com/your-repo/book_trailer).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask (Python 3.11) |
| Embeddings | Google Gemini `text-embedding-004` via litellm |
| Search | NumPy cosine similarity |
| Chat AI | Google Gemini (planned) |
| Data | 1500+ books parsed from FB2 format |
| Frontend | Tailwind CSS, Cormorant Garamond + Inter |

## Quick Start

```bash
# Install dependencies
pip install flask litellm numpy python-dotenv

# Set up environment
cp .env.example .env
# Add your GOOGLE_API_KEY

# Run
python app.py
# → http://localhost:5000
```

### Demo Mode (for video recording)

```bash
# Open the scripted demo
open http://localhost:5000/store?demo=1
```

The demo mode uses pre-scripted conversations with books from an Amazon dataset (4.4M books). No AI API calls required — perfect for recording promo videos.

## Project Structure

```
book_search/
├── app.py              # Flask server — search API + web UI
├── parser.py           # FB2 book file parser
├── indexer.py          # Builds book metadata index
├── embeddings.py       # Generates semantic embeddings via Gemini
├── extract_demo_books.py  # Extracts demo books from Amazon dataset
├── explore_jsonl.py    # Tool to explore large JSONL files
├── templates/
│   ├── index.html      # Legacy search interface
│   ├── landing.html    # Promo landing page
│   └── store.html      # Bookstore with AI chat (supports ?demo=1)
├── static/covers/      # Book cover images
└── data/
    ├── index.json      # Book metadata (1500+ Russian books)
    ├── embeddings.npy  # Pre-computed vectors
    ├── demo_books.json # Demo book metadata (9 books from Amazon)
    └── meta_Books.jsonl # Amazon Books dataset (4.4M books)
```

## Design

Dark cinematic theme with warm gold accents — shared visual identity with BookTrailer.

- **Backgrounds:** Deep blacks (`#0a0a0f`, `#1a1a24`)
- **Accents:** Warm gold (`#d4a574`, `#f5b041`)
- **Typography:** Cormorant Garamond (display) + Inter (body)
- **Effects:** Film grain overlay, glass headers, shimmer CTAs

## License

Private — not open source.
