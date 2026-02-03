# BookSearch — AI Shopping Assistant for Bookstores

AI-powered book discovery assistant that helps customers articulate what they want through conversational interaction, then finds the perfect books using semantic search and AI filtering.

## Instructions for Claude

- This project shares visual identity with [BookTrailer](/Users/dmytropetrovskyi/projects/book_trailer). Always match its styling (see "UI Design" section below).
- You have access to browse files in the BookTrailer project at `/Users/dmytropetrovskyi/projects/book_trailer/` — use it as a styling and architecture reference.
- After finishing a feature, ask: "Do you want me to commit, push, or deploy?"
- **NEVER GUESS API ERROR MEANINGS** — When encountering API errors, always search the web to understand what the error means.

## Project Vision

A PSC (Proof of Smart Concept) demonstrating an AI shopping assistant for a fake bookstore. Three phases:

### Phase 1: Landing Page
A single landing page with a promo video showcasing the AI assistant on a pre-recorded, hard-coded user journey through a fake bookstore.

### Phase 2: Interactive Demo *(in progress)*
A standalone fake bookstore app with a working AI assistant:
1. Customer opens the store, doesn't know what they want
2. AI assistant appears and asks discovery questions:
   - "What was the last book you enjoyed?"
   - "Is this a gift? For whom?"
   - "How do you want to feel while reading?"
3. In 2-3 conversational turns, the AI understands intent
4. Semantic search + AI filtering produces 3 curated recommendations

**Demo Mode** (`/store?demo=1`) — Scripted conversations for video recording:
- 3 pre-built user journeys with hardcoded responses (no AI API calls)
- Books from Amazon dataset with real covers and metadata
- See `docs/User journeys.md` for the conversation scripts

### Phase 3: BookTrailer Integration
Incorporate the [BookTrailer](https://github.com/your-repo/book_trailer) project:
- After AI recommends 3 books, user can press "Visualize"
- A 30-60s video trailer appears with key plot components
- Uses BookTrailer's pipeline: narrative extraction → image generation → video assembly

## Tech Stack

### Current (Semantic Search Engine)
- **Backend**: Flask (Python 3.11)
- **Embeddings**: Google Gemini (`gemini/text-embedding-004` via litellm)
- **Search**: NumPy cosine similarity on pre-computed embeddings
- **Data**: ~1500 Russian books parsed from FB2 format
- **Large Dataset**: DuckDB for querying ~10M Amazon books (14GB JSONL)
- **Frontend**: HTML5 + vanilla JS

### Planned (AI Assistant)
- **Chat**: Gemini for conversational AI
- **Search Pipeline**:
  1. Semantic search on embeddings (broad candidates)
  2. AI filtering/ranking based on chat context (refined picks)
- **Frontend**: Tailwind CSS (CDN) — matching BookTrailer's design system

## Project Structure

```
book_search/
├── app.py              # Flask web server (search API + UI)
├── parser.py           # FB2 file parser (title, authors, genres, annotations, covers)
├── indexer.py          # Builds index.json from FB2 files
├── embeddings.py       # Generates embeddings via Gemini API (batch, 100/batch)
├── extract_demo_books.py  # Extracts demo books from Amazon dataset
├── explore_jsonl.py    # Tool to explore large JSONL files
├── templates/
│   ├── index.html      # Legacy search interface (lexical + semantic modes)
│   ├── landing.html    # Promo landing page
│   └── store.html      # Bookstore with AI chat widget (supports ?demo=1 mode)
├── static/
│   └── covers/         # Extracted book cover images (JPG)
├── db/
│   ├── import_books.py # Import Amazon dataset to DuckDB
│   └── query_books.py  # Query interface for DuckDB (by title/author/genre)
├── data/
│   ├── index.json      # All book metadata (~1500 Russian books)
│   ├── embeddings.npy  # Pre-computed semantic vectors (4.6 MB)
│   ├── demo_books.json # Demo book metadata (9 books from Amazon)
│   ├── meta_Books.jsonl # Amazon Books dataset (~10M books, 14GB)
│   ├── books.duckdb    # DuckDB database (created by import_books.py)
│   └── flatten/        # Flattened FB2 source files
├── docs/
│   └── User journeys.md # Scripted demo conversation flows
├── .env                # GOOGLE_API_KEY
└── .envrc              # direnv: GCP config (personal account)
```

## How It Works

### Data Pipeline (already built)
```
FB2 files → parser.py → index.json (metadata + covers)
                              ↓
                        embeddings.py → embeddings.npy (semantic vectors)
```

### Search (already built)
Two modes in `app.py`:
1. **Lexical**: Case-insensitive substring match on title/authors/annotations
2. **Semantic**: Cosine similarity between query embedding and pre-computed book embeddings

### AI Assistant (to build)
```
Customer opens bookstore
    ↓
AI assistant greets with discovery questions
    ↓
2-3 conversational turns → understanding of intent
    ↓
Layer 1: Semantic search on embeddings (broad candidates)
    ↓
Layer 2: AI filtering with Gemini (refine using chat context)
    ↓
3 curated recommendations with covers + descriptions
    ↓
[Phase 3] "Visualize" button → BookTrailer video
```

## UI Design: "Cinematic Gold" (shared with BookTrailer)

Both BookSearch and BookTrailer share the same visual identity.

**Color Palette:**
- Backgrounds: `#0a0a0f` (deep), `#12121a` (slate), `#1a1a24` (surface)
- Gold accents: `#d4a574` (primary), `#f5b041` (light), `#b87333` (dark)
- Text: `#ffffff` (headings), `#a8a8b3` (body), `#6b6b7a` (muted)

**Typography:** Cormorant Garamond (headings) + Inter (body) via Google Fonts CDN

**Tailwind Config (inline in templates):**
```javascript
tailwind.config = {
  theme: {
    extend: {
      colors: {
        deep: '#0a0a0f',
        slate: '#12121a',
        surface: '#1a1a24',
        gold: {
          DEFAULT: '#d4a574',
          light: '#f5b041',
          dark: '#b87333',
          muted: 'rgba(212, 165, 116, 0.15)'
        },
        muted: '#a8a8b3',
        dim: '#6b6b7a'
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'serif'],
        body: ['Inter', 'sans-serif']
      }
    }
  }
}
```

**Key Visual Elements:**
- Film grain overlay (SVG fractal noise, opacity: 0.03)
- Glass-effect headers with `backdrop-blur-md`
- Gold shimmer on CTAs (`btn-shimmer` animation)
- Card hover: `translateY(-8px)` lift + expanded shadow
- Animated gradient borders on interactive elements
- Custom scrollbar: gold thumb on deep track

**Reference:** See BookTrailer templates at `/Users/dmytropetrovskyi/projects/book_trailer/app/templates/` for exact implementation.

## Development

```bash
# Run the search server
python app.py
# → http://localhost:5000

# Open demo mode for video recording
open "http://localhost:5000/store?demo=1"

# Rebuild index from FB2 files
python indexer.py

# Regenerate embeddings (requires GOOGLE_API_KEY)
python embeddings.py

# Extract demo books from Amazon dataset (if needed)
python extract_demo_books.py

# Explore Amazon dataset interactively
python explore_jsonl.py

# DuckDB: Import Amazon dataset (10M books)
python db/import_books.py --sample  # Import 10K for testing
python db/import_books.py           # Full import (~10M books)

# DuckDB: Query books
python db/query_books.py --limit 10 title "harry potter"
python db/query_books.py --limit 10 author "stephen king"
python db/query_books.py --limit 10 genre "Science Fiction"
python db/query_books.py --limit 10 search --title "war" --genre "History"
python db/query_books.py genres     # List all genres with counts
```

## Environment Variables

Required in `.env`:
```
GOOGLE_API_KEY=         # Gemini API (embeddings + future chat)
```

Optional in `.envrc` (for Vertex AI / GCP):
```
CLOUDSDK_ACTIVE_CONFIG_NAME=personal
VERTEXAI_PROJECT=gen-lang-client-0463729029
VERTEXAI_LOCATION=us-central1
```

## BookTrailer Reference

The sibling project at `/Users/dmytropetrovskyi/projects/book_trailer/` contains:
- `app/templates/landing.html` — Landing page design reference
- `app/templates/dashboard.html` — Form/input design reference
- `app/templates/viewer*.html` — Content viewer design reference
- `app/services/` — AI pipeline services (parser, scenarist, visual_director, video_director)
- `CLAUDE.md` — Full documentation of BookTrailer architecture

Use these as reference when building Phase 3 integration.
