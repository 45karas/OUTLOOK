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


def _get_mailbox() -> str:
    """Extract mailbox from request, returning 'me' for personal mailbox."""
    raw = request.form.get("mailbox") or request.args.get("mailbox", "")
    shared = raw.strip()
    if shared:
        return f"users/{shared}"
    return "me"


@bp.get("/api/outlook/folders")
def list_folders():
    """List mail folders."""
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        folders = outlook_core.list_mail_folders(token_id, mailbox=mailbox)
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
        mailbox (optional, shared mailbox email)
    """
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        folder_id = request.args.get("folder_id", "inbox")
        top = int(request.args.get("top", 50))
        skip = int(request.args.get("skip", 0))
        search = request.args.get("search", "")
        order_by = request.args.get("order_by", "receivedDateTime desc")

        result = outlook_core.list_messages(
            token_id, folder_id=folder_id, top=top, skip=skip,
            search=search, order_by=order_by, mailbox=mailbox,
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
        mailbox = _get_mailbox()
        msg = outlook_core.get_message(token_id, message_id, mailbox=mailbox)
        return json.dumps(msg)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.get("/api/outlook/me")
def get_me():
    """Get current user's email / profile info."""
    try:
        token_id = _get_token_id()
        from ..core import requests_ as gspy_requests
        mailbox = _get_mailbox()
        resp = gspy_requests.graph_request(f"/{mailbox}", token_id, method="GET")
        return resp
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
        mailbox (optional)
    """
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
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
            mailbox=mailbox,
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
        mailbox = _get_mailbox()
        success = outlook_core.delete_message(token_id, message_id, mailbox=mailbox)
        return json.dumps({"success": success})
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/permanent_delete/<message_id>")
def permanent_delete_message(message_id: str):
    """Permanently delete a message (bypasses Deleted Items)."""
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        success = outlook_core.permanent_delete(token_id, message_id, mailbox=mailbox)
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
        mailbox (optional)
    """
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        query = request.args.get("query", "")
        top = int(request.args.get("top", 50))

        if not query:
            return "[Error] Search query is required", 400

        result = outlook_core.search_messages(token_id, query, top=top, mailbox=mailbox)
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
        mailbox = _get_mailbox()
        success = outlook_core.mark_as_read(token_id, message_id, mailbox=mailbox)
        return json.dumps({"success": success})
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/mark_unread/<message_id>")
def mark_as_unread(message_id: str):
    """Mark a message as unread."""
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        success = outlook_core.mark_as_unread(token_id, message_id, mailbox=mailbox)
        return json.dumps({"success": success})
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/toggle_flag/<message_id>")
def toggle_flag(message_id: str):
    """Toggle the flag status of a message.

    Form params:
        flagged: "true" or "false"
    """
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        flagged = request.form.get("flagged", "true").lower() == "true"
        result = outlook_core.toggle_flag(token_id, message_id, flagged, mailbox=mailbox)
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/reply/<message_id>")
def reply_message(message_id: str):
    """Reply to a message (creates draft reply).

    Form params:
        body: HTML or text body
        content_type: "HTML" (default) or "Text"
        reply_all: "true" or "false" (default: false)
        mailbox (optional)
    """
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        body = request.form.get("body", "")
        content_type = request.form.get("content_type", "HTML")
        reply_all = request.form.get("reply_all", "false").lower() == "true"

        if not body:
            return "[Error] Reply body is required", 400

        result = outlook_core.reply_message(
            token_id, message_id, body,
            content_type=content_type, reply_all=reply_all, mailbox=mailbox,
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
        mailbox = _get_mailbox()
        destination = request.form.get("destination_folder_id", "")

        if not destination:
            return "[Error] destination_folder_id is required", 400

        result = outlook_core.move_message(token_id, message_id, destination, mailbox=mailbox)
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.get("/api/outlook/attachments/<message_id>")
def get_attachments(message_id: str):
    """Get attachments for a message."""
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        attachments = outlook_core.get_attachments(token_id, message_id, mailbox=mailbox)
        return json.dumps(attachments)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/upload_attachment/<message_id>")
def upload_attachment(message_id: str):
    """Upload a file attachment to a draft message.

    Form params:
        name: attachment filename
        content_type: MIME type
        content_bytes: base64-encoded file content
    """
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        name = request.form.get("name", "")
        content_type = request.form.get("content_type", "application/octet-stream")
        content_bytes = request.form.get("content_bytes", "")

        if not name:
            return "[Error] Attachment name is required", 400
        if not content_bytes:
            return "[Error] Attachment content_bytes is required", 400

        result = outlook_core.upload_attachment(
            token_id, message_id, name, content_type, content_bytes, mailbox=mailbox,
        )
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/send_draft/<message_id>")
def send_draft(message_id: str):
    """Send a previously created draft message."""
    try:
        token_id = _get_token_id()
        mailbox = _get_mailbox()
        success = outlook_core.send_draft(token_id, message_id, mailbox=mailbox)
        return json.dumps({"success": success})
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500


@bp.post("/api/outlook/create_draft")
def create_draft():
    """Create a draft message.

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
        mailbox = _get_mailbox()
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

        if not subject:
            return "[Error] Subject is required", 400

        result = outlook_core.create_draft(
            token_id, to_recipients, subject, body,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            content_type=content_type,
            importance=importance,
            mailbox=mailbox,
        )
        return json.dumps(result)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"[Error] {e}", 500
