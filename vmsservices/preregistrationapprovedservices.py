from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone

from .bancreationservices import is_person_banned
from .models import Key, Pass, VisitorDetail
from .visitorcontructorcreationsservices import (
    KIND_MODELS,
    PRE_REG_SOURCES,
    _build_qs,
    _can_check_in_at,
    _fail,
    _open_visit_sites,
    _serialize,
    _site_scope,
)

VISITOR_MENU_KEY = "/visitor"


def _serialize_row(rec, kind):
    data = _serialize(rec, kind)
    today = timezone.localdate()
    last_day = rec.to_date or rec.from_date
    data["can_check_in"] = bool(
        not rec.check_in
        and rec.from_date
        and rec.from_date <= today <= last_day
    )
    return data


# ----------------------------------------------------------------------
# list (approved pre-registrations only)
# ----------------------------------------------------------------------

def list_approved_pre_registrations(
    user,
    page=None,
    page_size=None,
    search="",
    site_guid=None,
    kind="",
    visit_status="",
    from_date=None,
    to_date=None,
):
    scope_q, error = _site_scope(user, site_guid)
    if error:
        return error

    search = (search or "").strip()
    kinds = [kind] if kind else list(KIND_MODELS.keys())

    rows = []
    for k in kinds:
        qs = _build_qs(KIND_MODELS[k], scope_q, search, from_date, to_date).filter(
            source__in=PRE_REG_SOURCES,
            approval_status="APPROVED",
        )

        if visit_status == "Pending":
            qs = qs.filter(check_in__isnull=True)
        elif visit_status == "Checked In":
            qs = qs.filter(check_in__isnull=False, check_out__isnull=True)
        elif visit_status == "Checked Out":
            qs = qs.filter(check_out__isnull=False)

        for rec in qs:
            rows.append((rec.created_at, k, rec))

    rows.sort(key=lambda r: r[0], reverse=True)

    if page is None and page_size is None:
        return {
            "success": True,
            "message": "Approved pre-registrations fetched",
            "data": {"results": [_serialize_row(rec, k) for _, k, rec in rows]},
        }

    page = page or 1
    page_size = page_size or 10
    paginator = Paginator(rows, page_size)

    if page > paginator.num_pages and paginator.num_pages > 0:
        return _fail("Page number out of range", 404)

    page_obj = paginator.page(page)

    return {
        "success": True,
        "message": "Approved pre-registrations fetched",
        "data": {
            "results": [_serialize_row(rec, k) for _, k, rec in page_obj.object_list],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": paginator.count,
                "total_pages": paginator.num_pages,
            },
        },
    }


# ----------------------------------------------------------------------
# check-in (updates the existing pre-registration row)
# ----------------------------------------------------------------------

def check_in_pre_registration(
    user, kind, guid, pass_no="", key_no="", vehicle_number=""
):
    model = KIND_MODELS[kind]
    pass_no = (pass_no or "").strip()
    key_no = (key_no or "").strip()

    with transaction.atomic():
        rec = (
            model.objects.select_for_update(of=("self",))
            .select_related("person", "site", "tenant")
            .filter(guid=guid, source__in=PRE_REG_SOURCES)
            .first()
        )
        if rec is None:
            return _fail("Pre-registration not found", 404)

        if rec.approval_status != "APPROVED":
            return _fail("Only approved requests can be checked in", 409)

        if not _can_check_in_at(user, rec.site):
            return _fail("You can only check in visitors at your own site", 403)

        if rec.check_in:
            return _fail("This visit is already checked in", 409)

        today = timezone.localdate()
        if rec.from_date and today < rec.from_date:
            return _fail(
                f"This visit starts on {rec.from_date.strftime('%d-%m-%Y')}", 409
            )
        if (rec.to_date or rec.from_date) and today > (rec.to_date or rec.from_date):
            return _fail("This pre-registration has expired", 409)

        # ---- person ----
        person = VisitorDetail.objects.select_for_update().get(pk=rec.person_id)

        if is_person_banned(person, rec.site):
            return _fail(
                "This person is banned at this site and cannot be checked in", 403
            )

        if person.currently_checked_in:
            open_site = _open_visit_sites([person.id]).get(person.id)
            where = f" at {open_site['name']}" if open_site else ""
            return _fail(f"This person is already checked in{where}", 409)

        # ---- pass / key must be free at this site ----
        pass_obj = None
        if pass_no:
            pass_obj = (
                Pass.objects.select_for_update()
                .filter(site=rec.site, pass_no=pass_no, status="Active")
                .first()
            )
            if pass_obj is None:
                return _fail("Selected pass is not available")

        key_obj = None
        if key_no:
            key_obj = (
                Key.objects.select_for_update()
                .filter(site=rec.site, key_no=key_no, status="Available")
                .first()
            )
            if key_obj is None:
                return _fail("Selected key is not available")

        # ---- update the visit row ----
        rec.check_in = timezone.now()
        rec.pass_no = pass_no
        rec.key_no = key_no
        rec.vehicle_number = (vehicle_number or "").strip()
        rec.save()

        person.currently_checked_in = True
        person.save()
        rec.person = person

        if pass_obj:
            pass_obj.status = "Assigned"
            pass_obj.updated_by = user
            pass_obj.save()
        if key_obj:
            key_obj.status = "Assigned"
            key_obj.updated_by = user
            key_obj.save()

    return {
        "success": True,
        "message": "Checked in",
        "data": _serialize_row(rec, kind),
    }