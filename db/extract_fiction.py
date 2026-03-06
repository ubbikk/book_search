#!/usr/bin/env python3
"""
Extract popular fiction books from the main DuckDB database into a smaller,
deduplicated database for embedding and semantic search.

Source: McAuley-Lab/Amazon-Reviews-2023 (Books category)

Usage:
    python db/extract_fiction.py              # Extract ~100K popular fiction
    python db/extract_fiction.py --limit 10000  # Extract top 10K only
"""

import argparse
import time
from pathlib import Path

import duckdb

SOURCE_DB = Path("data/books.duckdb")
TARGET_DB = Path("data/fiction.duckdb")

# Fiction categories to include
FICTION_CATEGORIES = [
    "Literature & Fiction",
    "Mystery, Thriller & Suspense",
    "Science Fiction & Fantasy",
    "Romance",
    "Horror",
    "Genre Fiction",
]

MIN_RATING_COUNT = 50  # Minimum number of ratings (popularity threshold)


def extract(limit: int | None = None):
    if not SOURCE_DB.exists():
        print(f"Error: {SOURCE_DB} not found. Run db/import_books.py first.")
        return

    if TARGET_DB.exists():
        print(f"Removing existing {TARGET_DB}")
        TARGET_DB.unlink()

    print(f"Extracting popular fiction from {SOURCE_DB}...")
    start = time.time()

    src = duckdb.connect(str(SOURCE_DB), read_only=True)
    dst = duckdb.connect(str(TARGET_DB))

    # Build fiction filter
    cat_filters = " OR ".join(
        f"list_contains(categories, '{cat}')" for cat in FICTION_CATEGORIES
    )

    limit_clause = f"LIMIT {limit}" if limit else ""

    # Extract deduplicated fiction books, keeping the edition with most ratings.
    # Dedup key: normalized title (strip subtitle after :, (, [) + lowercase author.
    query = f"""
        CREATE TABLE books AS
        WITH ranked AS (
            SELECT *,
                LOWER(REGEXP_REPLACE(title, '\\s*[:(\\[].*', '')) AS clean_title,
                LOWER(TRIM(author_name)) AS clean_author,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        LOWER(REGEXP_REPLACE(title, '\\s*[:(\\[].*', '')),
                        LOWER(TRIM(author_name))
                    ORDER BY rating_number DESC
                ) AS rn
            FROM books
            WHERE len(description) > 0
                AND rating_number >= {MIN_RATING_COUNT}
                AND (language = 'English' OR language IS NULL)
                AND ({cat_filters})
        )
        SELECT
            parent_asin,
            title,
            author_name,
            main_category,
            categories,
            average_rating,
            rating_number,
            price,
            description,
            subtitle,
            isbn_10,
            isbn_13,
            publisher,
            language,
            images,
            store
        FROM ranked
        WHERE rn = 1
        ORDER BY rating_number DESC
        {limit_clause}
    """

    print("Running extraction query (this may take a minute)...")
    dst.execute(f"ATTACH '{SOURCE_DB}' AS src (READ_ONLY)")
    dst.execute(query.replace("FROM books", "FROM src.books"))

    # Create indexes for common queries
    dst.execute("CREATE INDEX idx_rating ON books(rating_number)")
    dst.execute("CREATE INDEX idx_avg_rating ON books(average_rating)")
    dst.execute("CREATE INDEX idx_parent_asin ON books(parent_asin)")

    count = dst.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    elapsed = time.time() - start
    db_size = TARGET_DB.stat().st_size / (1024 * 1024)

    print(f"\nExtracted {count:,} books in {elapsed:.1f}s")
    print(f"Database: {TARGET_DB} ({db_size:.1f} MB)")

    # --- Stats ---
    print("\n" + "=" * 60)
    print("EXTRACTION STATS")
    print("=" * 60)

    # Rating distribution
    print("\nRating distribution:")
    for lo, hi in [(50, 100), (100, 500), (500, 1000), (1000, 5000), (5000, 10000), (10000, 50000), (50000, None)]:
        if hi:
            n = dst.execute(f"SELECT COUNT(*) FROM books WHERE rating_number >= {lo} AND rating_number < {hi}").fetchone()[0]
            print(f"  {lo:>6,} - {hi:>6,} ratings: {n:>6,} books")
        else:
            n = dst.execute(f"SELECT COUNT(*) FROM books WHERE rating_number >= {lo}").fetchone()[0]
            print(f"  {lo:>6,}+          ratings: {n:>6,} books")

    # Average rating distribution
    print("\nAverage rating distribution:")
    for stars in [3.0, 3.5, 4.0, 4.5]:
        n = dst.execute(f"SELECT COUNT(*) FROM books WHERE average_rating >= {stars}").fetchone()[0]
        print(f"  >= {stars} stars: {n:,} books ({100*n/count:.0f}%)")

    # Category breakdown
    print("\nTop categories:")
    cats = dst.execute("""
        SELECT cat, COUNT(*) as cnt
        FROM (SELECT UNNEST(categories) as cat FROM books)
        WHERE cat != 'Books' AND cat != 'Genre Fiction'
        GROUP BY cat ORDER BY cnt DESC LIMIT 15
    """).fetchall()
    for cat, cnt in cats:
        print(f"  {cnt:>6,}  {cat}")

    # Description stats
    print("\nDescription length (characters):")
    desc_stats = dst.execute("""
        SELECT
            AVG(LENGTH(array_to_string(description, ' '))) as avg_len,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(array_to_string(description, ' '))) as median_len,
            MIN(LENGTH(array_to_string(description, ' '))) as min_len,
            MAX(LENGTH(array_to_string(description, ' '))) as max_len
        FROM books
    """).fetchone()
    print(f"  Avg: {desc_stats[0]:,.0f} chars (~{desc_stats[0]/4:,.0f} tokens)")
    print(f"  Median: {desc_stats[1]:,.0f} chars (~{desc_stats[1]/4:,.0f} tokens)")
    print(f"  Min: {desc_stats[2]:,} | Max: {desc_stats[3]:,}")

    # Token cost estimate
    avg_tokens = desc_stats[0] / 4  # rough estimate
    total_tokens = count * min(avg_tokens, 2048)  # capped at model max
    cost = (total_tokens / 1_000_000) * 0.15
    print(f"\nEmbedding cost estimate (gemini-embedding-001 @ $0.15/1M tokens):")
    print(f"  {count:,} books × ~{min(avg_tokens, 2048):,.0f} tokens = {total_tokens:,.0f} tokens")
    print(f"  Estimated cost: ${cost:.2f}")

    # Top 10 books
    print("\nTop 10 books by popularity:")
    top = dst.execute("""
        SELECT title, author_name, rating_number, average_rating
        FROM books ORDER BY rating_number DESC LIMIT 10
    """).fetchall()
    for i, (title, author, ratings, avg) in enumerate(top, 1):
        print(f"  {i:2}. {title[:55]}")
        print(f"      {author} | {ratings:,} ratings | {avg} stars")

    src.close()
    dst.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract popular fiction to DuckDB")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max books to extract (default: all matching)")
    args = parser.parse_args()
    extract(limit=args.limit)
