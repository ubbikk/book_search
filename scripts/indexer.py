"""Index all FB2 files and create a searchable JSON index."""

import json
import os
import sys
from pathlib import Path

from parser import parse_fb2


def build_index(source_dir: str, output_file: str, covers_dir: str):
    """
    Parse all FB2 files and create a JSON index.

    Args:
        source_dir: Directory containing FB2 files
        output_file: Path to output JSON file
        covers_dir: Directory to save extracted covers
    """
    books = []
    errors = []

    fb2_files = list(Path(source_dir).glob('*.fb2'))
    total = len(fb2_files)

    print(f"Found {total} FB2 files to process...")

    for i, filepath in enumerate(fb2_files, 1):
        if i % 100 == 0 or i == total:
            print(f"Processing {i}/{total}...")

        try:
            metadata = parse_fb2(str(filepath), covers_dir=covers_dir)
            if 'error' in metadata:
                errors.append(metadata)
            else:
                books.append(metadata)
        except Exception as e:
            errors.append({
                'filepath': str(filepath),
                'error': str(e)
            })

    # Sort by title
    books.sort(key=lambda x: (x.get('title') or '').lower())

    # Save index
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Indexed {len(books)} books.")
    print(f"Index saved to: {output_file}")

    if errors:
        print(f"Errors: {len(errors)} files failed to parse")
        error_file = output_file.replace('.json', '_errors.json')
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"Error log saved to: {error_file}")


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))

    source_dir = os.path.join(base_dir, 'data', 'flatten')
    output_file = os.path.join(base_dir, 'data', 'index.json')
    covers_dir = os.path.join(base_dir, 'static', 'covers')

    build_index(source_dir, output_file, covers_dir)
