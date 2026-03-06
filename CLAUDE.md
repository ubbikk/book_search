# BookSearch — AI Shopping Assistant for Bookstores

AI-powered book discovery assistant that helps customers articulate what they want through conversational interaction, then finds the perfect books using semantic search and AI filtering.

## Instructions for Claude

- This project shares visual identity with [BookTrailer](/Users/dmytropetrovskyi/projects/book_trailer). Always match its styling (see "UI Design" section below).
- You have access to browse files in the BookTrailer project at `/Users/dmytropetrovskyi/projects/book_trailer/` — use it as a styling and architecture reference.
- After finishing a feature, ask: "Do you want me to commit, push, or deploy?"
- **NEVER GUESS API ERROR MEANINGS** — When encountering API errors, always search the web to understand what the error means.

## Project Vision

A PSC (Proof of Smart Concept) demonstrating an AI shopping assistant for a fake bookstore. Three phases:

### Phase 1: Landing Page (done)
A single landing page with a promo video showcasing the AI assistant on a pre-recorded, hard-coded user journey through a fake bookstore.

### Phase 2: Interactive Demo (done)
A standalone fake bookstore app with a working AI assistant:
1. Customer opens the store, AI assistant greets with flexible opening
2. Quick-start buttons ("A book I loved", "It's a gift", "Surprise me") or freeform text
3. AI asks 2-3 adaptive discovery questions based on user input
4. Two-layer search: FAISS semantic search (100 candidates) → Gemini AI filtering (top 3)
5. 3 curated recommendations with covers, metadata, and personalized explanations
6. Conversation continues — user can refine, ask for different books, or shift direction

**Demo Mode** (`/store?demo=1`) — Scripted conversations for video recording:
- 3 pre-built user journeys with hardcoded responses (no AI API calls)
- Books from Amazon dataset with real covers and metadata
- See `docs/User journeys.md` for the conversation scripts

### Phase 3: BookTrailer Integration (planned)
Incorporate the [BookTrailer](https://github.com/your-repo/book_trailer) project:
- After AI recommends 3 books, user can press "Visualize"
- A 30-60s video trailer appears with key plot components
- Uses BookTrailer's pipeline: narrative extraction → image generation → video assembly

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **Chat AI**: Gemini Flash (`gemini-2.0-flash` via litellm) for conversational discovery and book filtering
- **Embeddings**: Google Gemini (`gemini-embedding-001` via litellm)
- **Search**: FAISS HNSW index on 100K pre-computed embeddings (sub-ms queries, 99.3% recall@10)
- **Hybrid Scoring**: `alpha * cosine_similarity + (1-alpha) * log_popularity` (alpha=0.7)
- **Dataset**: 100K popular English fiction books (DuckDB), extracted from Amazon Reviews 2023
- **Frontend**: HTML5 + vanilla JS + Tailwind CSS (CDN)
- **Deployment**: Docker + Google Cloud Run

## Project Structure

```
book_search/
├── app.py                 # Flask web server (search API, chat API, UI routes)
├── prompts/
│   ├── system.md          # AI assistant system prompt (discovery conversation rules)
│   └── filter.md          # Book selection/filtering prompt (picks top 3 from candidates)
├── templates/
│   ├── index.html         # Legacy search interface (lexical + semantic modes)
│   ├── landing.html       # Promo landing page
│   └── store.html         # Bookstore with AI chat widget (supports ?demo=1 mode)
├── static/
│   └── covers/            # Book cover images (JPG)
├── db/                    # Data pipeline scripts
│   ├── import_books.py    # Import Amazon dataset to DuckDB (4.4M books)
│   ├── extract_fiction.py # Extract 100K popular fiction into fiction.duckdb
│   ├── embed_fiction.py   # Generate Gemini embeddings for fiction books
│   ├── query_books.py     # Query interface for DuckDB (by title/author/genre)
│   └── test_search.py     # Benchmark: brute-force vs FAISS (HNSW, IVF-Flat)
├── scripts/               # One-time utility scripts (not used at runtime)
│   ├── build_demo_index.py    # Build the 24-book demo index from Amazon data
│   ├── find_famous_books.py   # Find famous books in Amazon JSONL dataset
│   ├── extract_demo_books.py  # Extract demo book metadata from Amazon dataset
│   ├── explore_jsonl.py       # Interactive tool to explore large JSONL files
│   ├── embeddings.py          # Legacy: generate embeddings for Russian books
│   ├── indexer.py             # Legacy: build index.json from FB2 files
│   └── parser.py              # Legacy: FB2 file parser
├── services/              # Backend services
│   ├── firebase_auth.py   # Firebase authentication
│   └── firestore.py       # Firestore database
├── tests/
│   └── test_recommendations.py  # E2E tests: 10 user journeys through the full pipeline
├── docs/
│   ├── User journeys.md  # Scripted demo conversation flows
│   └── *.md               # Research articles on book discovery
├── data/                  # Large data files (gitignored)
│   ├── fiction.duckdb     # Production: 100K popular fiction metadata (703 MB)
│   ├── fiction_embeddings.npy  # 100K × 3072 Gemini embeddings (1.2 GB)
│   ├── fiction_hnsw.faiss # HNSW index for sub-ms search (1.2 GB)
│   ├── fiction_asin_order.npy  # Maps FAISS index position → parent_asin
│   ├── index.json         # 24 curated English books for store display
│   ├── embeddings.npy     # Legacy semantic vectors
│   └── demo_books.json    # Demo mode book metadata (9 books)
├── Dockerfile             # Docker config for Cloud Run deployment
├── requirements.txt       # Python dependencies
├── .env                   # GOOGLE_API_KEY (gitignored)
└── .envrc                 # direnv: GCP config (gitignored)
```

## How It Works

### AI Assistant Pipeline
```
Customer opens /store
    ↓
AI greets → quick-start buttons or freeform text
    ↓
2-3 conversational turns (Gemini Flash) → understanding of intent
    ↓
AI emits [READY_TO_SEARCH] marker with search params
    ↓
Layer 1: FAISS HNSW hybrid search (semantic + popularity, top 100)
    ↓
Layer 2: Gemini AI filtering (selects top 3 from candidates)
    ↓
3 recommendations with covers + personalized explanations
    ↓
User can continue: "try different ones" / "more like these" / freeform
(previously shown books are excluded from subsequent rounds)
```

### Fiction Data Pipeline
```
Amazon Reviews 2023 JSONL (14GB, 4.4M books)
    ↓
db/import_books.py → books.duckdb (full import)
    ↓
db/extract_fiction.py → fiction.duckdb (100K popular English fiction, deduplicated)
    ↓
db/embed_fiction.py → fiction_embeddings.npy (100K × 3072 via gemini-embedding-001)
    ↓
db/test_search.py → fiction_hnsw.faiss (HNSW index, 99.3% recall, <1ms queries)
```

**Dataset:** McAuley-Lab/Amazon-Reviews-2023 — https://amazon-reviews-2023.github.io/
**Filtering:** 6 fiction categories, English, 100+ ratings, deduplicated by title+author
**Embedding cost:** ~$10 for 100K books via gemini-embedding-001 ($0.15/1M tokens)

### Key Technical Details

- **Hybrid scoring**: `alpha * cosine_similarity + (1-alpha) * log_popularity` (alpha=0.7) prevents obscure books from dominating pure semantic results
- **`[READY_TO_SEARCH]` marker**: The AI signals readiness with a JSON block containing positive-only search query (embeddings can't understand negation) and full preferences (for AI filter which can)
- **Deduplication**: Session tracks `shown_asins` to exclude previously recommended books from follow-up rounds
- **Daily limit**: 10 AI requests/day (global counter, resets at midnight) to control API costs
- **Prompts are separate files**: `prompts/system.md` and `prompts/filter.md` for easy iteration

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
# Run the server (loads 100K fiction dataset on startup)
python app.py
# → http://localhost:5000

# Open the bookstore with AI assistant
open "http://localhost:5000/store"

# Open demo mode for video recording
open "http://localhost:5000/store?demo=1"

# Run e2e tests (10 user journeys)
pytest tests/test_recommendations.py -v

# Fiction data pipeline
python db/extract_fiction.py              # Extract 100K popular fiction → fiction.duckdb
python db/embed_fiction.py --all          # Embed all 100K (cost: ~$10)
python db/test_search.py --build-faiss   # Build FAISS indexes

# Query books from DuckDB
python db/query_books.py --limit 10 title "harry potter"
python db/query_books.py --limit 10 author "stephen king"
python db/query_books.py genres           # List all genres with counts
```

## Deployment

**Production URL:** https://booksearch-345011742806.us-central1.run.app
**GCP Project:** `gen-lang-client-0463729029`

```bash
# Deploy to Cloud Run (uploads ~2GB, takes ~10 min)
source .env && gcloud run deploy booksearch \
  --source . \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 300 \
  --set-env-vars "GOOGLE_API_KEY=$GOOGLE_API_KEY" \
  --allow-unauthenticated \
  --project gen-lang-client-0463729029

# View logs
gcloud run services logs read booksearch --region us-central1 --project gen-lang-client-0463729029 --limit 50
```

**How it works:**
- `--source .` triggers Cloud Build to build the Docker image remotely
- `.gcloudignore` controls what gets uploaded (excludes raw datasets, keeps runtime data)
- `.dockerignore` controls what goes into the container (same exclusions)
- Data files (~1.9GB) are baked into the image: `fiction.duckdb`, `fiction_hnsw.faiss`, `fiction_asin_order.npy`
- `fiction_embeddings.npy` (1.1GB) is excluded — only needed for rebuilding FAISS, not at runtime
- 4Gi memory is required to hold the FAISS index in RAM
- `load_index()` runs at module level so gunicorn loads data on startup

## Environment Variables

Required in `.env`:
```
GOOGLE_API_KEY=         # Gemini API (embeddings + chat)
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
