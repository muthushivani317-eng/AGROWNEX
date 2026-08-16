"""Mint a Firebase ID token for the controlled KVK tester."""

from __future__ import annotations

import os

import httpx
from firebase_admin import auth

from app.core.security import ensure_firebase_app


TESTER_PHONE_NUMBER = "+918667237404"
TOKEN_EXCHANGE_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"
)


def main() -> None:
    firebase_app = ensure_firebase_app()
    if firebase_app is None:
        raise RuntimeError("Firebase Admin is not configured.")

    user = auth.get_user_by_phone_number(TESTER_PHONE_NUMBER, app=firebase_app)
    custom_token = auth.create_custom_token(user.uid, app=firebase_app)

    response = httpx.post(
        TOKEN_EXCHANGE_URL,
        params={"key": os.environ["FIREBASE_WEB_API_KEY"]},
        json={"token": custom_token.decode(), "returnSecureToken": True},
        timeout=30.0,
    )
    response.raise_for_status()

    id_token = response.json().get("idToken")
    if not isinstance(id_token, str) or not id_token:
        raise RuntimeError("Firebase token exchange returned no ID token.")

    print(id_token)


if __name__ == "__main__":
    main()
