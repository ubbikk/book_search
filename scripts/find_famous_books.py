#!/usr/bin/env python3
"""Search for famous books in the Amazon JSONL dataset in a single pass."""

import json
from pathlib import Path

FILE_PATH = Path("data/meta_Books.jsonl")

# Famous books to search for - (search_term, expected_author_substring)
TARGETS = [
    ("To Kill a Mockingbird", "Harper Lee"),
    ("The Great Gatsby", "Fitzgerald"),
    ("Nineteen Eighty", "Orwell"),
    ("Pride And Prejudice", "Austen"),
    ("The Catcher in the Rye", "Salinger"),
    ("The Hobbit", "Tolkien"),
    ("Brave New World", "Huxley"),
    ("Fahrenheit 451", "Bradbury"),
    ("The Lord of the Rings", "Tolkien"),
    ("Animal Farm", "Orwell"),
    ("One Hundred Years of Solitude", "Marquez"),
    ("The Picture of Dorian Gray", "Wilde"),
    ("Dune", "Herbert"),
    ("Slaughterhouse-Five", "Vonnegut"),
    ("The Road", "McCarthy"),
    ("Gone Girl", "Flynn"),
    ("The Handmaid's Tale", "Atwood"),
    ("Sapiens", "Harari"),
    ("Educated", "Westover"),
    ("Where the Crawdads Sing", "Owens"),
    ("The Night Circus", "Morgenstern"),
    ("Project Hail Mary", "Weir"),
    ("Atomic Habits", "Clear"),
    ("Thinking, Fast and Slow", "Kahneman"),
    ("The Midnight Library", "Haig"),
    ("Circe", "Miller"),
    ("The Song of Achilles", "Miller"),
    ("A Court of Thorns and Roses", "Maas"),
    ("The Silent Patient", "Michaelides"),
    ("Becoming", "Obama"),
    ("Ender's Game", "Card"),
    ("The Martian", "Weir"),
    ("Ready Player One", "Cline"),
    ("The Da Vinci Code", "Brown"),
    ("The Hunger Games", "Collins"),
    ("Outlander", "Gabaldon"),
    ("Life of Pi", "Martel"),
    ("The Kite Runner", "Hosseini"),
]

found = {}
found_keys = set()

print(f"Searching for {len(TARGETS)} famous books...")
print(f"Scanning {FILE_PATH}...")

with open(FILE_PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if len(found) >= len(TARGETS):
            break

        record = json.loads(line)
        title = record.get("title", "")
        main_cat = record.get("main_category", "")

        # Only consider actual books
        if main_cat not in ("Books",):
            continue

        # Check author
        author_info = record.get("author")
        if not author_info:
            continue
        author_name = author_info.get("name", "") if isinstance(author_info, dict) else str(author_info)

        # Check images
        images = record.get("images", [])
        if not images:
            continue
        image_url = None
        for img in images:
            if isinstance(img, dict) and img.get("large"):
                image_url = img["large"]
                break
        if not image_url:
            continue

        # Check rating (want popular editions)
        rating_number = record.get("rating_number", 0) or 0

        for search_title, search_author in TARGETS:
            key = (search_title, search_author)
            if key in found_keys:
                continue

            # Title must start with the search term (avoid study guides etc)
            if not title.lower().startswith(search_title.lower()):
                continue

            if search_author.lower() not in author_name.lower():
                continue

            # Prefer high-rating editions
            if key in found and found[key]["rating_number"] >= rating_number:
                continue

            desc = record.get("features", [])
            desc_text = " ".join(desc) if isinstance(desc, list) else str(desc)
            if len(desc_text) > 500:
                desc_text = desc_text[:500]

            found[key] = {
                "line": i,
                "parent_asin": record.get("parent_asin"),
                "title": title.split(":")[0].split("(")[0].strip(),
                "full_title": title,
                "author": author_name,
                "description": desc_text,
                "average_rating": record.get("average_rating"),
                "rating_number": rating_number,
                "price": record.get("price"),
                "image_url": image_url,
                "categories": record.get("categories", []),
            }

            if rating_number > 1000:
                found_keys.add(key)  # Lock in high-rated editions

            print(f"  Found: {title[:60]} by {author_name} (ratings: {rating_number})")

        if i % 100000 == 0 and i > 0:
            print(f"  ... scanned {i:,} records, found {len(found)}/{len(TARGETS)}")

print(f"\n{'='*60}")
print(f"Found {len(found)}/{len(TARGETS)} books")
print(f"{'='*60}\n")

for key, book in sorted(found.items(), key=lambda x: -(x[1]["rating_number"] or 0)):
    print(f"  {book['title'][:40]:40s} | {book['author']:25s} | ratings: {book['rating_number']:>8,} | ASIN: {book['parent_asin']}")

# Save results
output = list(found.values())
with open("data/famous_books_candidates.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\nSaved {len(output)} books to data/famous_books_candidates.json")
