#!/usr/bin/env python3
"""
Query books from DuckDB database.

Can work with either:
1. Pre-imported DuckDB database (fast)
2. Direct JSONL queries (no import needed, slower)

Usage:
    python db/query_books.py title "harry potter"
    python db/query_books.py author "stephen king"
    python db/query_books.py genre "Science Fiction"
    python db/query_books.py search --title "game" --genre "Fantasy"
    python db/query_books.py --direct title "harry potter"  # Query JSONL directly
"""

import argparse
from pathlib import Path
from typing import Optional

import duckdb

DB_PATH = Path("data/books.duckdb")
JSONL_PATH = Path("data/meta_Books.jsonl")


def get_connection(direct: bool = False) -> duckdb.DuckDBPyConnection:
    """Get database connection."""
    if direct or not DB_PATH.exists():
        if not JSONL_PATH.exists():
            raise FileNotFoundError(f"Neither {DB_PATH} nor {JSONL_PATH} found")
        return duckdb.connect()  # In-memory for direct JSONL queries
    return duckdb.connect(str(DB_PATH), read_only=True)


def _get_source(direct: bool) -> str:
    """Get the data source (table or JSONL read)."""
    if direct or not DB_PATH.exists():
        return f"""(
            SELECT
                title,
                author->>'name' as author_name,
                main_category,
                categories,
                average_rating,
                rating_number,
                price,
                description
            FROM read_json_auto('{JSONL_PATH}', maximum_object_size=50000000, ignore_errors=true)
        )"""
    return "books"


def search_by_title(query: str, limit: int = 20, direct: bool = False) -> list[dict]:
    """Search books by title (case-insensitive contains)."""
    conn = get_connection(direct)
    source = _get_source(direct)

    sql = f"""
        SELECT title, author_name, main_category, average_rating, price
        FROM {source}
        WHERE title ILIKE ?
        ORDER BY rating_number DESC NULLS LAST
        LIMIT ?
    """
    # Add wildcards for contains search
    pattern = f"%{query}%"

    result = conn.execute(sql, [pattern, limit]).fetchall()
    conn.close()

    return [
        {
            "title": row[0],
            "author": row[1],
            "category": row[2],
            "rating": row[3],
            "price": row[4],
        }
        for row in result
    ]


def search_by_author(query: str, limit: int = 20, direct: bool = False) -> list[dict]:
    """Search books by author name (case-insensitive contains)."""
    conn = get_connection(direct)
    source = _get_source(direct)

    sql = f"""
        SELECT title, author_name, main_category, average_rating, price
        FROM {source}
        WHERE author_name ILIKE ?
        ORDER BY average_rating DESC NULLS LAST
        LIMIT ?
    """
    pattern = f"%{query}%"

    result = conn.execute(sql, [pattern, limit]).fetchall()
    conn.close()

    return [
        {
            "title": row[0],
            "author": row[1],
            "category": row[2],
            "rating": row[3],
            "price": row[4],
        }
        for row in result
    ]


def filter_by_genre(genre: str, limit: int = 20, direct: bool = False) -> list[dict]:
    """Filter books by category/genre (checks both main_category and categories array)."""
    conn = get_connection(direct)
    source = _get_source(direct)

    sql = f"""
        SELECT title, author_name, main_category, average_rating, price
        FROM {source}
        WHERE main_category ILIKE ?
           OR list_contains(categories, ?)
        ORDER BY average_rating DESC NULLS LAST
        LIMIT ?
    """
    pattern = f"%{genre}%"

    result = conn.execute(sql, [pattern, genre, limit]).fetchall()
    conn.close()

    return [
        {
            "title": row[0],
            "author": row[1],
            "category": row[2],
            "rating": row[3],
            "price": row[4],
        }
        for row in result
    ]


def search_combined(
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    min_rating: Optional[float] = None,
    limit: int = 20,
    direct: bool = False,
) -> list[dict]:
    """Combined search with multiple filters."""
    conn = get_connection(direct)
    source = _get_source(direct)

    conditions = []
    params = []

    if title:
        conditions.append("title ILIKE ?")
        params.append(f"%{title}%")

    if author:
        conditions.append("author_name ILIKE ?")
        params.append(f"%{author}%")

    if genre:
        conditions.append("(main_category ILIKE ? OR list_contains(categories, ?))")
        params.extend([f"%{genre}%", genre])

    if min_rating:
        conditions.append("average_rating >= ?")
        params.append(min_rating)

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)

    sql = f"""
        SELECT title, author_name, main_category, average_rating, price, description
        FROM {source}
        WHERE {where_clause}
        ORDER BY average_rating DESC NULLS LAST
        LIMIT ?
    """

    result = conn.execute(sql, params).fetchall()
    conn.close()

    return [
        {
            "title": row[0],
            "author": row[1],
            "category": row[2],
            "rating": row[3],
            "price": row[4],
            "description": row[5],
        }
        for row in result
    ]


def get_genres(limit: int = 50, direct: bool = False) -> list[tuple[str, int]]:
    """Get list of genres with book counts."""
    conn = get_connection(direct)
    source = _get_source(direct)

    sql = f"""
        SELECT main_category, COUNT(*) as count
        FROM {source}
        WHERE main_category IS NOT NULL
        GROUP BY main_category
        ORDER BY count DESC
        LIMIT ?
    """

    result = conn.execute(sql, [limit]).fetchall()
    conn.close()

    return [(row[0], row[1]) for row in result]


def print_results(results: list[dict], verbose: bool = False):
    """Pretty print search results."""
    if not results:
        print("No results found.")
        return

    print(f"\nFound {len(results)} results:\n")
    for i, book in enumerate(results, 1):
        title = book["title"] or "Unknown"
        if len(title) > 60:
            title = title[:57] + "..."

        author = book.get("author") or "Unknown"
        category = book.get("category") or "N/A"
        rating = book.get("rating")
        rating_str = f"{rating:.1f}" if rating else "N/A"
        price = book.get("price")
        price_str = f"${price:.2f}" if price else "N/A"

        print(f"{i:2}. {title}")
        print(f"    Author: {author} | Category: {category}")
        print(f"    Rating: {rating_str} | Price: {price_str}")

        if verbose and book.get("description"):
            desc = book["description"]
            if isinstance(desc, list):
                desc = " ".join(desc)
            if desc and len(desc) > 200:
                desc = desc[:197] + "..."
            if desc:
                print(f"    Description: {desc}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query books from DuckDB")
    parser.add_argument("--direct", action="store_true",
                        help="Query JSONL directly (no import needed, slower)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Maximum results to return")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show descriptions")

    subparsers = parser.add_subparsers(dest="command", help="Query type")

    # Title search
    title_parser = subparsers.add_parser("title", help="Search by title")
    title_parser.add_argument("query", help="Title to search for")

    # Author search
    author_parser = subparsers.add_parser("author", help="Search by author")
    author_parser.add_argument("query", help="Author name to search for")

    # Genre filter
    genre_parser = subparsers.add_parser("genre", help="Filter by genre")
    genre_parser.add_argument("query", help="Genre/category to filter by")

    # Combined search
    search_parser = subparsers.add_parser("search", help="Combined search")
    search_parser.add_argument("--title", "-t", help="Title contains")
    search_parser.add_argument("--author", "-a", help="Author contains")
    search_parser.add_argument("--genre", "-g", help="Genre/category")
    search_parser.add_argument("--min-rating", "-r", type=float, help="Minimum rating")

    # List genres
    subparsers.add_parser("genres", help="List all genres with counts")

    args = parser.parse_args()

    if args.command == "title":
        results = search_by_title(args.query, args.limit, args.direct)
        print_results(results, args.verbose)

    elif args.command == "author":
        results = search_by_author(args.query, args.limit, args.direct)
        print_results(results, args.verbose)

    elif args.command == "genre":
        results = filter_by_genre(args.query, args.limit, args.direct)
        print_results(results, args.verbose)

    elif args.command == "search":
        results = search_combined(
            title=args.title,
            author=args.author,
            genre=args.genre,
            min_rating=args.min_rating,
            limit=args.limit,
            direct=args.direct,
        )
        print_results(results, args.verbose)

    elif args.command == "genres":
        genres = get_genres(args.limit, args.direct)
        print("\nGenres (by book count):\n")
        for genre, count in genres:
            print(f"  {count:>8,}  {genre}")

    else:
        parser.print_help()
