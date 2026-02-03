#!/usr/bin/env python3
"""
Import books from JSONL into DuckDB.

Usage:
    python db/import_books.py           # Full import
    python db/import_books.py --sample  # Import first 10,000 for testing
"""

import argparse
import time
from pathlib import Path

import duckdb

JSONL_PATH = Path("data/meta_Books.jsonl")
DB_PATH = Path("data/books.duckdb")


def import_books(sample: bool = False):
    """Import books from JSONL to DuckDB."""
    if not JSONL_PATH.exists():
        print(f"Error: {JSONL_PATH} not found")
        return

    # Remove existing database if it exists
    if DB_PATH.exists():
        print(f"Removing existing database: {DB_PATH}")
        DB_PATH.unlink()

    print(f"Importing from {JSONL_PATH} to {DB_PATH}")
    start_time = time.time()

    conn = duckdb.connect(str(DB_PATH))

    # Build the query
    limit_clause = "LIMIT 10000" if sample else ""

    query = f"""
        CREATE TABLE books AS
        SELECT
            row_number() OVER () as id,
            title,
            author->>'name' as author_name,
            author->>'avatar' as author_avatar,
            main_category,
            categories,
            average_rating,
            rating_number,
            price,
            description,
            features,
            subtitle,
            details->>'ISBN 10' as isbn_10,
            details->>'ISBN 13' as isbn_13,
            details->>'Publisher' as publisher,
            details->>'Language' as language,
            details->>'Hardcover' as hardcover,
            details->>'Paperback' as paperback,
            images,
            parent_asin,
            store
        FROM read_json_auto(
            '{JSONL_PATH}',
            maximum_object_size=50000000,
            ignore_errors=true
        )
        {limit_clause}
    """

    print("Creating table (this may take a while for full import)...")
    conn.execute(query)

    # Get row count
    count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    elapsed = time.time() - start_time

    print(f"\nImported {count:,} books in {elapsed:.1f} seconds")
    print(f"Database size: {DB_PATH.stat().st_size / (1024*1024):.1f} MB")

    # Show sample
    print("\nSample records:")
    result = conn.execute("""
        SELECT title, author_name, main_category
        FROM books
        LIMIT 5
    """).fetchall()

    for row in result:
        title = (row[0][:50] + '...') if row[0] and len(row[0]) > 50 else row[0]
        print(f"  - {title} | {row[1]} | {row[2]}")

    conn.close()
    print(f"\nDatabase saved to: {DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import books to DuckDB")
    parser.add_argument("--sample", action="store_true",
                        help="Import only first 10,000 records for testing")
    args = parser.parse_args()

    import_books(sample=args.sample)
