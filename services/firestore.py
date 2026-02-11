"""
Firestore service for user and access request persistence.

Collections:
- users: Firebase-authenticated user profiles
- access_requests: Pending/approved/rejected access requests
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

USERS_COLLECTION = 'booksearch_users'
ACCESS_REQUESTS_COLLECTION = 'booksearch_access_requests'


class FirestoreService:
    """Firestore operations for user and access request persistence."""

    def __init__(self):
        """Initialize Firestore client."""
        project = os.getenv('GOOGLE_CLOUD_PROJECT')
        if project:
            self.db = firestore.Client(project=project)
        else:
            self.db = firestore.Client()
        self.users = self.db.collection(USERS_COLLECTION)

    # ==================== User Operations ====================

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by document ID."""
        doc = self.users.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[Dict[str, Any]]:
        """Get a user by Firebase UID."""
        docs = self.users.where('firebase_uid', '==', firebase_uid).limit(1).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email address."""
        docs = self.users.where('email', '==', email.lower()).limit(1).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def create_firebase_user(
        self,
        firebase_uid: str,
        email: str,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        auth_provider: str = 'unknown'
    ) -> Dict[str, Any]:
        """Create a new user from Firebase authentication."""
        doc_ref = self.users.document()
        user_data = {
            'firebase_uid': firebase_uid,
            'email': email.lower(),
            'display_name': display_name or email.split('@')[0],
            'photo_url': photo_url,
            'auth_provider': auth_provider,
            'is_admin': False,
            'approved': False,
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login_at': firestore.SERVER_TIMESTAMP,
        }
        doc_ref.set(user_data)

        user_data['id'] = doc_ref.id
        return user_data

    def update_user_login(self, user_id: str, photo_url: Optional[str] = None) -> bool:
        """Update last login timestamp and optionally photo URL."""
        doc_ref = self.users.document(user_id)
        if not doc_ref.get().exists:
            return False

        update_data = {'last_login_at': firestore.SERVER_TIMESTAMP}
        if photo_url:
            update_data['photo_url'] = photo_url
        doc_ref.update(update_data)
        return True

    # ==================== Approval System ====================

    def set_user_approved(self, user_id: str, approved: bool) -> bool:
        """Set user approval status."""
        doc_ref = self.users.document(user_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.update({'approved': approved})
        return True

    def create_access_request(self, user_id: str, email: str) -> str:
        """Create an access request. Returns document ID."""
        access_requests = self.db.collection(ACCESS_REQUESTS_COLLECTION)
        doc_ref = access_requests.document()

        request_data = {
            'user_id': user_id,
            'email': email,
            'status': 'pending',
            'created_at': firestore.SERVER_TIMESTAMP,
            'reviewed_at': None
        }
        doc_ref.set(request_data)
        return doc_ref.id

    def get_user_access_request(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent access request for a user."""
        access_requests = self.db.collection(ACCESS_REQUESTS_COLLECTION)
        docs = access_requests.where('user_id', '==', user_id).stream()

        user_requests = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            user_requests.append(data)

        if not user_requests:
            return None

        def sort_key(x):
            created = x.get('created_at')
            if created is None:
                return ''
            if hasattr(created, 'isoformat'):
                return created.isoformat()
            return str(created)

        user_requests.sort(key=sort_key, reverse=True)
        return user_requests[0]

    def get_pending_access_requests(self) -> List[Dict[str, Any]]:
        """Get all pending access requests for admin review."""
        access_requests = self.db.collection(ACCESS_REQUESTS_COLLECTION)
        requests = []

        for doc in access_requests.where('status', '==', 'pending').stream():
            data = doc.to_dict()
            data['id'] = doc.id
            requests.append(data)

        def sort_key(x):
            created = x.get('created_at')
            if created is None:
                return ''
            if hasattr(created, 'isoformat'):
                return created.isoformat()
            return str(created)

        requests.sort(key=sort_key)
        return requests

    def approve_access_request(self, request_id: str) -> bool:
        """Approve an access request and update user."""
        access_requests = self.db.collection(ACCESS_REQUESTS_COLLECTION)
        doc_ref = access_requests.document(request_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        request_data = doc.to_dict()

        doc_ref.update({
            'status': 'approved',
            'reviewed_at': firestore.SERVER_TIMESTAMP
        })

        user_id = request_data['user_id']
        self.set_user_approved(user_id, True)
        return True

    def reject_access_request(self, request_id: str) -> bool:
        """Reject an access request."""
        access_requests = self.db.collection(ACCESS_REQUESTS_COLLECTION)
        doc_ref = access_requests.document(request_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        doc_ref.update({
            'status': 'rejected',
            'reviewed_at': firestore.SERVER_TIMESTAMP
        })
        return True


# Singleton
_firestore_service = None


def get_firestore():
    """Get or create the Firestore service singleton."""
    global _firestore_service
    if _firestore_service is None:
        try:
            _firestore_service = FirestoreService()
        except Exception as e:
            print(f"Firestore initialization failed: {e}")
            return None
    return _firestore_service
