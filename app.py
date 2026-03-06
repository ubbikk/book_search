"""BookSearch — AI Shopping Assistant for Bookstores."""

import json
import os
import re
import smtplib
import threading
import uuid
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import duckdb
import faiss
import numpy as np
from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import litellm

load_dotenv()

os.environ["GEMINI_API_KEY"] = os.environ.get("GOOGLE_API_KEY", "")

# --- Firestore service (lazy-loaded) ---

_firestore_service = None


def get_firestore_service():
    """Get or create the Firestore service."""
    global _firestore_service
    if _firestore_service is None:
        from services.firestore import get_firestore
        _firestore_service = get_firestore()
    return _firestore_service


# --- Email notification ---


def send_access_request_notification(user_email: str, user_name: str = None):
    """Send email notification when a user requests access."""
    print(f"[Email] Starting notification for {user_email}", flush=True)

    smtp_email = os.getenv('SMTP_EMAIL')
    smtp_password = os.getenv('SMTP_PASSWORD')
    notify_email = os.getenv('NOTIFY_EMAIL', 'dd.petrovskiy@gmail.com')

    if not smtp_email or not smtp_password:
        print(f"[Email] SMTP not configured (SMTP_EMAIL={bool(smtp_email)}, SMTP_PASSWORD={bool(smtp_password)})", flush=True)
        return False

    print(f"[Email] Sending to {notify_email} via {smtp_email}", flush=True)

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'BookSearch Access Request: {user_email}'
        msg['From'] = smtp_email
        msg['To'] = notify_email

        display_name = user_name or user_email.split('@')[0]

        text_content = f"""New BookSearch Access Request

User: {display_name}
Email: {user_email}
"""

        html_content = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #ffffff; padding: 40px;">
    <div style="max-width: 500px; margin: 0 auto; background: #1a1a24; border-radius: 16px; padding: 32px; border: 1px solid rgba(255,255,255,0.1);">
        <h1 style="color: #d4a574; margin: 0 0 24px 0; font-size: 24px;">New Access Request</h1>
        <p style="color: #a8a8b3; margin: 0 0 16px 0;">A user has requested access to BookSearch:</p>
        <div style="background: #0a0a0f; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
            <p style="margin: 0 0 8px 0;"><strong style="color: #d4a574;">User:</strong> {display_name}</p>
            <p style="margin: 0;"><strong style="color: #d4a574;">Email:</strong> {user_email}</p>
        </div>
    </div>
</body>
</html>
"""

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        print("[Email] Connecting to smtp.gmail.com:587...", flush=True)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            print("[Email] TLS started, logging in...", flush=True)
            server.login(smtp_email, smtp_password)
            print("[Email] Logged in, sending message...", flush=True)
            server.send_message(msg)

        print(f"[Email] SUCCESS - Notification sent to {notify_email}", flush=True)
        return True

    except Exception as e:
        print(f"[Email] FAILED - {type(e).__name__}: {e}", flush=True)
        return False


# --- FirestoreUser (Flask-Login compatible) ---


class FirestoreUser:
    """User class compatible with Flask-Login, backed by Firestore."""

    def __init__(self, user_data: dict):
        self.id = user_data.get('id')
        self.firebase_uid = user_data.get('firebase_uid')
        self.email = user_data.get('email')
        self.display_name = user_data.get('display_name')
        self.photo_url = user_data.get('photo_url')
        self.auth_provider = user_data.get('auth_provider')
        self.is_admin = user_data.get('is_admin', False)
        self._approved = user_data.get('approved', False)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def name(self):
        return self.display_name or self.email or 'User'

    @property
    def is_approved(self):
        return self._approved

    @staticmethod
    def get_by_id(user_id: str):
        """Load user by ID from Firestore."""
        firestore = get_firestore_service()
        if not firestore:
            return None
        user_data = firestore.get_user_by_id(user_id)
        if user_data:
            return FirestoreUser(user_data)
        return None

    @staticmethod
    def get_or_create_from_firebase(decoded_token: dict):
        """Get existing user or create from Firebase token."""
        from services.firebase_auth import get_provider_from_token

        firestore = get_firestore_service()
        if not firestore:
            return None

        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        name = decoded_token.get('name')
        picture = decoded_token.get('picture')
        provider = get_provider_from_token(decoded_token)

        # Try to find by Firebase UID first
        user_data = firestore.get_user_by_firebase_uid(firebase_uid)
        if user_data:
            firestore.update_user_login(user_data['id'], picture)
            return FirestoreUser(user_data)

        # Try to find by email (for linking existing accounts)
        if email:
            existing = firestore.get_user_by_email(email)
            if existing:
                firestore.update_user_login(existing['id'], picture)
                return FirestoreUser(existing)

        # Create new user
        user_data = firestore.create_firebase_user(
            firebase_uid=firebase_uid,
            email=email,
            display_name=name,
            photo_url=picture,
            auth_provider=provider
        )
        return FirestoreUser(user_data)


# --- Flask App Setup ---

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "booksearch-dev-key")

# Session configuration
is_production = os.getenv('K_SERVICE') is not None or os.getenv('PRODUCTION') == 'true'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_SECURE'] = is_production
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = is_production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'landing'


@login_manager.user_loader
def load_user(user_id):
    return FirestoreUser.get_by_id(user_id)


@login_manager.unauthorized_handler
def unauthorized():
    """Return 401 JSON for API requests, redirect for pages."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Login required"}), 401
    return redirect(url_for('landing'))

# Configuration
BASE_DIR = Path(__file__).parent
INDEX_PATH = BASE_DIR / "data" / "index.json"
EMBEDDINGS_PATH = BASE_DIR / "data" / "embeddings.npy"
PROMO_DIR = BASE_DIR / "data" / "promo"
GCS_PROMO_URL = "https://storage.googleapis.com/booksearch-assets/promo/booksearch_promo.mp4"
EMBEDDING_MODEL = "gemini/gemini-embedding-001"
CHAT_MODEL = "gemini/gemini-2.0-flash"

# Fiction dataset paths
FICTION_DB_PATH = BASE_DIR / "data" / "fiction.duckdb"
FICTION_EMBEDDINGS_PATH = BASE_DIR / "data" / "fiction_embeddings.npy"
FICTION_ASIN_ORDER_PATH = BASE_DIR / "data" / "fiction_asin_order.npy"
FICTION_FAISS_PATH = BASE_DIR / "data" / "fiction_hnsw.faiss"

# Hybrid search parameter: 1.0 = pure semantic, 0.0 = pure popularity
HYBRID_ALPHA = 0.7

# Legacy data (for /search route)
BOOKS = []
EMBEDDINGS = None

# Fiction data (for AI assistant)
FICTION_BOOKS = {}  # parent_asin -> book dict
FICTION_ASINS = None  # numpy array mapping FAISS index -> parent_asin
FICTION_FAISS_INDEX = None  # FAISS HNSW index
FICTION_POPULARITY = None  # numpy array of normalized popularity scores (same order as FAISS)

CHAT_SESSIONS = {}

# Usage-based access control
DAILY_AI_LIMIT = 10
_daily_ai_counter = {"date": None, "count": 0}

# --- Chat Prompts (loaded from prompts/ directory) ---

PROMPTS_DIR = BASE_DIR / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "system.md").read_text()
FILTER_PROMPT = (PROMPTS_DIR / "filter.md").read_text()


def load_index():
    """Load book index and embeddings at startup."""
    global BOOKS, EMBEDDINGS
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            BOOKS = json.load(f)
        print(f"Loaded {len(BOOKS)} legacy books")

    if EMBEDDINGS_PATH.exists():
        EMBEDDINGS = np.load(EMBEDDINGS_PATH)
        print(f"Loaded legacy embeddings: {EMBEDDINGS.shape}")

    _load_fiction_data()


def _load_fiction_data():
    """Load fiction dataset: DuckDB metadata, FAISS index, popularity scores."""
    global FICTION_BOOKS, FICTION_ASINS, FICTION_FAISS_INDEX, FICTION_POPULARITY

    if not FICTION_DB_PATH.exists():
        print("Fiction database not found. Skipping fiction data.")
        return

    # Load book metadata from DuckDB
    conn = duckdb.connect(str(FICTION_DB_PATH), read_only=True)
    rows = conn.execute("""
        SELECT parent_asin, title, author_name, main_category, categories,
               average_rating, rating_number, price, description, images
        FROM books
    """).fetchall()
    conn.close()

    FICTION_BOOKS = {}
    for row in rows:
        asin = row[0]
        # Parse images to get cover URL
        images = row[9]
        cover_url = None
        if images:
            # images is a list of dicts: [{"large": "...", "hi_res": "...", "thumb": "..."}, ...]
            img_list = images
            if isinstance(images, str):
                try:
                    img_list = json.loads(images)
                except (json.JSONDecodeError, ValueError):
                    img_list = []
            if isinstance(img_list, list) and img_list:
                main_img = img_list[0] if isinstance(img_list[0], dict) else {}
                cover_url = main_img.get("hi_res") or main_img.get("large")

        # Parse description
        description = row[8]
        if isinstance(description, list):
            description = " ".join(description)
        elif isinstance(description, str):
            try:
                desc_list = json.loads(description)
                if isinstance(desc_list, list):
                    description = " ".join(desc_list)
            except (json.JSONDecodeError, ValueError):
                pass

        # Parse categories
        categories = row[4]
        if isinstance(categories, str):
            try:
                categories = json.loads(categories)
            except (json.JSONDecodeError, ValueError):
                categories = [categories]
        if not isinstance(categories, list):
            categories = []

        FICTION_BOOKS[asin] = {
            "title": row[1],
            "authors": [row[2]] if row[2] else [],
            "genres": categories,
            "average_rating": row[5],
            "rating_number": row[6],
            "price": row[7],
            "annotation": (description or "")[:500],
            "cover": cover_url,
        }

    print(f"Loaded {len(FICTION_BOOKS)} fiction books from DuckDB")

    # Load FAISS index
    if FICTION_FAISS_PATH.exists():
        FICTION_FAISS_INDEX = faiss.read_index(str(FICTION_FAISS_PATH))
        print(f"Loaded FAISS HNSW index: {FICTION_FAISS_INDEX.ntotal:,} vectors")
    else:
        print("FAISS index not found. Run 'python db/test_search.py --build-faiss'")

    # Load ASIN order (maps FAISS index position -> parent_asin)
    if FICTION_ASIN_ORDER_PATH.exists():
        FICTION_ASINS = np.load(FICTION_ASIN_ORDER_PATH)
        print(f"Loaded ASIN order: {len(FICTION_ASINS)} entries")

    # Pre-compute normalized popularity scores (log-scale, min-max normalized)
    if FICTION_ASINS is not None:
        ratings = np.array([
            FICTION_BOOKS.get(asin, {}).get("rating_number", 0)
            for asin in FICTION_ASINS
        ], dtype=np.float32)
        log_ratings = np.log1p(ratings)
        min_lr, max_lr = log_ratings.min(), log_ratings.max()
        if max_lr > min_lr:
            FICTION_POPULARITY = (log_ratings - min_lr) / (max_lr - min_lr)
        else:
            FICTION_POPULARITY = np.zeros_like(log_ratings)
        print(f"Pre-computed popularity scores for {len(FICTION_POPULARITY)} books")


# --- Routes ---


@app.route("/")
def landing():
    """Landing page."""
    # Check access request status for logged-in users
    access_request = None
    if current_user.is_authenticated and not current_user.is_approved:
        firestore = get_firestore_service()
        if firestore:
            access_request = firestore.get_user_access_request(current_user.id)

    promo_url = GCS_PROMO_URL if is_production else "/promo/booksearch_promo.mp4"

    return render_template(
        "landing.html",
        total_books=len(BOOKS),
        promo_video_url=promo_url,
        current_user=current_user,
        access_request=access_request,
        firebase_api_key=os.getenv('FIREBASE_API_KEY', ''),
        firebase_auth_domain=os.getenv('FIREBASE_AUTH_DOMAIN', ''),
        firebase_project_id=os.getenv('FIREBASE_PROJECT_ID', os.getenv('GOOGLE_CLOUD_PROJECT', '')),
    )


@app.route("/promo/<path:filename>")
def serve_promo(filename):
    """Serve promo video from data/promo directory."""
    return send_from_directory(PROMO_DIR, filename)


# --- Auth Routes ---


@app.route('/api/auth/firebase', methods=['POST'])
def api_firebase_auth():
    """Authenticate with Firebase ID token."""
    from services.firebase_auth import verify_firebase_token

    data = request.get_json()
    id_token = data.get('idToken')

    if not id_token:
        return jsonify({"error": "ID token required"}), 400

    decoded = verify_firebase_token(id_token)
    if not decoded:
        return jsonify({"error": "Invalid or expired token"}), 401

    user = FirestoreUser.get_or_create_from_firebase(decoded)
    if not user:
        return jsonify({"error": "Could not create user account"}), 500

    login_user(user, remember=True)

    return jsonify({
        "success": True,
        "redirect": url_for('landing'),
        "user": {
            "name": user.name,
            "email": user.email,
            "photo_url": user.photo_url
        }
    })


@app.route('/auth/callback')
def auth_callback():
    """Handle Firebase magic link callback."""
    return redirect(url_for('landing'))


@app.route('/logout')
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('landing'))


@app.route('/api/request-access', methods=['POST'])
@login_required
def api_request_access():
    """Submit an access request."""
    if current_user.is_approved:
        return jsonify({"error": "Already approved"}), 400

    firestore = get_firestore_service()
    if not firestore:
        return jsonify({"error": "Service unavailable"}), 503

    existing = firestore.get_user_access_request(current_user.id)
    if existing and existing.get('status') == 'pending':
        return jsonify({"error": "Request already pending"}), 400

    request_id = firestore.create_access_request(
        user_id=current_user.id,
        email=current_user.email,
    )

    # Send email notification (non-blocking)
    print(f"[AccessRequest] Spawning email notification thread for {current_user.email}", flush=True)
    threading.Thread(
        target=send_access_request_notification,
        args=(current_user.email, current_user.display_name),
        daemon=True
    ).start()

    return jsonify({
        "success": True,
        "request_id": request_id,
        "message": "Access request submitted. We'll review it shortly."
    })


# --- Search API ---


def search_books(query: str, limit: int = 50) -> list:
    """Lexical search: case-insensitive substring matching."""
    if not query:
        return BOOKS[:limit]

    query_lower = query.lower()
    results = []

    for book in BOOKS:
        title = (book.get("title") or "").lower()
        if query_lower in title:
            results.append(book)
            continue

        authors = " ".join(book.get("authors") or []).lower()
        if query_lower in authors:
            results.append(book)
            continue

        annotation = (book.get("annotation") or "").lower()
        if query_lower in annotation:
            results.append(book)
            continue

        if len(results) >= limit:
            break

    return results[:limit]


def semantic_search(query: str, limit: int = 50) -> list:
    """Semantic search using embeddings similarity."""
    if EMBEDDINGS is None:
        return []

    response = litellm.embedding(model=EMBEDDING_MODEL, input=[query])
    query_embedding = np.array(response.data[0]["embedding"], dtype=np.float32)

    norms = np.linalg.norm(EMBEDDINGS, axis=1) * np.linalg.norm(query_embedding)
    similarities = np.dot(EMBEDDINGS, query_embedding) / (norms + 1e-10)

    top_indices = np.argsort(similarities)[::-1][:limit]

    results = []
    for idx in top_indices:
        book = BOOKS[idx].copy()
        book["score"] = float(similarities[idx])
        results.append(book)

    return results


def fiction_search(query: str, limit: int = 100, alpha: float = HYBRID_ALPHA) -> list:
    """Semantic search on fiction dataset using FAISS + popularity re-ranking.

    Args:
        query: Search query text
        limit: Number of results to return
        alpha: Hybrid weight (1.0=pure semantic, 0.0=pure popularity)

    Returns:
        List of book dicts with score and hybrid_score
    """
    if FICTION_FAISS_INDEX is None or FICTION_ASINS is None:
        return []

    # Embed query
    response = litellm.embedding(model=EMBEDDING_MODEL, input=[query])
    query_vec = np.array(response.data[0]["embedding"], dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(query_vec)

    # FAISS search: retrieve more candidates for re-ranking
    n_candidates = min(limit * 3, FICTION_FAISS_INDEX.ntotal)
    FICTION_FAISS_INDEX.hnsw.efSearch = 256
    distances, indices = FICTION_FAISS_INDEX.search(query_vec, n_candidates)

    # Re-rank with hybrid score
    results = []
    for i, (idx, sim_score) in enumerate(zip(indices[0], distances[0])):
        if idx < 0:
            continue
        asin = FICTION_ASINS[idx]
        book = FICTION_BOOKS.get(asin)
        if not book:
            continue

        # Normalize similarity to [0, 1] (inner product after L2 norm is already in [-1, 1])
        norm_sim = (sim_score + 1) / 2

        pop_score = FICTION_POPULARITY[idx] if FICTION_POPULARITY is not None else 0
        hybrid_score = alpha * norm_sim + (1 - alpha) * pop_score

        book_result = book.copy()
        book_result["score"] = float(sim_score)
        book_result["hybrid_score"] = float(hybrid_score)
        book_result["parent_asin"] = str(asin)
        results.append(book_result)

    # Sort by hybrid score
    results.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return results[:limit]


@app.route("/search")
def search():
    """Search endpoint with mode selection."""
    query = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 50)), 200)
    mode = request.args.get("mode", "lexical")

    if mode == "semantic" and EMBEDDINGS is not None and query:
        results = semantic_search(query, limit)
    else:
        results = search_books(query, limit)

    return jsonify(
        {
            "query": query,
            "mode": mode,
            "count": len(results),
            "total": len(BOOKS),
            "has_embeddings": EMBEDDINGS is not None,
            "books": results,
        }
    )


# --- Store & Chat API ---


@app.route("/store")
def store():
    """Bookstore page with browse grid and AI chat widget."""
    if "chat_id" not in session:
        session["chat_id"] = str(uuid.uuid4())
    total = len(FICTION_BOOKS) if FICTION_BOOKS else len(BOOKS)
    return render_template("store.html", total_books=total)


@app.route("/api/books")
def api_books():
    """Paginated book list for the browse grid."""
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 24)), 48)
    start = (page - 1) * per_page
    end = start + per_page

    slim_books = [
        {
            "title": b.get("title", ""),
            "authors": b.get("authors", []),
            "cover": b.get("cover"),
            "year": b.get("year"),
        }
        for b in BOOKS[start:end]
    ]

    return jsonify(
        {
            "books": slim_books,
            "page": page,
            "per_page": per_page,
            "total": len(BOOKS),
            "has_more": end < len(BOOKS),
        }
    )


def _check_daily_limit():
    """Check if the daily AI request limit has been reached. Returns True if OK."""
    from datetime import date, timezone
    today = date.today()
    if _daily_ai_counter["date"] != today:
        _daily_ai_counter["date"] = today
        _daily_ai_counter["count"] = 0
    return _daily_ai_counter["count"] < DAILY_AI_LIMIT


def _increment_daily_counter():
    """Increment the daily AI request counter."""
    _daily_ai_counter["count"] += 1


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle chat messages from the AI assistant widget."""
    data = request.get_json()
    user_message = (data.get("message") or "").strip()
    session_id = data.get("session_id") or session.get("chat_id", str(uuid.uuid4()))

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Check daily limit
    if not _check_daily_limit():
        return jsonify({
            "reply": "We've reached our daily limit for AI-powered recommendations. "
                     "Please try again tomorrow, or request access for unlimited use.",
            "type": "limit_reached",
            "session_id": session_id,
        })

    # Initialize session if new — seed with the greeting shown in the UI
    if session_id not in CHAT_SESSIONS:
        CHAT_SESSIONS[session_id] = {
            "messages": [
                {"role": "assistant", "content": "Welcome! I'm your book assistant. "
                 "Looking for something to read? Tell me \u2014 what was the last book you really enjoyed?"}
            ],
            "state": "discovery",
        }

    chat = CHAT_SESSIONS[session_id]
    chat["messages"].append({"role": "user", "content": user_message})

    _increment_daily_counter()

    # Build messages for LLM
    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat["messages"]

    try:
        response = litellm.completion(
            model=CHAT_MODEL,
            messages=llm_messages,
            temperature=0.7,
            max_tokens=500,
        )
        assistant_reply = response.choices[0].message.content
    except Exception as e:
        print(f"Chat LLM error: {e}")
        return jsonify(
            {
                "reply": "I'm having trouble thinking right now. Please try again.",
                "type": "message",
                "session_id": session_id,
            }
        )

    chat["messages"].append({"role": "assistant", "content": assistant_reply})

    # Check if assistant is ready to search
    if "[READY_TO_SEARCH]" in assistant_reply:
        return _handle_search_pipeline(chat, session_id, assistant_reply)

    return jsonify(
        {"reply": assistant_reply, "type": "message", "session_id": session_id}
    )


def _handle_search_pipeline(chat, session_id, assistant_reply):
    """Execute the two-layer search pipeline and return recommendations."""
    chat["state"] = "searching"

    # Extract search params from the assistant's message
    search_match = re.search(
        r"```search\s*\n({.*?})\s*\n```", assistant_reply, re.DOTALL
    )
    if search_match:
        try:
            search_params = json.loads(search_match.group(1))
            query = search_params.get("query", "")
            preferences = search_params.get("preferences", "")
        except json.JSONDecodeError:
            query = ""
            preferences = ""
    else:
        query = ""
        preferences = ""

    # Fallback: synthesize query from user messages
    if not query:
        query = " ".join(
            m["content"] for m in chat["messages"] if m["role"] == "user"
        )

    # Layer 1: Hybrid search (semantic + popularity) — top 100 candidates
    candidates = fiction_search(query, limit=100)
    if not candidates:
        # Fallback to legacy search
        candidates = semantic_search(query, limit=20)
    if not candidates:
        candidates = search_books(query, limit=20)

    # Build candidates text for the filter LLM
    candidates_text = ""
    for i, book in enumerate(candidates):
        title = book.get("title", "Unknown")
        authors = ", ".join(book.get("authors", []))
        annotation = (book.get("annotation") or "")[:300]
        genres = ", ".join(book.get("genres", []))
        rating_num = book.get("rating_number", 0)
        avg_rating = book.get("average_rating", 0)
        candidates_text += (
            f"\n[{i}] Title: {title}\nAuthors: {authors}"
            f"\nGenres: {genres}\nRating: {avg_rating:.1f}/5 ({rating_num:,} ratings)"
            f"\nDescription: {annotation}\n"
        )

    # Build conversation summary
    conversation_summary = "\n".join(
        f"{'Customer' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in chat["messages"][:-1]
        if m["role"] in ("user", "assistant")
    )

    # Layer 2: AI filtering with Gemini
    filter_prompt = FILTER_PROMPT.format(
        conversation_summary=conversation_summary,
        preferences=preferences or query,
        candidates_text=candidates_text,
    )

    selected_books = []
    try:
        filter_response = litellm.completion(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": filter_prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        filter_text = filter_response.choices[0].message.content

        # Parse the filter response
        json_match = re.search(
            r"```json\s*\n(\[.*?\])\s*\n```", filter_text, re.DOTALL
        )
        if not json_match:
            json_match = re.search(r"(\[.*\])", filter_text, re.DOTALL)

        if json_match:
            picks = json.loads(json_match.group(1))
            for pick in picks[:3]:
                idx = pick["index"]
                if 0 <= idx < len(candidates):
                    book = candidates[idx].copy()
                    book["explanation"] = pick.get("explanation", "")
                    selected_books.append(book)
    except Exception as e:
        print(f"Filter LLM error: {e}")

    # Fallback: top 3 semantic results
    if len(selected_books) < 3:
        for book in candidates:
            if book not in selected_books:
                book_copy = book.copy()
                book_copy["explanation"] = (
                    "A top match from our catalog based on your interests."
                )
                selected_books.append(book_copy)
                if len(selected_books) >= 3:
                    break

    chat["state"] = "done"

    # Clean the assistant reply (remove marker and search block)
    clean_reply = assistant_reply.split("[READY_TO_SEARCH]")[0].strip()
    clean_reply = re.sub(r"```search.*?```", "", clean_reply, flags=re.DOTALL).strip()
    chat["messages"][-1]["content"] = clean_reply

    return jsonify(
        {
            "reply": clean_reply,
            "type": "recommendations",
            "books": [
                {
                    "title": b.get("title", ""),
                    "authors": b.get("authors", []),
                    "cover": b.get("cover"),
                    "annotation": (b.get("annotation") or "")[:200],
                    "year": b.get("year"),
                    "genres": b.get("genres", []),
                    "explanation": b.get("explanation", ""),
                }
                for b in selected_books[:3]
            ],
            "session_id": session_id,
        }
    )


@app.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    """Reset the chat session."""
    data = request.get_json() or {}
    session_id = data.get("session_id") or session.get("chat_id")
    if session_id and session_id in CHAT_SESSIONS:
        del CHAT_SESSIONS[session_id]
    new_id = str(uuid.uuid4())
    session["chat_id"] = new_id
    return jsonify({"session_id": new_id})


if __name__ == "__main__":
    load_index()
    app.run(debug=True, host="0.0.0.0", port=5000)
