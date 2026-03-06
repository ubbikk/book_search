#!/usr/bin/env python3
"""
Generate embeddings for fiction books in fiction.duckdb.

Reads books from fiction.duckdb, generates embeddings via Gemini,
and stores them back as a numpy file alongside the DB.

Usage:
    python db/embed_fiction.py                # Embed top 10K
    python db/embed_fiction.py --limit 100000 # Embed top 100K
    python db/embed_fiction.py --all          # Embed all books
"""

import argparse
import os
import time
from pathlib import Path

import duckdb
import numpy as np
from dotenv import load_dotenv

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm

litellm.suppress_debug_info = True
load_dotenv()

os.environ["GEMINI_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")

DB_PATH = Path("data/fiction.duckdb")
EMBEDDINGS_PATH = Path("data/fiction_embeddings.npy")
ASIN_ORDER_PATH = Path("data/fiction_asin_order.npy")  # to map embedding index -> parent_asin

EMBEDDING_MODEL = "gemini/gemini-embedding-001"
BATCH_SIZE = 100
MAX_TEXT_CHARS = 8000  # ~2000 tokens, stay within model limit


def create_book_text(title: str, author: str, description: list | str) -> str:
    """Create text for embedding from book metadata."""
    parts = []
    if title:
        parts.append(title)
    if author:
        parts.append(f"by {author}")
    if description:
        if isinstance(description, list):
            desc = " ".join(description)
        else:
            desc = description
        if desc:
            parts.append(desc)
    text = ". ".join(parts)
    return text[:MAX_TEXT_CHARS]


def embed_batch(texts: list[str], retries: int = 3) -> list[list[float]]:
    """Embed a batch of texts with retry logic."""
    for attempt in range(retries):
        try:
            response = litellm.embedding(model=EMBEDDING_MODEL, input=texts)
            return [item["embedding"] for item in response.data]
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def main(limit: int | None = None):
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found. Run db/extract_fiction.py first.")
        return

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    limit_clause = f"LIMIT {limit}" if limit else ""
    rows = conn.execute(f"""
        SELECT parent_asin, title, author_name, description
        FROM books
        ORDER BY rating_number DESC
        {limit_clause}
    """).fetchall()
    conn.close()

    n = len(rows)
    print(f"Generating embeddings for {n:,} books...")

    # Prepare texts
    asins = []
    texts = []
    for asin, title, author, desc in rows:
        asins.append(asin)
        texts.append(create_book_text(title, author, desc))

    # Calculate estimated cost
    total_chars = sum(len(t) for t in texts)
    est_tokens = total_chars / 4
    est_cost = (est_tokens / 1_000_000) * 0.15
    print(f"Total text: {total_chars:,} chars (~{est_tokens:,.0f} tokens)")
    print(f"Estimated cost: ${est_cost:.2f}")
    print()

    # Generate embeddings in batches
    all_embeddings = []
    n_batches = (n + BATCH_SIZE - 1) // BATCH_SIZE
    start = time.time()

    for i in range(0, n, BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        if batch_num % 10 == 1 or batch_num == n_batches:
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (n - i) / rate if rate > 0 else 0
            print(f"Batch {batch_num}/{n_batches} ({i:,}/{n:,}) "
                  f"[{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining]")

        embeddings = embed_batch(batch)
        all_embeddings.extend(embeddings)

    elapsed = time.time() - start
    embeddings_array = np.array(all_embeddings, dtype=np.float32)
    asins_array = np.array(asins)

    # Save
    np.save(EMBEDDINGS_PATH, embeddings_array)
    np.save(ASIN_ORDER_PATH, asins_array)

    print(f"\nDone in {elapsed:.1f}s")
    print(f"Embeddings shape: {embeddings_array.shape}")
    print(f"Saved to: {EMBEDDINGS_PATH} ({EMBEDDINGS_PATH.stat().st_size / (1024*1024):.1f} MB)")
    print(f"ASIN order: {ASIN_ORDER_PATH}")

    # Report actual usage from litellm if available
    print(f"\nActual cost: check your Google AI Studio dashboard for exact usage")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fiction embeddings")
    parser.add_argument("--limit", type=int, default=10000,
                        help="Number of books to embed (default: 10000)")
    parser.add_argument("--all", action="store_true",
                        help="Embed all books in the database")
    args = parser.parse_args()

    main(limit=None if args.all else args.limit)
