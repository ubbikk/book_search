#!/usr/bin/env python3
"""
Test search performance: brute-force cosine similarity vs FAISS index.

Usage:
    python db/test_search.py               # Run all tests
    python db/test_search.py --build-faiss  # Only build the FAISS index
"""

import argparse
import os
import time
from pathlib import Path

import duckdb
import numpy as np

DB_PATH = Path("data/fiction.duckdb")
EMBEDDINGS_PATH = Path("data/fiction_embeddings.npy")
ASIN_ORDER_PATH = Path("data/fiction_asin_order.npy")
FAISS_INDEX_PATH = Path("data/fiction.faiss")

# Test queries (will be embedded on the fly)
TEST_QUERIES = [
    "a dark mystery set in a small town with secrets",
    "romantic comedy with witty dialogue",
    "epic fantasy with dragons and magic",
    "psychological thriller about an unreliable narrator",
    "coming-of-age story about a young girl in the south",
]


def load_data():
    """Load embeddings, ASINs, and book metadata."""
    embeddings = np.load(EMBEDDINGS_PATH)
    asins = np.load(ASIN_ORDER_PATH)

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    # Build a lookup: parent_asin -> book info
    rows = conn.execute("""
        SELECT parent_asin, title, author_name, rating_number, average_rating
        FROM books
    """).fetchall()
    conn.close()

    books = {row[0]: {
        "title": row[1], "author": row[2],
        "ratings": row[3], "stars": row[4]
    } for row in rows}

    return embeddings, asins, books


def embed_query(text: str) -> np.ndarray:
    """Embed a single query using Gemini."""
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    import litellm
    litellm.suppress_debug_info = True
    from dotenv import load_dotenv
    load_dotenv()
    os.environ["GEMINI_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")

    response = litellm.embedding(
        model="gemini/gemini-embedding-001",
        input=[text],
    )
    return np.array(response.data[0]["embedding"], dtype=np.float32)


def cosine_search(query_vec: np.ndarray, embeddings: np.ndarray, k: int = 10):
    """Brute-force cosine similarity search."""
    # Normalize
    query_norm = query_vec / np.linalg.norm(query_vec)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / norms

    similarities = normed @ query_norm
    top_k = np.argsort(similarities)[::-1][:k]
    return top_k, similarities[top_k]


def build_faiss_index(embeddings: np.ndarray):
    """Build FAISS indexes: HNSW (best recall) and IVF-Flat (good balance)."""
    import faiss

    n, d = embeddings.shape
    print(f"Building FAISS indexes for {n:,} vectors of dim {d}...")

    # Normalize embeddings (for inner product = cosine similarity)
    faiss.normalize_L2(embeddings)

    indexes = {}

    # 1. HNSW — graph-based, excellent recall, no training needed
    print("\n--- HNSW (M=32) ---")
    t0 = time.time()
    hnsw = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
    hnsw.hnsw.efConstruction = 200
    hnsw.add(embeddings)
    build_time = time.time() - t0
    print(f"Built in {build_time:.1f}s ({hnsw.ntotal:,} vectors)")
    hnsw_path = FAISS_INDEX_PATH.with_name("fiction_hnsw.faiss")
    faiss.write_index(hnsw, str(hnsw_path))
    print(f"Saved to {hnsw_path} ({hnsw_path.stat().st_size / (1024*1024):.1f} MB)")
    indexes["hnsw"] = hnsw

    # 2. IVF-Flat — exact distances within searched cells
    print("\n--- IVF-Flat (nlist=256) ---")
    nlist = 256
    quantizer = faiss.IndexFlatIP(d)
    ivf = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
    t0 = time.time()
    ivf.train(embeddings)
    ivf.add(embeddings)
    build_time = time.time() - t0
    print(f"Built in {build_time:.1f}s ({ivf.ntotal:,} vectors)")
    ivf_path = FAISS_INDEX_PATH.with_name("fiction_ivf.faiss")
    faiss.write_index(ivf, str(ivf_path))
    print(f"Saved to {ivf_path} ({ivf_path.stat().st_size / (1024*1024):.1f} MB)")
    indexes["ivf"] = ivf

    return indexes


def faiss_search(query_vec: np.ndarray, index, k: int = 10, nprobe: int = 64, ef_search: int = 128):
    """Search using FAISS index."""
    import faiss
    query = query_vec.reshape(1, -1).copy()
    faiss.normalize_L2(query)
    # Set search params based on index type
    if hasattr(index, 'hnsw'):
        index.hnsw.efSearch = ef_search
    elif hasattr(index, 'nprobe'):
        index.nprobe = nprobe
    distances, indices = index.search(query, k)
    return indices[0], distances[0]


def print_results(label: str, indices, scores, asins, books, k: int = 5):
    """Print search results."""
    print(f"\n  {label}:")
    for i, (idx, score) in enumerate(zip(indices[:k], scores[:k]), 1):
        asin = asins[idx]
        book = books.get(asin, {})
        title = book.get("title", "?")[:55]
        author = book.get("author", "?")
        ratings = book.get("ratings", 0)
        print(f"    {i}. [{score:.4f}] {title}")
        print(f"       {author} | {ratings:,} ratings")


def test_recall(embeddings, index, asins, n_queries=200, k=10, nprobe=64, ef_search=128):
    """Measure recall@k of FAISS vs exact search."""
    import faiss

    rng = np.random.default_rng(42)
    query_indices = rng.choice(len(embeddings), n_queries, replace=False)

    normed = embeddings.copy()
    faiss.normalize_L2(normed)

    recalls = []
    for qi in query_indices:
        query = normed[qi].reshape(1, -1).copy()

        # Exact
        sims = normed @ query.T
        exact_top = set(np.argsort(sims.ravel())[::-1][1:k+1])

        # FAISS
        if hasattr(index, 'hnsw'):
            index.hnsw.efSearch = ef_search
        elif hasattr(index, 'nprobe'):
            index.nprobe = nprobe
        _, faiss_top = index.search(query, k + 1)
        faiss_set = set(faiss_top[0]) - {qi}
        faiss_set = set(list(faiss_set)[:k])

        recall = len(exact_top & faiss_set) / k
        recalls.append(recall)

    return np.mean(recalls)


def main(build_only: bool = False):
    import faiss

    print("Loading data...")
    embeddings, asins, books = load_data()
    n = len(embeddings)
    print(f"Loaded {n:,} embeddings of dim {embeddings.shape[1]}")

    # Build FAISS indexes
    emb_copy = embeddings.copy()
    indexes = build_faiss_index(emb_copy)

    if build_only:
        return

    # Recall tests
    print("\n" + "=" * 60)
    print("RECALL TEST (200 random queries, k=10)")
    print("=" * 60)

    emb_normed = embeddings.copy()
    faiss.normalize_L2(emb_normed)

    print("\n  HNSW:")
    for ef in [32, 64, 128, 256, 512]:
        recall = test_recall(emb_normed, indexes["hnsw"], asins, n_queries=200, k=10, ef_search=ef)
        print(f"    efSearch={ef:>3}: recall@10 = {recall:.3f}")

    print("\n  IVF-Flat:")
    for nprobe in [8, 16, 32, 64, 128]:
        recall = test_recall(emb_normed, indexes["ivf"], asins, n_queries=200, k=10, nprobe=nprobe)
        print(f"    nprobe={nprobe:>3}: recall@10 = {recall:.3f}")

    # Speed tests
    print("\n" + "=" * 60)
    print("SPEED TEST")
    print("=" * 60)

    query_vec = embeddings[0].copy()

    # Brute-force
    times_bf = []
    for _ in range(20):
        t0 = time.time()
        cosine_search(query_vec, embeddings, k=10)
        times_bf.append(time.time() - t0)
    avg_bf = np.mean(times_bf) * 1000
    print(f"\n  Brute-force cosine ({n:,} vectors): {avg_bf:.1f} ms/query")

    # HNSW speed
    print("\n  HNSW:")
    for ef in [32, 64, 128, 256]:
        times = []
        for _ in range(50):
            t0 = time.time()
            faiss_search(query_vec, indexes["hnsw"], k=10, ef_search=ef)
            times.append(time.time() - t0)
        avg = np.mean(times) * 1000
        print(f"    efSearch={ef:>3}: {avg:.2f} ms/query ({avg_bf/avg:.0f}x faster)")

    # IVF-Flat speed
    print("\n  IVF-Flat:")
    for nprobe in [8, 16, 32, 64]:
        times = []
        for _ in range(50):
            t0 = time.time()
            faiss_search(query_vec, indexes["ivf"], k=10, nprobe=nprobe)
            times.append(time.time() - t0)
        avg = np.mean(times) * 1000
        print(f"    nprobe={nprobe:>3}: {avg:.2f} ms/query ({avg_bf/avg:.0f}x faster)")

    # Live query test — use HNSW (best recall)
    best_index = indexes["hnsw"]
    print("\n" + "=" * 60)
    print("LIVE QUERY TEST (HNSW efSearch=256 vs brute-force)")
    print("=" * 60)

    for query_text in TEST_QUERIES:
        print(f"\n  Query: \"{query_text}\"")
        q_vec = embed_query(query_text)

        bf_idx, bf_scores = cosine_search(q_vec, embeddings, k=5)
        print_results("Brute-force top 5", bf_idx, bf_scores, asins, books, k=5)

        f_idx, f_scores = faiss_search(q_vec, best_index, k=5, ef_search=256)
        print_results("HNSW top 5 (efSearch=256)", f_idx, f_scores, asins, books, k=5)

        overlap = len(set(bf_idx[:5]) & set(f_idx[:5]))
        print(f"\n  Overlap: {overlap}/5 results match")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test search performance")
    parser.add_argument("--build-faiss", action="store_true",
                        help="Only build the FAISS index")
    args = parser.parse_args()
    main(build_only=args.build_faiss)
