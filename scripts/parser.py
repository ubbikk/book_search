"""FB2 file parser for extracting book metadata."""

import base64
import hashlib
import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET


def parse_fb2(filepath: str, covers_dir: str = None) -> dict:
    """
    Parse an FB2 file and extract metadata.

    Args:
        filepath: Path to the FB2 file
        covers_dir: Directory to save extracted cover images (optional)

    Returns:
        Dictionary with book metadata
    """
    # Try different encodings
    content = None
    for encoding in ['utf-8', 'windows-1251', 'cp1251']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        # Fallback: read as binary and try to detect
        with open(filepath, 'rb') as f:
            raw = f.read()
        # Check XML declaration for encoding
        if b'windows-1251' in raw[:100].lower():
            content = raw.decode('windows-1251', errors='replace')
        else:
            content = raw.decode('utf-8', errors='replace')

    # Parse XML
    try:
        # Remove namespace for easier parsing
        content = re.sub(r'\sxmlns[^"]*"[^"]*"', '', content)
        content = re.sub(r'\sl:', ' ', content)
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return {'error': str(e), 'filepath': filepath}

    metadata = {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'title': None,
        'authors': [],
        'year': None,
        'annotation': None,
        'genres': [],
        'lang': None,
        'cover': None,
    }

    # Find description/title-info
    title_info = root.find('.//title-info')
    if title_info is not None:
        # Title
        book_title = title_info.find('book-title')
        if book_title is not None:
            metadata['title'] = book_title.text

        # Authors
        for author in title_info.findall('author'):
            first_name = author.find('first-name')
            last_name = author.find('last-name')
            middle_name = author.find('middle-name')

            name_parts = []
            if first_name is not None and first_name.text:
                name_parts.append(first_name.text)
            if middle_name is not None and middle_name.text:
                name_parts.append(middle_name.text)
            if last_name is not None and last_name.text:
                name_parts.append(last_name.text)

            if name_parts:
                metadata['authors'].append(' '.join(name_parts))

        # Genres
        for genre in title_info.findall('genre'):
            if genre.text:
                metadata['genres'].append(genre.text)

        # Language
        lang = title_info.find('lang')
        if lang is not None:
            metadata['lang'] = lang.text

        # Annotation
        annotation = title_info.find('annotation')
        if annotation is not None:
            paragraphs = []
            for p in annotation.findall('.//p'):
                if p.text:
                    paragraphs.append(p.text)
                # Also get tail text and nested elements
                text = ''.join(p.itertext())
                if text and text not in paragraphs:
                    paragraphs.append(text)
            # Deduplicate while preserving order
            seen = set()
            unique_paragraphs = []
            for p in paragraphs:
                if p not in seen:
                    seen.add(p)
                    unique_paragraphs.append(p)
            metadata['annotation'] = '\n'.join(unique_paragraphs)

        # Cover reference
        coverpage = title_info.find('coverpage')
        if coverpage is not None:
            image = coverpage.find('image')
            if image is not None:
                href = image.get('href', '')
                if href.startswith('#'):
                    href = href[1:]
                metadata['_cover_id'] = href

    # Year from publish-info
    publish_info = root.find('.//publish-info')
    if publish_info is not None:
        year = publish_info.find('year')
        if year is not None:
            metadata['year'] = year.text

    # Extract cover image if covers_dir is provided
    if covers_dir and metadata.get('_cover_id'):
        cover_id = metadata['_cover_id']
        for binary in root.findall('.//binary'):
            bin_id = binary.get('id', '')
            if bin_id == cover_id:
                content_type = binary.get('content-type', 'image/jpeg')
                ext = 'jpg' if 'jpeg' in content_type else content_type.split('/')[-1]

                try:
                    image_data = base64.b64decode(binary.text or '')
                    if image_data:
                        # Use hash for filename to avoid duplicates
                        img_hash = hashlib.md5(image_data).hexdigest()[:12]
                        cover_filename = f"{img_hash}.{ext}"
                        cover_path = os.path.join(covers_dir, cover_filename)

                        if not os.path.exists(cover_path):
                            os.makedirs(covers_dir, exist_ok=True)
                            with open(cover_path, 'wb') as f:
                                f.write(image_data)

                        metadata['cover'] = cover_filename
                except Exception:
                    pass
                break

    # Clean up internal fields
    metadata.pop('_cover_id', None)

    return metadata


if __name__ == '__main__':
    # Test with a sample file
    import sys
    if len(sys.argv) > 1:
        result = parse_fb2(sys.argv[1], covers_dir='static/covers')
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
