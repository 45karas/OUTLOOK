# graphspy/web/pages.py

# Built-in imports
import os

# Local library imports
from ..api.company_auth import oauth_configured
from ..db import connection

# External library imports
from flask import Blueprint, redirect, render_template, request, send_from_directory, session

bp = Blueprint("pages", __name__, template_folder="templates", static_folder="static")


@bp.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(bp.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@bp.route("/")
def home():
    return redirect("/admin")


@bp.route("/admin")
def admin():
    accounts = connection.query_db_json(
        "SELECT id, stored_at, issued_at, expires_at, description, user, resource FROM accesstokens ORDER BY id DESC"
    )
    return render_template(
        "admin_panel.html",
        title="DollarHub Admin",
        accounts=accounts,
        error=request.args.get("error", ""),
        oauth_ready=oauth_configured(),
    )


@bp.route("/connect")
def customer_connect():
    return render_template(
        "customer_connect.html",
        title="Connect Mailbox",
        customer=request.args.get("customer", "").strip(),
        oauth_ready=oauth_configured(),
    )


@bp.route("/connected")
def customer_connected():
    return render_template("customer_connected.html", title="Mailbox Connected")


@bp.route("/settings")
def settings():
    return render_template("settings.html", title="Settings")


def has_active_access_token() -> bool:
    row = connection.query_db(
        "SELECT value FROM settings WHERE setting = 'active_access_token_id'", one=True
    )
    if not row or not row[0] or str(row[0]) == "0":
        return False
    token_row = connection.query_db(
        "SELECT id FROM accesstokens WHERE id = ?", [row[0]], one=True
    )
    return bool(token_row)


@bp.route("/mail")
def mail():
    token_id = request.args.get("token_id", "").strip()
    if token_id.isdigit():
        token_row = connection.query_db_json(
            "SELECT id, description, user FROM accesstokens WHERE id = ?",
            [token_id],
            one=True,
        )
        if token_row:
            connection.execute_db(
                "INSERT OR REPLACE INTO settings (setting, value) VALUES ('active_access_token_id', ?)",
                (token_id,),
            )
            session["company_user"] = token_row.get("user") or "Microsoft user"
            session["company_access_token_id"] = int(token_id)
        else:
            return redirect("/admin?error=missing_token")

    if not has_active_access_token():
        latest = connection.query_db(
            "SELECT id FROM accesstokens ORDER BY id DESC LIMIT 1", one=True
        )
        if latest:
            return redirect(f"/mail?token_id={latest[0]}")
        session.clear()
        return redirect("/admin?error=no_active_token")
    return render_template("mail_panel.html", title="Outlook Mail", token_id=token_id)


@bp.route("/setup-login")
def setup_login():
    return render_template("setup_login.html", title="Microsoft Login Setup")


@bp.route("/access_tokens")
def access_tokens():
    return render_template("access_tokens.html", title="Access Tokens")


@bp.route("/refresh_tokens")
def refresh_tokens():
    return render_template("refresh_tokens.html", title="Refresh Tokens")


@bp.route("/device_certificates")
def device_certificates():
    return render_template("device_certificates.html", title="Device Certificates")


@bp.route("/primary_refresh_tokens")
def primary_refresh_tokens():
    return render_template("primary_refresh_tokens.html", title="Primary Refresh Tokens")


@bp.route("/winhello_keys")
def winhello_keys():
    return render_template("winhello_keys.html", title="Windows Hello Keys")


@bp.route("/device_codes")
def device_codes():
    return render_template("device_codes.html", title="Device Codes")


@bp.route("/mfa")
def mfa():
    return render_template("mfa.html", title="MFA Methods")


@bp.route("/custom_requests")
def custom_requests():
    return render_template("custom_requests.html", title="Custom Requests")


@bp.route("/generic_search")
def generic_search():
    return render_template("generic_search.html", title="Generic MSGraph Search")


@bp.route("/recent_files")
def recent_files():
    return render_template("recent_files.html", title="Recent Files")


@bp.route("/shared_with_me")
def shared_with_me():
    return render_template("shared_with_me.html", title="Files Shared With Me")


@bp.route("/onedrive")
def onedrive():
    return render_template("OneDrive.html", title="OneDrive")


@bp.route("/sharepoint_sites")
def sharepoint_sites():
    return render_template("SharePointSites.html", title="SharePoint Sites")


@bp.route("/sharepoint_drives")
def sharepoint_drives():
    return render_template("SharePointDrives.html", title="SharePoint Drives")


@bp.route("/sharepoint")
def sharepoint():
    return render_template("SharePoint.html", title="SharePoint")


@bp.route("/outlook")
def outlook():
    return render_template("outlook.html", title="Outlook")


@bp.route("/outlook_graph")
def outlook_graph():
    return render_template("outlook_graph.html", title="Outlook Graph")


@bp.route("/teams")
def teams():
    return render_template("teams.html", title="Microsoft Teams")


@bp.route("/entra_users")
def entra_users():
    return render_template("entra_users.html", title="Entra ID Users")


@bp.route("/entra_groups")
def entra_groups():
    return render_template("entra_groups.html", title="Entra ID Groups")


@bp.route("/entra_roles")
def entra_roles():
    return render_template('entra_roles.html', title="Entra ID Roles")




