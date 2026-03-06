#!/usr/bin/env python3
"""Build a demo index.json with 24 famous English books from the Amazon dataset.

Downloads cover images and creates index.json in the format expected by app.py.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

CANDIDATES_PATH = Path("data/famous_books_candidates.json")
INDEX_PATH = Path("data/index.json")
COVERS_DIR = Path("static/covers")

# Map parent_asin to clean metadata overrides
# (title, genres, year, description_override)
SELECTED_BOOKS = {
    "1846572568": {
        "title": "To Kill a Mockingbird",
        "genres": ["Classics", "Literary Fiction", "Southern Gothic"],
        "year": "1960",
    },
    "1597371416": {
        "title": "Pride and Prejudice",
        "genres": ["Classics", "Romance", "Literary Fiction"],
        "year": "1813",
    },
    "B0018SWBQ4": {
        "title": "The Great Gatsby",
        "genres": ["Classics", "Literary Fiction", "American Literature"],
        "year": "1925",
        "annotation": "The Great Gatsby, F. Scott Fitzgerald's third book, stands as the supreme achievement of his career. The story of the mysteriously wealthy Jay Gatsby and his love for the beautiful Daisy Buchanan is an exquisitely crafted tale of America in the 1920s. This classic novel of the Jazz Age has been acclaimed by generations of readers.",
    },
    "0140126716": {
        "title": "1984",
        "genres": ["Classics", "Dystopian", "Science Fiction", "Political Fiction"],
        "year": "1949",
    },
    "0451526341": {
        "title": "Animal Farm",
        "genres": ["Classics", "Satire", "Political Fiction", "Allegory"],
        "year": "1945",
    },
    "1509827838": {
        "title": "The Picture of Dorian Gray",
        "genres": ["Classics", "Gothic", "Literary Fiction", "Philosophy"],
        "year": "1890",
    },
    "0060929871": {
        "title": "Brave New World",
        "genres": ["Classics", "Dystopian", "Science Fiction"],
        "year": "1932",
    },
    "0316769533": {
        "title": "The Catcher in the Rye",
        "genres": ["Classics", "Literary Fiction", "Coming-of-Age"],
        "year": "1951",
    },
    "B000UEV18Q": {
        "title": "Dune",
        "genres": ["Science Fiction", "Fantasy", "Classics"],
        "year": "1965",
        "annotation": "Set on the desert planet Arrakis, Dune is the story of Paul Atreides—who would become known as Muad'Dib—and of a great family's ambition to bring to fruition humankind's most ancient and unattainable dream. A stunning blend of adventure and mysticism, environmentalism and politics, Dune is a powerful, fantastical tale that takes an unprecedented look into our universe.",
    },
    "0395177111": {
        "title": "The Hobbit",
        "genres": ["Fantasy", "Classics", "Adventure"],
        "year": "1937",
    },
    "0812533550": {
        "title": "Ender's Game",
        "genres": ["Science Fiction", "Military Fiction", "Young Adult"],
        "year": "1985",
        "annotation": "In order to develop a secure defense against a hostile alien race's next attack, government combatants devise a program to train the brightest young minds in combat strategy. The game is more than just a game—it is training for what could be the battle to save Earth.",
    },
    "038549081X": {
        "title": "The Handmaid's Tale",
        "genres": ["Dystopian", "Science Fiction", "Feminist Fiction"],
        "year": "1985",
    },
    "0593135202": {
        "title": "Project Hail Mary",
        "genres": ["Science Fiction", "Adventure", "Humor"],
        "year": "2021",
    },
    "1101903589": {
        "title": "The Martian",
        "genres": ["Science Fiction", "Thriller", "Adventure"],
        "year": "2014",
    },
    "B09VGTY199": {
        "title": "Where the Crawdads Sing",
        "genres": ["Literary Fiction", "Mystery", "Coming-of-Age"],
        "year": "2018",
    },
    "1846555248": {
        "title": "The Night Circus",
        "genres": ["Fantasy", "Romance", "Historical Fiction"],
        "year": "2011",
        "annotation": "The circus arrives without warning. No announcements precede it. It is simply there, when yesterday it was not. The Night Circus tells the story of two young magicians, Celia and Marco, who are pitted against each other in a contest that will determine their fates—and the fate of the enchanted circus that serves as the venue for their rivalry.",
    },
    "0655697284": {
        "title": "The Midnight Library",
        "genres": ["Literary Fiction", "Fantasy", "Philosophy"],
        "year": "2020",
    },
    "1526610140": {
        "title": "Circe",
        "genres": ["Fantasy", "Mythology", "Literary Fiction", "Historical Fiction"],
        "year": "2018",
        "annotation": "In the house of Helios, god of the sun, a daughter is born. But Circe is a strange child—not powerful like her father, nor viciously alluring like her mother. Turning to the world of mortals for companionship, she discovers that she does possess power—the power of witchcraft, which can transform rivals into monsters and menace the gods themselves.",
    },
    "0062060627": {
        "title": "The Song of Achilles",
        "genres": ["Fantasy", "Mythology", "Romance", "Historical Fiction"],
        "year": "2011",
    },
    "B001I3XCG2": {
        "title": "The Kite Runner",
        "genres": ["Literary Fiction", "Historical Fiction", "Drama"],
        "year": "2003",
        "annotation": "The unforgettable, heartbreaking story of the unlikely friendship between a wealthy boy and the son of his father's servant, The Kite Runner is a beautifully crafted novel set in a country that is in the process of being destroyed. It is about the power of reading, the price of betrayal, and the possibility of redemption.",
    },
    "B08HCQ2D8N": {
        "title": "The Silent Patient",
        "genres": ["Thriller", "Mystery", "Psychological Fiction"],
        "year": "2019",
        "annotation": "Alicia Berenson's life is seemingly perfect. A famous painter married to an in-demand fashion photographer, she lives in a grand house overlooking a park in one of London's most desirable areas. One evening her husband Gabriel returns home late from a fashion shoot, and Alicia shoots him five times in the face, and then never speaks another word.",
    },
    "0099560437": {
        "title": "Ready Player One",
        "genres": ["Science Fiction", "Gaming", "Adventure", "Pop Culture"],
        "year": "2011",
        "annotation": "In the year 2045, reality is an ugly place. The only time Wade Watts really feels alive is when he's jacked into the OASIS, a vast virtual utopia that lets you be anything you want to be. And like most of humanity, Wade dreams of discovering the ultimate lottery ticket hidden within this virtual world.",
    },
    "0525528059": {
        "title": "Educated",
        "genres": ["Memoir", "Non-Fiction", "Biography"],
        "year": "2018",
    },
    "0141033576": {
        "title": "Thinking, Fast and Slow",
        "genres": ["Non-Fiction", "Psychology", "Science", "Economics"],
        "year": "2011",
        "annotation": "In this international bestseller, Daniel Kahneman, the renowned psychologist and winner of the Nobel Prize in Economics, takes us on a groundbreaking tour of the mind and explains the two systems that drive the way we think—fast, intuitive thinking, and slow, deliberate thinking—and how they shape our judgments and decisions.",
    },
}


def slugify(text: str) -> str:
    """Convert text to a URL-safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60]


def download_cover(url: str, filename: str) -> bool:
    """Download a cover image. Returns True on success."""
    filepath = COVERS_DIR / filename
    if filepath.exists():
        print(f"    Cover already exists: {filename}")
        return True

    # Try to get a higher-res version by modifying the Amazon URL
    # Replace sizing params to get larger image
    hi_res_url = re.sub(
        r"\._[A-Z0-9,_]+_\.",
        ".",
        url,
    )

    for try_url in [hi_res_url, url]:
        try:
            req = urllib.request.Request(
                try_url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if len(data) < 500:
                    continue
                filepath.write_bytes(data)
                print(f"    Downloaded: {filename} ({len(data):,} bytes)")
                return True
        except Exception as e:
            print(f"    Failed ({try_url[:60]}...): {e}")

    return False


def build_index():
    """Build index.json from selected candidates."""
    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    with open(CANDIDATES_PATH) as f:
        candidates = json.load(f)

    # Index candidates by parent_asin
    by_asin = {c["parent_asin"]: c for c in candidates}

    books = []
    for asin, overrides in SELECTED_BOOKS.items():
        candidate = by_asin.get(asin)
        if not candidate:
            print(f"  WARNING: ASIN {asin} not found in candidates!")
            continue

        title = overrides["title"]
        slug = slugify(title)

        # Determine file extension from URL
        image_url = candidate["image_url"]
        ext = ".jpg"
        if ".png" in image_url.lower():
            ext = ".png"
        elif ".webp" in image_url.lower():
            ext = ".webp"
        cover_filename = f"{slug}{ext}"

        print(f"  Processing: {title}")
        download_cover(image_url, cover_filename)

        # Use override annotation or candidate description
        annotation = overrides.get("annotation") or candidate.get("description", "")

        book = {
            "title": title,
            "authors": [candidate["author"]],
            "annotation": annotation,
            "genres": overrides["genres"],
            "year": overrides["year"],
            "cover": cover_filename,
            "lang": "en",
            "average_rating": candidate.get("average_rating"),
            "rating_number": candidate.get("rating_number"),
        }
        books.append(book)

    # Sort: classics first, then by rating count descending
    books.sort(key=lambda b: -(b.get("rating_number") or 0))

    # Write index
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(books)} books to {INDEX_PATH}")
    return books


if __name__ == "__main__":
    build_index()
