"""Generate embeddings for book search using litellm."""

import json
import os
import numpy as np
from dotenv import load_dotenv

# Disable tiktoken to avoid network dependency
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import litellm
litellm.suppress_debug_info = True

load_dotenv()

INDEX_PATH = os.path.join(os.path.dirname(__file__), 'data', 'index.json')
EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'embeddings.npy')
EMBEDDING_MODEL = "gemini/gemini-embedding-001"

# Set API key for litellm
os.environ["GEMINI_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")


def create_book_text(book: dict) -> str:
    """Create searchable text from book metadata."""
    parts = []
    if book.get('title'):
        parts.append(f"Title: {book['title']}")
    if book.get('authors'):
        parts.append(f"Authors: {', '.join(book['authors'])}")
    if book.get('genres'):
        parts.append(f"Genres: {', '.join(book['genres'][:5])}")
    if book.get('annotation'):
        annotation = book['annotation'][:500]
        parts.append(f"Description: {annotation}")
    return '\n'.join(parts)


def get_embeddings(texts: list[str], batch_size: int = 100) -> np.ndarray:
    """Get embeddings for a list of texts using litellm."""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"Processing batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")

        response = litellm.embedding(
            model=EMBEDDING_MODEL,
            input=batch
        )
        batch_embeddings = [item["embedding"] for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return np.array(all_embeddings, dtype=np.float32)


def build_embeddings():
    """Build embeddings for all books."""
    print("Loading book index...")
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        books = json.load(f)

    print(f"Creating text representations for {len(books)} books...")
    texts = [create_book_text(book) for book in books]

    print("Generating embeddings...")
    embeddings = get_embeddings(texts)

    print(f"Saving embeddings to {EMBEDDINGS_PATH}...")
    np.save(EMBEDDINGS_PATH, embeddings)

    print(f"Done! Shape: {embeddings.shape}")
    return embeddings


if __name__ == '__main__':
    build_embeddings()
