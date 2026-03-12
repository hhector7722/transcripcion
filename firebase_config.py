"""
Inicialización de Firebase (Storage + Firestore).
Si no hay credenciales en env, las funciones que usan Firebase no harán nada.
"""
import os
import json
from typing import Any, Optional, Tuple

_firestore = None
_storage_bucket = None
_bucket_name: Optional[str] = None


def init_firebase() -> Tuple[Optional[Any], Optional[Any]]:
    """Inicializa Firebase y devuelve (bucket, firestore). Si no hay config, devuelve (None, None)."""
    global _firestore, _storage_bucket, _bucket_name
    if _storage_bucket is not None or _firestore is not None:
        return _storage_bucket, _firestore

    creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")

    if not bucket_name:
        return None, None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore, storage
    except ImportError:
        return None, None

    if not creds_json and not credentials_path:
        return None, None

    try:
        if creds_json:
            cred_dict = json.loads(creds_json)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate(credentials_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        _firestore = firestore.client()
        _storage_bucket = storage.bucket()
        _bucket_name = bucket_name
        return _storage_bucket, _firestore
    except Exception:
        return None, None


def get_firestore():
    if _firestore is None:
        init_firebase()
    return _firestore


def get_storage_bucket():
    if _storage_bucket is None:
        init_firebase()
    return _storage_bucket


def is_firebase_configured() -> bool:
    bucket, _ = init_firebase()
    return bucket is not None
