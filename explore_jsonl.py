#!/usr/bin/env python3
"""
Explore large JSONL files without loading them into memory.
Usage: python explore_jsonl.py [command] [options]
"""

import json
import sys
from collections import Counter
from pathlib import Path

FILE_PATH = Path("data/meta_Books.jsonl")


def count_lines():
    """Count total number of records."""
    count = 0
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    print(f"Total records: {count:,}")


def show_schema(n=10):
    """Show all unique keys from first n records."""
    all_keys = set()
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            record = json.loads(line)
            all_keys.update(record.keys())

    print(f"Keys found in first {n} records:")
    for key in sorted(all_keys):
        print(f"  - {key}")


def show_sample(n=3):
    """Show first n complete records (pretty printed)."""
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            record = json.loads(line)
            print(f"\n{'='*60}")
            print(f"Record {i + 1}:")
            print('='*60)
            print(json.dumps(record, indent=2, ensure_ascii=False)[:3000])
            if len(json.dumps(record)) > 3000:
                print("... [truncated]")


def show_field(field_name, n=10):
    """Show values of a specific field from first n records."""
    print(f"Field '{field_name}' in first {n} records:\n")
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            record = json.loads(line)
            value = record.get(field_name, "<MISSING>")
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            print(f"{i + 1}: {value_str}")


def field_stats(field_name, sample_size=1000):
    """Get statistics about a field (type, null count, unique values)."""
    types = Counter()
    null_count = 0
    values = []

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= sample_size:
                break
            record = json.loads(line)
            value = record.get(field_name)

            if value is None:
                null_count += 1
                types['null'] += 1
            else:
                types[type(value).__name__] += 1
                if isinstance(value, (str, int, float, bool)):
                    values.append(value)
                elif isinstance(value, list):
                    values.append(f"list[{len(value)}]")

    print(f"Field: {field_name}")
    print(f"Sample size: {sample_size}")
    print(f"Null count: {null_count}")
    print(f"Types: {dict(types)}")

    if values:
        unique = len(set(str(v) for v in values))
        print(f"Unique values (in sample): {unique}")
        print(f"\nSample values:")
        for v in values[:5]:
            print(f"  - {str(v)[:100]}")


def search(field_name, query, max_results=5):
    """Search for records where field contains query string."""
    found = 0
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if found >= max_results:
                break
            record = json.loads(line)
            value = str(record.get(field_name, ""))
            if query.lower() in value.lower():
                found += 1
                print(f"\n{'='*60}")
                print(f"Record {i + 1} (line {i}):")
                print('='*60)
                print(json.dumps(record, indent=2, ensure_ascii=False)[:2000])


def interactive():
    """Interactive exploration mode."""
    print("JSONL Explorer - Interactive Mode")
    print("="*40)
    print("Commands:")
    print("  count        - Count total records")
    print("  schema [n]   - Show keys from first n records")
    print("  sample [n]   - Show first n records")
    print("  field <name> [n] - Show field values")
    print("  stats <name> [n] - Field statistics")
    print("  search <field> <query> - Search records")
    print("  quit         - Exit")
    print()

    while True:
        try:
            cmd = input("> ").strip().split()
            if not cmd:
                continue

            action = cmd[0].lower()

            if action == "quit" or action == "q":
                break
            elif action == "count":
                count_lines()
            elif action == "schema":
                n = int(cmd[1]) if len(cmd) > 1 else 10
                show_schema(n)
            elif action == "sample":
                n = int(cmd[1]) if len(cmd) > 1 else 3
                show_sample(n)
            elif action == "field":
                if len(cmd) < 2:
                    print("Usage: field <name> [n]")
                    continue
                n = int(cmd[2]) if len(cmd) > 2 else 10
                show_field(cmd[1], n)
            elif action == "stats":
                if len(cmd) < 2:
                    print("Usage: stats <name> [sample_size]")
                    continue
                n = int(cmd[2]) if len(cmd) > 2 else 1000
                field_stats(cmd[1], n)
            elif action == "search":
                if len(cmd) < 3:
                    print("Usage: search <field> <query>")
                    continue
                search(cmd[1], " ".join(cmd[2:]))
            else:
                print(f"Unknown command: {action}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        interactive()
    else:
        cmd = sys.argv[1]
        if cmd == "count":
            count_lines()
        elif cmd == "schema":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            show_schema(n)
        elif cmd == "sample":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            show_sample(n)
        elif cmd == "field":
            show_field(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
        elif cmd == "stats":
            field_stats(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1000)
        elif cmd == "search":
            search(sys.argv[2], " ".join(sys.argv[3:]))
        else:
            print(f"Unknown command: {cmd}")
