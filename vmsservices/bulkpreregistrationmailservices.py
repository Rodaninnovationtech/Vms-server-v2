import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def _d(value):
    return value.strftime("%d-%m-%Y") if value else "—"


def _t(value):
    return value.strftime("%I:%M %p") if value else ""


def send_bulk_pre_registration_request_mail(records, kind, bulk_id, requester):
    """ONE summary mail to the approver for the whole upload (not one per row).
    Never raises, so a mail problem cannot break the upload."""
    if not records:
        return
    first = records[0]
    to_email = (first.approver_email or "").strip()
    if not to_email:
        return

    try:
        link = f"{settings.FRONTEND_URL.rstrip('/')}{settings.APPROVAL_PAGE_PATH}"
        head = [
            ("Bulk ID", bulk_id),
            ("Type", kind),
            ("Visitors", str(len(records))),
            ("Site", first.site.site_name),
            ("Location", first.tenant.tenant_name if first.tenant_id else "—"),
            ("From", f"{_d(first.from_date)} {_t(first.from_time)}".strip()),
            ("To", f"{_d(first.to_date)} {_t(first.to_time)}".strip()),
            ("Requested By", requester.email),
        ]
        people = [
            (r.person.person_name, f"{r.person.identity_type} · {r.person.identity_number}")
            for r in records
        ]

        subject = f"Bulk pre-registration {bulk_id}: {len(records)} visitors awaiting your approval"
        text = (
            "Hello,\n\nA bulk pre-registration request is waiting for your approval.\n\n"
            + "\n".join(f"{k}: {v}" for k, v in head)
            + "\n\nVisitors:\n"
            + "\n".join(f"- {n} ({i})" for n, i in people)
            + f"\n\nPlease review it here: {link}\n"
        )

        def rows_html(pairs):
            return "".join(
                f"<tr><td style='padding:6px 12px;color:#64748b'>{escape(a)}</td>"
                f"<td style='padding:6px 12px;color:#0f172a'>{escape(b)}</td></tr>"
                for a, b in pairs
            )

        html = (
            "<div style='font-family:Arial,sans-serif;font-size:14px'>"
            "<p>Hello,</p><p>A bulk pre-registration request is waiting for your approval.</p>"
            f"<table style='border-collapse:collapse;border:1px solid #e2e8f0'>{rows_html(head)}</table>"
            "<p><b>Visitors</b></p>"
            f"<table style='border-collapse:collapse;border:1px solid #e2e8f0'>{rows_html(people)}</table>"
            f"<p><a href='{escape(link)}' style='background:#6d28d9;color:#fff;"
            "padding:10px 16px;border-radius:6px;text-decoration:none'>Review Requests</a></p>"
            "</div>"
        )

        msg = EmailMultiAlternatives(
            subject, text, settings.DEFAULT_FROM_EMAIL, [to_email],
            reply_to=[requester.email] if requester.email else None,
            headers={"Auto-Submitted": "auto-generated"},
        )
        msg.attach_alternative(html, "text/html")
        msg.send()
    except Exception:
        logger.exception("Could not send bulk pre-registration mail to %s", to_email)