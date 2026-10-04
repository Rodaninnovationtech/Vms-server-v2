import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def _d(value):
    return value.strftime("%d-%m-%Y") if value else "—"


def _t(value):
    return value.strftime("%I:%M %p") if value else ""


def _details(rec, kind):
    person = rec.person
    rows = [
        ("Visitor Name", person.person_name),
        ("Type", kind),
        ("Identity", f"{person.identity_type} · {person.identity_number}"),
        ("Contact", person.phone_number or "—"),
        ("Email", person.email or "—"),
    ]
    if kind == "Contractor":
        rows += [
            ("Company", rec.company or "—"),
            ("Company Phone", rec.company_phone or "—"),
        ]
    rows += [
        ("Site", rec.site.site_name),
        ("Location", rec.tenant.tenant_name if rec.tenant_id else "—"),
        ("From", f"{_d(rec.from_date)} {_t(rec.from_time)}".strip()),
        ("To", f"{_d(rec.to_date)} {_t(rec.to_time)}".strip()),
        ("Vehicle", rec.vehicle_number or "—"),
        ("Remark", rec.remark or "—"),
        ("Requested By", rec.requester_email or "—"),
    ]
    return rows


def send_pre_registration_request_mail(rec, kind):
    """Mails the selected approver. Never raises, so a mail problem
    cannot break the pre-registration request."""
    to_email = (rec.approver_email or "").strip()
    if not to_email:
        return

    try:
        rows = _details(rec, kind)
        link = f"{settings.FRONTEND_URL.rstrip('/')}{settings.APPROVAL_PAGE_PATH}"
        # subject = f"You got a request for Pre-Registration - {rec.person.person_name}"
        subject = f"Pre-registration request from {rec.person.person_name} awaiting your approval"

        text = (
            # "Hello,\n\nYou got a request for Pre-Registration. Details:\n\n"
            "Hello,\n\nA visitor pre-registration request is waiting for your approval. Details:\n\n"
            + "\n".join(f"{label}: {value}" for label, value in rows)
            + f"\n\nPlease review it here: {link}\n"
        )

        table = "".join(
            f"<tr><td style='padding:6px 12px;color:#64748b'>{escape(label)}</td>"
            f"<td style='padding:6px 12px;color:#0f172a'>{escape(str(value))}</td></tr>"
            for label, value in rows
        )
        html = (
            "<div style='font-family:Arial,sans-serif;font-size:14px'>"
            # "<p>Hello,</p><p><b>You got a request for Pre-Registration.</b></p>"
            "<p>Hello,</p><p>A visitor pre-registration request is waiting for your approval.</p>"
            "<table style='border-collapse:collapse;border:1px solid #e2e8f0'>"
            f"{table}</table>"
            f"<p><a href='{escape(link)}' style='background:#6d28d9;color:#fff;"
            "padding:10px 16px;border-radius:6px;text-decoration:none'>"
            # "Review Request</a></p></div>"
            "Review Request</a></p>"
            # f"<p style='color:#64748b;font-size:12px'>If the button doesn't work, open: {escape(link)}</p>"
            "</div>"
        )

        # msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg = EmailMultiAlternatives(
            subject, text, settings.DEFAULT_FROM_EMAIL, [to_email],
            reply_to=[rec.requester_email] if rec.requester_email else None,
            headers={"Auto-Submitted": "auto-generated"},
        )
        msg.attach_alternative(html, "text/html")
        msg.send()
    except Exception:
        logger.exception("Could not send pre-registration mail to %s", to_email)





# # set True if the visitor (person.email) should also get the decision mail
# NOTIFY_VISITOR = False


# def send_pre_registration_decision_mail(rec, kind, decided_by, approved):
#     """Mails the requester when a request is approved or rejected.
#     Never raises, so a mail problem cannot break the approval."""
#     recipients = []
#     if (rec.requester_email or "").strip():
#         recipients.append(rec.requester_email.strip())
#     if NOTIFY_VISITOR and (rec.person.email or "").strip():
#         visitor_mail = rec.person.email.strip()
#         if visitor_mail.lower() not in [r.lower() for r in recipients]:
#             recipients.append(visitor_mail)
#     if not recipients:
#         return

#     try:
#         word = "Approved" if approved else "Rejected"
#         color = "#047857" if approved else "#dc2626"

#         decider = (
#             f"{decided_by.first_name} {decided_by.last_name}".strip() or decided_by.email
#         )

#         rows = [("Decision", word), ("Decided By", decider)]
#         if not approved:
#             rows.append(("Reason", rec.approval_remark or "—"))
#         rows += _details(rec, kind)

#         link = (
#             f"{settings.FRONTEND_URL.rstrip('/')}"
#             f"{getattr(settings, 'PRE_REGISTRATION_PAGE_PATH', '/pre-registration')}"
#         )
#         subject = f"Your Pre-Registration request was {word} - {rec.person.person_name}"

#         text = (
#             "Hello,\n\n"
#             f"Your Pre-Registration request has been {word.lower()}. Details:\n\n"
#             + "\n".join(f"{label}: {value}" for label, value in rows)
#             + f"\n\nView it here: {link}\n"
#         )

#         table = "".join(
#             f"<tr><td style='padding:6px 12px;color:#64748b'>{escape(label)}</td>"
#             f"<td style='padding:6px 12px;color:#0f172a'>{escape(str(value))}</td></tr>"
#             for label, value in rows
#         )
#         html = (
#             "<div style='font-family:Arial,sans-serif;font-size:14px'>"
#             "<p>Hello,</p>"
#             f"<p><b>Your Pre-Registration request has been "
#             f"<span style='color:{color}'>{word.lower()}</span>.</b></p>"
#             "<table style='border-collapse:collapse;border:1px solid #e2e8f0'>"
#             f"{table}</table>"
#             f"<p><a href='{escape(link)}' style='background:#6d28d9;color:#fff;"
#             "padding:10px 16px;border-radius:6px;text-decoration:none'>"
#             "View Request</a></p></div>"
#         )

#         msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, recipients)
#         msg.attach_alternative(html, "text/html")
#         msg.send()
#     except Exception:
#         logger.exception("Could not send pre-registration decision mail to %s", recipients)



# True -> the requester also gets a copy of the decision mail
COPY_REQUESTER = False


def send_pre_registration_decision_mail(rec, kind, decided_by, approved):
    """Mails the VISITOR (person.email) when a request is approved or rejected.
    If the visitor has no email, falls back to the requester.
    Never raises, so a mail problem cannot break the approval."""
    visitor_mail = (rec.person.email or "").strip()
    requester_mail = (rec.requester_email or "").strip()

    recipients = []
    if visitor_mail:
        recipients.append(visitor_mail)
        if COPY_REQUESTER and requester_mail and requester_mail.lower() != visitor_mail.lower():
            recipients.append(requester_mail)
    elif requester_mail:
        recipients.append(requester_mail)   # fallback: visitor has no email

    if not recipients:
        return

    try:
        word = "Approved" if approved else "Rejected"
        color = "#047857" if approved else "#dc2626"

        decider = (
            f"{decided_by.first_name} {decided_by.last_name}".strip() or decided_by.email
        )

        rows = [("Decision", word), ("Decided By", decider)]
        if not approved:
            rows.append(("Reason", rec.approval_remark or "—"))
        rows += _details(rec, kind)

        # subject = f"Your visit pre-registration was {word} - {rec.person.person_name}"
        subject = f"Visit pre-registration {word.lower()}: {rec.person.person_name}"

        text = (
            f"Hello {rec.person.person_name},\n\n"
            f"Your visit pre-registration has been {word.lower()}. Details:\n\n"
            + "\n".join(f"{label}: {value}" for label, value in rows)
            + "\n"
        )

        table = "".join(
            f"<tr><td style='padding:6px 12px;color:#64748b'>{escape(label)}</td>"
            f"<td style='padding:6px 12px;color:#0f172a'>{escape(str(value))}</td></tr>"
            for label, value in rows
        )
        html = (
            "<div style='font-family:Arial,sans-serif;font-size:14px'>"
            f"<p>Hello {escape(rec.person.person_name)},</p>"
            f"<p><b>Your visit pre-registration has been "
            f"<span style='color:{color}'>{word.lower()}</span>.</b></p>"
            "<table style='border-collapse:collapse;border:1px solid #e2e8f0'>"
            f"{table}</table></div>"
        )

        # msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, recipients)
        msg = EmailMultiAlternatives(
            subject, text, settings.DEFAULT_FROM_EMAIL, recipients,
            reply_to=[requester_mail] if requester_mail else None,
            headers={"Auto-Submitted": "auto-generated"},
        )
        msg.attach_alternative(html, "text/html")
        msg.send()
    except Exception:
        logger.exception("Could not send pre-registration decision mail to %s", recipients)