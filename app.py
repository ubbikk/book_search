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
EMBEDDING_MODEL = "gemini/text-embedding-004"
CHAT_MODEL = "gemini/gemini-2.0-flash"

BOOKS = []
EMBEDDINGS = None
CHAT_SESSIONS = {}

# --- Chat Prompts ---

SYSTEM_PROMPT = """\
You are a friendly and knowledgeable bookstore assistant for a Russian-language bookstore. \
You help customers discover books they'll love through brief, warm conversation.

Your catalog contains ~1,500 Russian books across fiction, sci-fi, romance, detective, history, and more.

CONVERSATION RULES:
1. Greet the customer warmly and ask ONE discovery question to start.
2. Ask at most 2-3 questions total before making recommendations. Don't interrogate.
3. Good discovery questions (pick the most relevant, don't ask all):
   - "What was the last book you really enjoyed?"
   - "Is this for yourself or a gift?"
   - "What kind of mood are you in — something light and fun, or deep and thought-provoking?"
   - "Are there any genres you particularly love or want to avoid?"
   - "Any favorite authors?"
4. Listen actively — reflect back what you hear before asking the next question.
5. When you have enough context (usually after 2-3 exchanges), say you're ready to search.
6. Speak in English. The books are in Russian, but you communicate in English.
7. Be concise — 2-3 sentences per reply max.
8. Never invent book titles or authors. You will receive real search results to recommend from.

When you decide you have enough information to recommend books, your FINAL message before search \
must end with the exact marker: [READY_TO_SEARCH]

Along with the marker, include a JSON block with your synthesized search understanding:
```search
{"query": "a concise semantic search query based on the conversation", "preferences": "brief summary of user preferences"}
```"""

FILTER_PROMPT = """\
You are a bookstore assistant. Based on the conversation with the customer, \
select exactly 3 books from the candidates below that best match what they're looking for.

CONVERSATION CONTEXT:
{conversation_summary}

CUSTOMER PREFERENCES:
{preferences}

CANDIDATE BOOKS (top semantic matches from our catalog):
{candidates_text}

For each of your 3 picks, provide a brief personalized explanation (1-2 sentences) of why this \
book is perfect for THIS customer based on what they told you. Write in English.

Respond in this exact JSON format:
```json
[
  {{"index": 0, "explanation": "..."}},
  {{"index": 1, "explanation": "..."}},
  {{"index": 2, "explanation": "..."}}
]
```
Where "index" is the candidate number (0-based) from the list above."""


def load_index():
    """Load book index and embeddings at startup."""
    global BOOKS, EMBEDDINGS
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        BOOKS = json.load(f)
    print(f"Loaded {len(BOOKS)} books")

    if EMBEDDINGS_PATH.exists():
        EMBEDDINGS = np.load(EMBEDDINGS_PATH)
        print(f"Loaded embeddings: {EMBEDDINGS.shape}")
    else:
        print("No embeddings file found. Run 'python embeddings.py' to generate.")


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
    return render_template("store.html", total_books=len(BOOKS))


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


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle chat messages from the AI assistant widget."""
    data = request.get_json()
    user_message = (data.get("message") or "").strip()
    session_id = data.get("session_id") or session.get("chat_id", str(uuid.uuid4()))

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Initialize session if new
    if session_id not in CHAT_SESSIONS:
        CHAT_SESSIONS[session_id] = {"messages": [], "state": "discovery"}

    chat = CHAT_SESSIONS[session_id]
    chat["messages"].append({"role": "user", "content": user_message})

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

    # Layer 1: Semantic search — top 20 candidates
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
        candidates_text += (
            f"\n[{i}] Title: {title}\nAuthors: {authors}"
            f"\nGenres: {genres}\nDescription: {annotation}\n"
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
