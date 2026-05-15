# graphspy/api/access_tokens.py

# Built-in imports
import json

# External library imports
from flask import Blueprint, redirect, request
import jwt

# Local library imports
from ..db import connection
from .company_auth import (
    ManualTokenError,
    normalize_pasted_token,
    save_validated_access_token,
    set_active_access_token,
)

bp = Blueprint("access_tokens", __name__)


@bp.get("/api/list_access_tokens")
def list_access_tokens():
    rows = connection.query_db_json("SELECT * FROM accesstokens")
    return json.dumps(rows)


@bp.post("/api/add_access_token")
def add_access_token():
    accesstoken = normalize_pasted_token(request.form.get("accesstoken", ""))
    description = request.form.get("description", "")
    if not accesstoken:
        return redirect("/admin?error=missing_token")
    try:
        access_token_id, _ = save_validated_access_token(accesstoken, description)
    except ManualTokenError as exc:
        return redirect(f"/admin?error={exc.error_key}")
    except Exception:
        return redirect("/admin?error=invalid_token")
    set_active_access_token(access_token_id)
    return redirect(f"/mail?token_id={access_token_id}")


@bp.get("/api/get_access_token/<id>")
def get_access_token(id):
    row = connection.query_db_json(
        "SELECT * FROM accesstokens WHERE id = ?", [id], one=True
    )
    return json.dumps(row)


@bp.get("/api/decode_token/<id>")
def decode_token(id):
    row = connection.query_db(
        "SELECT accesstoken FROM accesstokens WHERE id = ?", [id], one=True
    )
    if not row:
        return f"[Error] Could not find access token with id {id}", 400
    try:
        decoded = jwt.decode(row[0], options={"verify_signature": False})
    except jwt.exceptions.DecodeError:
        return {
            "token_type": "opaque",
            "resource": "https://graph.microsoft.com",
            "message": "This token cannot be decoded locally, but it can still be used with Microsoft Graph.",
        }
    return decoded


@bp.get("/api/delete_access_token/<id>")
def delete_access_token(id):
    connection.execute_db("DELETE FROM accesstokens WHERE id = ?", [id])
    return "true"


@bp.get("/api/active_access_token/<id>")
def set_active_access_token(id):
    existing = connection.query_db(
        "SELECT value FROM settings WHERE setting = 'active_access_token_id'", one=True
    )
    if not existing:
        connection.execute_db(
            "INSERT INTO settings (setting, value) VALUES ('active_access_token_id', ?)",
            (id,),
        )
    else:
        connection.execute_db(
            "UPDATE settings SET value = ? WHERE setting = 'active_access_token_id'",
            (id,),
        )
    return id


@bp.get("/api/active_access_token")
def get_active_access_token():
    row = connection.query_db(
        "SELECT value FROM settings WHERE setting = 'active_access_token_id'", one=True
    )
    return f"{row[0]}" if row else "0"
