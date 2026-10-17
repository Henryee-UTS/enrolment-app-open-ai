
"""Lab 11 JWT verification endpoint."""

import os

import jwt
from flask import Blueprint, jsonify, request


auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/auth/verify")
def verify_token():
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret or len(secret) < 32:
        return jsonify({"error": "JWT authentication not configured"}), 503

    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return jsonify({"error": "Bearer token required"}), 401

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        return jsonify({"error": "Bearer token required"}), 401

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    return jsonify({
        "status": "valid",
        "subject": payload.get("sub"),
    }), 200
