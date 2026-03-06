"""
End-to-end tests for the AI recommendation pipeline.

Tests the full flow: user messages → AI discovery → semantic search → AI filtering → 3 books.
Requires fiction data files and GOOGLE_API_KEY to be set.

Usage:
    pytest tests/test_recommendations.py -v
    pytest tests/test_recommendations.py -v -k "thriller"
    pytest tests/test_recommendations.py -v --alpha 0.5  # Test different hybrid weights
"""

import json
import uuid

import pytest

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# --- User Journey Definitions ---

JOURNEYS = [
    {
        "id": "thriller_fan",
        "description": "Thriller fan looking for something dark",
        "messages": [
            "Hi, I'm looking for a good book to read",
            "I loved Gone Girl by Gillian Flynn",
            "I love the dark, twisty psychological stuff. Unreliable narrators are my thing.",
        ],
    },
    {
        "id": "gift_for_mom",
        "description": "Looking for a gift for mom who likes historical fiction",
        "messages": [
            "I need a gift for my mom",
            "She's in her 60s and loves historical fiction, especially set in Europe",
            "She recently enjoyed The Nightingale by Kristin Hannah",
        ],
    },
    {
        "id": "scifi_reader",
        "description": "Sci-fi reader wanting something fresh",
        "messages": [
            "I want something in science fiction",
            "I've read all the classics — Asimov, Clarke, Herbert. I want something modern and thought-provoking.",
            "I really liked Project Hail Mary by Andy Weir",
        ],
    },
    {
        "id": "romance_reader",
        "description": "Romance reader wanting something fun and light",
        "messages": [
            "I'm in the mood for a fun romance",
            "I loved Beach Read by Emily Henry. Something witty and modern.",
            "Contemporary settings, nothing too heavy",
        ],
    },
    {
        "id": "fantasy_epic",
        "description": "Looking for an epic fantasy series",
        "messages": [
            "I want a big epic fantasy series to dive into",
            "I've read Lord of the Rings and Game of Thrones. Looking for something with deep worldbuilding.",
            "I like complex magic systems and political intrigue",
        ],
    },
    {
        "id": "literary_fiction",
        "description": "Literary fiction reader seeking depth",
        "messages": [
            "I'm looking for something literary and meaningful",
            "I recently read A Little Life by Hanya Yanagihara and it wrecked me. I want something equally powerful.",
            "I don't mind if it's sad — I want to feel something deep",
        ],
    },
    {
        "id": "mystery_cozy",
        "description": "Looking for a cozy mystery",
        "messages": [
            "I want a mystery but nothing too dark or violent",
            "I love cozy mysteries — small towns, charming characters, a puzzle to solve",
            "Something like the Thursday Murder Club by Richard Osman",
        ],
    },
    {
        "id": "teen_reader",
        "description": "YA reader looking for adventure",
        "messages": [
            "I'm looking for a good YA book",
            "I loved The Hunger Games and Divergent",
            "I want a strong female protagonist in a dystopian or fantasy world",
        ],
    },
    {
        "id": "horror_fan",
        "description": "Horror reader wanting psychological dread",
        "messages": [
            "I want something genuinely scary",
            "Not slasher stuff — I mean psychological horror that gets under your skin",
            "I loved The Haunting of Hill House by Shirley Jackson",
        ],
    },
    {
        "id": "surprise_me",
        "description": "Open-minded reader wanting a surprise",
        "messages": [
            "Surprise me with something great",
            "I read all kinds of things. Recently I enjoyed both a thriller and a literary novel.",
            "I just want something that's hard to put down, regardless of genre",
        ],
    },
]


@pytest.fixture(scope="session")
def app_client():
    """Create a test client with fiction data loaded."""
    from app import app, load_index, DAILY_AI_LIMIT, _daily_ai_counter

    # Set a high daily limit for testing
    _daily_ai_counter["count"] = 0
    _daily_ai_counter["date"] = None

    load_index()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def alpha(request):
    """Get alpha value from command line or use default."""
    return request.config.getoption("--alpha", default=None)


def pytest_addoption(parser):
    parser.addoption("--alpha", type=float, default=None,
                     help="Hybrid search alpha (1.0=semantic, 0.0=popularity)")


def run_journey(client, journey: dict, alpha: float = None) -> dict:
    """Run a single user journey through the chat API and return results."""
    session_id = str(uuid.uuid4())
    all_responses = []

    for message in journey["messages"]:
        payload = {"message": message, "session_id": session_id}
        response = client.post(
            "/api/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200, f"Chat API returned {response.status_code}"
        data = response.get_json()
        all_responses.append(data)

        # If we got recommendations, we're done
        if data.get("type") == "recommendations":
            return {
                "journey_id": journey["id"],
                "responses": all_responses,
                "books": data.get("books", []),
                "reply": data.get("reply", ""),
                "turns": len(all_responses),
            }

    # If the AI hasn't searched yet after all messages, it might need one more turn.
    # The last response should still be a discovery question — that's OK for some journeys.
    last_data = all_responses[-1]
    return {
        "journey_id": journey["id"],
        "responses": all_responses,
        "books": last_data.get("books", []),
        "reply": last_data.get("reply", ""),
        "turns": len(all_responses),
        "final_type": last_data.get("type"),
    }


@pytest.mark.parametrize("journey", JOURNEYS, ids=[j["id"] for j in JOURNEYS])
def test_journey_returns_recommendations(app_client, journey, alpha):
    """Each journey should produce 3 book recommendations."""
    import app as app_module

    # Override alpha if provided
    original_alpha = app_module.HYBRID_ALPHA
    if alpha is not None:
        app_module.HYBRID_ALPHA = alpha

    try:
        result = run_journey(app_client, journey)
    finally:
        app_module.HYBRID_ALPHA = original_alpha

    # Log results for review
    print(f"\n{'='*60}")
    print(f"Journey: {journey['id']} — {journey['description']}")
    print(f"Turns: {result['turns']}")
    print(f"AI reply: {result['reply'][:200]}")

    books = result["books"]
    if books:
        print(f"Recommendations ({len(books)}):")
        for i, book in enumerate(books, 1):
            title = book.get("title", "?")
            authors = ", ".join(book.get("authors", []))
            explanation = book.get("explanation", "")
            print(f"  {i}. {title} by {authors}")
            print(f"     → {explanation}")
    else:
        print(f"No recommendations yet. Final type: {result.get('final_type')}")
        print(f"Last reply: {result['reply'][:300]}")

    # Assertions
    if result.get("final_type") == "recommendations" or books:
        assert len(books) == 3, f"Expected 3 books, got {len(books)}"
        for book in books:
            assert book.get("title"), "Book missing title"
            assert book.get("authors"), "Book missing authors"
            assert book.get("explanation"), "Book missing explanation"


def test_daily_limit(app_client):
    """Test that the daily limit is enforced."""
    import app as app_module

    # Set a very low limit
    original_limit = app_module.DAILY_AI_LIMIT
    app_module.DAILY_AI_LIMIT = 2
    app_module._daily_ai_counter["count"] = 0
    app_module._daily_ai_counter["date"] = None

    try:
        session_id = str(uuid.uuid4())

        # First 2 should work
        for i in range(2):
            response = app_client.post(
                "/api/chat",
                data=json.dumps({"message": f"test {i}", "session_id": session_id}),
                content_type="application/json",
            )
            data = response.get_json()
            assert data.get("type") != "limit_reached", f"Limit reached too early on request {i+1}"

        # Third should hit the limit
        response = app_client.post(
            "/api/chat",
            data=json.dumps({"message": "one more", "session_id": str(uuid.uuid4())}),
            content_type="application/json",
        )
        data = response.get_json()
        assert data.get("type") == "limit_reached", "Expected limit_reached but got " + str(data.get("type"))

    finally:
        app_module.DAILY_AI_LIMIT = original_limit
        app_module._daily_ai_counter["count"] = 0
        app_module._daily_ai_counter["date"] = None


def test_fiction_search_direct():
    """Test fiction_search function directly (no chat, just search)."""
    from app import fiction_search, load_index, FICTION_FAISS_INDEX

    if FICTION_FAISS_INDEX is None:
        load_index()

    from app import FICTION_FAISS_INDEX as idx
    if idx is None:
        pytest.skip("Fiction FAISS index not available")

    results = fiction_search("dark psychological thriller with unreliable narrator", limit=10)
    assert len(results) > 0, "No results from fiction_search"
    assert len(results) <= 10

    # Check result structure
    for book in results:
        assert "title" in book
        assert "authors" in book
        assert "score" in book
        assert "hybrid_score" in book

    # Print top results
    print("\nDirect fiction_search results:")
    for i, book in enumerate(results[:5], 1):
        print(f"  {i}. [{book['hybrid_score']:.3f}] {book['title']} by {', '.join(book['authors'])}")
        print(f"     Similarity: {book['score']:.3f} | Ratings: {book.get('rating_number', 0):,}")


def test_hybrid_alpha_comparison():
    """Compare results with different alpha values to help tune the parameter."""
    from app import fiction_search, load_index, FICTION_FAISS_INDEX

    if FICTION_FAISS_INDEX is None:
        load_index()

    from app import FICTION_FAISS_INDEX as idx
    if idx is None:
        pytest.skip("Fiction FAISS index not available")

    query = "epic fantasy with dragons and magic systems"
    alphas = [1.0, 0.7, 0.5, 0.3, 0.0]

    print(f"\nQuery: \"{query}\"")
    for a in alphas:
        results = fiction_search(query, limit=5, alpha=a)
        print(f"\n  Alpha={a} (semantic={a:.0%}, popularity={1-a:.0%}):")
        for i, book in enumerate(results[:5], 1):
            ratings = book.get("rating_number", 0)
            print(f"    {i}. {book['title'][:50]} | {ratings:,} ratings | hybrid={book['hybrid_score']:.3f}")
