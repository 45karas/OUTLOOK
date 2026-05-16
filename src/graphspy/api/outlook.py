# graphspy/api/outlook.py

"""API endpoints for server-side Outlook/email operations."""

# Built-in imports
import json

# External library imports
from flask import Blueprint, request

# Local library imports
from ..core import outlook as outlook_core

bp = Blueprint("outlook", __name__)


def _get_token_id() -> int:
    """Extract access_token_id from request, or use the active token."""
    token_id = request.form.get("access_token_id") or request.args.get("access_token_id")

    if not token_id:
        from ..db import connection
        row = connection.query_db(
            "SELECT value FROM settings WHERE setting = 'active_access_token_id'",
            one=True,
        )
        token_id = row[0] if row else None

    if not token_id or token_id == "0":
        raise ValueError("No access token specified and no active token set")

    return int(token_id)


@bp.get("/api/outlook/folders")
def list_folders():
    """List mail folders."""
    try:
        token_id = _get_token_id()
        folders = outlook_core.list_mail_folders(token_id)
        return json.dumps(folders)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.get("/api/outlook/messages")
def list_messages():
    """List messages in a folder.

    Query params:
        folder_id (default: inbox)
        top (default: 50)
        skip (default: 0)
        search (optional)
        order_by (default: receivedDateTime desc)
    """
    try:
        token_id = _get_token_id()
        folder_id = request.args.get("folder_id", "inbox")
        top = int(request.args.get("top", 50))
        skip = int(request.args.get("skip", 0))
        search = request.args.get("search", "")
        order_by = request.args.get("order_by", "receivedDateTime desc")

        result = outlook_core.list_messages(
            token_id, folder_id=folder_id, top=top, skip=skip,
            search=search, order_by=order_by,
        )
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.get("/api/outlook/message/<message_id>")
def get_message(message_id: str):
    """Get full details of a single message."""
    try:
        token_id = _get_token_id()
        msg = outlook_core.get_message(token_id, message_id)
        return json.dumps(msg)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/send")
def send_message():
    """Send an email.

    Form params:
        to: JSON array of {email, name} objects
        subject: string
        body: HTML or text body
        cc: JSON array (optional)
        bcc: JSON array (optional)
        content_type: "HTML" (default) or "Text"
        importance: "normal" (default), "low", or "high"
    """
    try:
        token_id = _get_token_id()
        to_raw = request.form.get("to", "[]")
        subject = request.form.get("subject", "")
        body = request.form.get("body", "")
        cc_raw = request.form.get("cc", "")
        bcc_raw = request.form.get("bcc", "")
        content_type = request.form.get("content_type", "HTML")
        importance = request.form.get("importance", "normal")

        to_recipients = json.loads(to_raw) if to_raw else []
        cc_recipients = json.loads(cc_raw) if cc_raw else None
        bcc_recipients = json.loads(bcc_raw) if bcc_raw else None

        if not to_recipients:
            return "[Error] At least one 'to' recipient is required", 400
        if not subject:
            return "[Error] Subject is required", 400

        result = outlook_core.send_message(
            token_id, to_recipients, subject, body,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            content_type=content_type,
            importance=importance,
        )
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.get("/api/outlook/delete/<message_id>")
def delete_message(message_id: str):
    """Delete a message (move to Deleted Items)."""
    try:
        token_id = _get_token_id()
        success = outlook_core.delete_message(token_id, message_id)
        return json.dumps({"success": success})
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.get("/api/outlook/search")
def search_messages():
    """Search messages across all folders.

    Query params:
        query: search string
        top: max results (default 50)
    """
    try:
        token_id = _get_token_id()
        query = request.args.get("query", "")
        top = int(request.args.get("top", 50))

        if not query:
            return "[Error] Search query is required", 400

        result = outlook_core.search_messages(token_id, query, top=top)
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/mark_read/<message_id>")
def mark_as_read(message_id: str):
    """Mark a message as read."""
    try:
        token_id = _get_token_id()
        success = outlook_core.mark_as_read(token_id, message_id)
        return json.dumps({"success": success})
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/reply/<message_id>")
def reply_message(message_id: str):
    """Reply to a message.

    Form params:
        body: HTML or text body
        content_type: "HTML" (default) or "Text"
        reply_all: "true" or "false" (default: false)
    """
    try:
        token_id = _get_token_id()
        body = request.form.get("body", "")
        content_type = request.form.get("content_type", "HTML")
        reply_all = request.form.get("reply_all", "false").lower() == "true"

        if not body:
            return "[Error] Reply body is required", 400

        result = outlook_core.reply_message(
            token_id, message_id, body,
            content_type=content_type, reply_all=reply_all,
        )
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/move/<message_id>")
def move_message(message_id: str):
    """Move a message to a different folder.

    Form params:
        destination_folder_id: target folder ID
    """
    try:
        token_id = _get_token_id()
        destination = request.form.get("destination_folder_id", "")

        if not destination:
            return "[Error] destination_folder_id is required", 400

        result = outlook_core.move_message(token_id, message_id, destination)
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500
