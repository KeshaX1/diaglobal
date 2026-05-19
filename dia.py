import html
import json
import mimetypes
import os
from pathlib import PurePosixPath
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


IS_RENDER = os.environ.get("RENDER") == "true"
HOST = os.environ.get("HOST") or ("0.0.0.0" if IS_RENDER else "127.0.0.1")
PORT = int(os.environ.get("PORT") or ("10000" if IS_RENDER else "8000"))
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
CONTACT_TO_EMAIL = os.environ.get("CONTACT_TO_EMAIL", "info@diaglobals.com")
CONTACT_FROM_EMAIL = os.environ.get("CONTACT_FROM_EMAIL", CONTACT_TO_EMAIL)
CONTACT_FROM_NAME = os.environ.get("CONTACT_FROM_NAME", "Dia Global")
MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
LONG_CACHE_EXTENSIONS = {
    ".css",
    ".js",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".svg",
    ".ico",
}


def clean(value, max_length):
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def get_language(data):
    language = clean(data.get("language"), 5).lower()
    return "en" if language == "en" else "tr"


def json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def build_email_payload(data):
    name = clean(data.get("name"), 120)
    email = clean(data.get("email"), 180)
    phone = clean(data.get("phone"), 80)
    subject = clean(data.get("subject"), 160)
    message = clean(data.get("message"), 4000)
    language = get_language(data)

    if not name or not email or not subject or not message or "@" not in email:
        return None

    safe_name = html.escape(name)
    safe_email = html.escape(email)
    safe_phone = html.escape(phone or "-")
    safe_subject = html.escape(subject)
    safe_message = html.escape(message).replace("\n", "<br>")

    if language == "en":
        mail_title = "Dia Global contact form"
        labels = {
            "name": "Full name",
            "email": "Email",
            "phone": "Phone",
            "subject": "Subject",
            "message": "Message",
            "language": "Language",
        }
    else:
        mail_title = "Dia Global iletişim formu"
        labels = {
            "name": "Ad Soyad",
            "email": "E-posta",
            "phone": "Telefon",
            "subject": "Konu",
            "message": "Mesaj",
            "language": "Dil",
        }

    text = (
        f"{mail_title}\n\n"
        f"{labels['name']}: {name}\n"
        f"{labels['email']}: {email}\n"
        f"{labels['phone']}: {phone or '-'}\n"
        f"{labels['subject']}: {subject}\n"
        f"{labels['language']}: {language}\n\n"
        f"{labels['message']}:\n{message}\n"
    )

    return {
        "sender": {
            "name": CONTACT_FROM_NAME,
            "email": CONTACT_FROM_EMAIL,
        },
        "to": [{"email": CONTACT_TO_EMAIL}],
        "replyTo": {
            "name": name,
            "email": email,
        },
        "subject": f"{mail_title}: {subject}",
        "textContent": text,
        "htmlContent": (
            f"<h2>{html.escape(mail_title)}</h2>"
            f"<p><strong>{labels['name']}:</strong> {safe_name}</p>"
            f"<p><strong>{labels['email']}:</strong> {safe_email}</p>"
            f"<p><strong>{labels['phone']}:</strong> {safe_phone}</p>"
            f"<p><strong>{labels['subject']}:</strong> {safe_subject}</p>"
            f"<p><strong>{labels['language']}:</strong> {language}</p>"
            f"<p><strong>{labels['message']}:</strong><br>{safe_message}</p>"
        ),
    }


def send_contact_email(payload):
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured")

    body = json.dumps(payload).encode("utf-8")
    request = Request(
        BREVO_API_URL,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-key": api_key,
        },
    )

    with urlopen(request, timeout=20) as response:
        return response.status


def send_brevo_email(payload):
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured")

    body = json.dumps(payload).encode("utf-8")
    request = Request(
        BREVO_API_URL,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-key": api_key,
        },
    )

    with urlopen(request, timeout=20) as response:
        return response.status


def log_email_delivery_error(error):
    if isinstance(error, HTTPError):
        try:
            details = error.read().decode("utf-8", errors="replace")
        except Exception:
            details = ""
        print(f"Brevo email failed: HTTP {error.code} {error.reason} {details}")
        return

    print(f"Brevo email failed: {error}")


def build_newsletter_payloads(data):
    email = clean(data.get("email"), 180)
    language = get_language(data)

    if not email or "@" not in email:
        return None

    if language == "en":
        user_subject = "Dia Global e-bulletin registration"
        user_text = (
            "Hello,\n\n"
            "Your Dia Global e-bulletin registration has been received. "
            "We will use this email address to share updates about foreign trade, logistics, and operational developments.\n\n"
            "Dia Global"
        )
        user_html = (
            "<p>Hello,</p>"
            "<p>Your Dia Global e-bulletin registration has been received. "
            "We will use this email address to share updates about foreign trade, logistics, and operational developments.</p>"
            "<p>Dia Global</p>"
        )
    else:
        user_subject = "Dia Global e-bülten kaydınız alındı"
        user_text = (
            "Merhaba,\n\n"
            "Dia Global e-bülten kaydınız alındı. Dış ticaret, lojistik ve operasyonel gelişmelerle ilgili "
            "güncellemeleri bu e-posta adresi üzerinden sizinle paylaşacağız.\n\n"
            "Dia Global"
        )
        user_html = (
            "<p>Merhaba,</p>"
            "<p>Dia Global e-bülten kaydınız alındı. Dış ticaret, lojistik ve operasyonel gelişmelerle ilgili "
            "güncellemeleri bu e-posta adresi üzerinden sizinle paylaşacağız.</p>"
            "<p>Dia Global</p>"
        )

    admin_text = f"Yeni Dia Global e-bülten kaydı:\n\nE-posta: {email}\nDil: {language}\n"
    safe_email = html.escape(email)
    safe_language = html.escape(language)

    return [
        {
            "sender": {
                "name": CONTACT_FROM_NAME,
                "email": CONTACT_FROM_EMAIL,
            },
            "to": [{"email": email}],
            "subject": user_subject,
            "textContent": user_text,
            "htmlContent": user_html,
        },
        {
            "sender": {
                "name": CONTACT_FROM_NAME,
                "email": CONTACT_FROM_EMAIL,
            },
            "to": [{"email": CONTACT_TO_EMAIL}],
            "subject": "Yeni Dia Global e-bülten kaydı",
            "textContent": admin_text,
            "htmlContent": (
                "<h2>Yeni Dia Global e-bülten kaydı</h2>"
                f"<p><strong>E-posta:</strong> {safe_email}</p>"
                f"<p><strong>Dil:</strong> {safe_language}</p>"
            ),
        },
    ]


class DiaRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/config":
            json_response(self, 200, {"mapboxAccessToken": MAPBOX_ACCESS_TOKEN})
            return

        super().do_GET()

    def do_POST(self):
        if self.path not in {"/api/contact", "/api/newsletter"}:
            json_response(self, 404, {"ok": False, "error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            json_response(self, 400, {"ok": False, "error": "Invalid request"})
            return

        if content_length <= 0 or content_length > 20000:
            json_response(self, 400, {"ok": False, "error": "Invalid request"})
            return

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            json_response(self, 400, {"ok": False, "error": "Invalid JSON"})
            return

        if self.path == "/api/newsletter":
            payloads = build_newsletter_payloads(data)
            if payloads is None:
                json_response(self, 400, {"ok": False, "error": "Missing required fields"})
                return

            try:
                for payload in payloads:
                    send_brevo_email(payload)
            except RuntimeError as error:
                print(error)
                json_response(self, 500, {"ok": False, "error": "Email service is not configured"})
                return
            except (HTTPError, URLError, TimeoutError) as error:
                log_email_delivery_error(error)
                json_response(self, 502, {"ok": False, "error": "Email service failed"})
                return

            json_response(self, 200, {"ok": True})
            return

        payload = build_email_payload(data)
        if payload is None:
            json_response(self, 400, {"ok": False, "error": "Missing required fields"})
            return

        try:
            send_contact_email(payload)
        except RuntimeError as error:
            print(error)
            json_response(self, 500, {"ok": False, "error": "Email service is not configured"})
            return
        except (HTTPError, URLError, TimeoutError) as error:
            log_email_delivery_error(error)
            json_response(self, 502, {"ok": False, "error": "Email service failed"})
            return

        json_response(self, 200, {"ok": True})

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        path = PurePosixPath(self.path.split("?", 1)[0])
        extension = path.suffix.lower()
        if str(path).startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        elif extension in LONG_CACHE_EXTENSIONS:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        elif extension == ".html" or not extension:
            self.send_header("Cache-Control", "public, max-age=300")
        super().end_headers()


if __name__ == "__main__":
    mimetypes.add_type("application/javascript; charset=utf-8", ".js")
    mimetypes.add_type("text/css; charset=utf-8", ".css")
    server = ThreadingHTTPServer((HOST, PORT), DiaRequestHandler)
    print(f"Serving Dia Global at http://{HOST}:{PORT}/")
    server.serve_forever()
