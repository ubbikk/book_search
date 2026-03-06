#!/usr/bin/env python3
"""
Extract the 9 demo books from Amazon dataset for the scripted chatbot demo.
"""

import json
from pathlib import Path

# Target ASINs for demo books
TARGET_BOOKS = {
    # Journey 1: "A book I loved" (The Martian → humor, fast pace)
    "0593135202": {
        "journey": 1,
        "explanation": "Same author, same energy — lone scientist solving impossible problems with wit and duct tape. If you loved The Martian, this is a no-brainer."
    },
    "0593410254": {
        "journey": 1,
        "explanation": "Four retirees solve murders. Sounds cozy, but it's sharp, funny, and moves fast. Very different setting, same \"smart people being clever\" vibe."
    },
    "0060853980": {
        "journey": 1,
        "explanation": "An angel and a demon try to stop the apocalypse. Absurdist humor, snappy dialogue, never takes itself seriously."
    },

    # Journey 2: "It's a gift" (Mom who loved Where the Crawdads Sing)
    "0312577230": {
        "journey": 2,
        "explanation": "Alaska wilderness, complicated family, gorgeous writing. Same \"place as character\" feel as Crawdads, but with more dramatic stakes."
    },
    "0593599004": {
        "journey": 2,
        "explanation": "Based on a true story — haunting, emotional, beautifully told. If she cried at Crawdads, she'll cry at this (in a good way)."
    },
    "1250080401": {
        "journey": 2,
        "explanation": "Two sisters in WWII France. Slower burn, deeply moving, the kind of book you think about for weeks after."
    },

    # Journey 3: "Surprise me" (Mind games thriller, no cop-out endings)
    "B08HCQ2D8N": {
        "journey": 3,
        "explanation": "A woman shoots her husband and never speaks again. The twist is earned and you'll want to immediately reread the first chapter."
    },
    "0385366752": {
        "journey": 3,
        "explanation": "If you somehow haven't read it — it's the gold standard for \"mind games.\" The midpoint turn is legendary."
    },
    "B07H3BCT1B": {
        "journey": 3,
        "explanation": "Groundhog Day meets Agatha Christie. Complex, rewarding, and the solution actually makes sense when you get there."
    },
}

def extract_books():
    """Extract target books from the Amazon dataset."""
    found_books = {}

    print("Scanning Amazon dataset for demo books...")
    with open("data/meta_Books.jsonl", "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i % 500000 == 0:
                print(f"  Processed {i:,} records...")

            record = json.loads(line)
            asin = record.get("parent_asin", "")

            if asin in TARGET_BOOKS and asin not in found_books:
                # Extract author name
                author_data = record.get("author", {})
                if isinstance(author_data, dict):
                    author_name = author_data.get("name", "Unknown")
                else:
                    author_name = str(author_data) if author_data else "Unknown"

                # Extract image URL
                images = record.get("images", [])
                image_url = ""
                if images and isinstance(images, list) and len(images) > 0:
                    img = images[0]
                    if isinstance(img, dict):
                        image_url = img.get("large", img.get("medium", ""))
                    elif isinstance(img, str):
                        image_url = img

                # Extract description
                desc_parts = record.get("description", [])
                description = ""
                if isinstance(desc_parts, list):
                    # Filter out review labels, keep actual description text
                    desc_text = []
                    skip_next = False
                    for part in desc_parts:
                        if skip_next:
                            skip_next = False
                            continue
                        if part in ["Review", "About the Author", "From the Back Cover",
                                   "From Publishers Weekly", "Amazon.com Review",
                                   "From School Library Journal", "Excerpt. © Reprinted by permission. All rights reserved.",
                                   "Book Description"]:
                            skip_next = True
                            continue
                        if part and len(part) > 50:  # Keep substantial text
                            desc_text.append(part)
                    description = " ".join(desc_text[:2])[:500]  # First 500 chars

                found_books[asin] = {
                    "asin": asin,
                    "title": record.get("title", "").split(":")[0].strip(),  # Clean title
                    "full_title": record.get("title", ""),
                    "author": author_name,
                    "description": description,
                    "average_rating": record.get("average_rating"),
                    "rating_number": record.get("rating_number"),
                    "price": record.get("price"),
                    "image_url": image_url,
                    "categories": record.get("categories", []),
                    "journey": TARGET_BOOKS[asin]["journey"],
                    "explanation": TARGET_BOOKS[asin]["explanation"],
                }

                print(f"  Found: {found_books[asin]['title']} by {author_name}")

            # Early exit if all found
            if len(found_books) == len(TARGET_BOOKS):
                break

    return found_books


def main():
    books = extract_books()

    # Check for missing books
    missing = set(TARGET_BOOKS.keys()) - set(books.keys())
    if missing:
        print(f"\nWarning: Could not find books with ASINs: {missing}")

    # Organize by journey
    output = {
        "journey_1": [],
        "journey_2": [],
        "journey_3": [],
    }

    for asin, book in books.items():
        journey_key = f"journey_{book['journey']}"
        output[journey_key].append(book)

    # Write output
    output_path = Path("data/demo_books.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(books)} books to {output_path}")
    print("\nBooks by journey:")
    for j in [1, 2, 3]:
        print(f"  Journey {j}: {len(output[f'journey_{j}'])} books")


if __name__ == "__main__":
    main()
