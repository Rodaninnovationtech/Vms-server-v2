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


# ----------------------------------------------------------------------
# bulk check-in: every pending approved visitor of one bulk_id,
# sharing ONE pass and ONE key. All-or-nothing.
# ----------------------------------------------------------------------

def check_in_bulk_pre_registration(user, bulk_id, pass_no="", key_no=""):
    pass_no = (pass_no or "").strip()
    key_no = (key_no or "").strip()

    with transaction.atomic():
        recs = []
        for kind, model in KIND_MODELS.items():
            qs = (
                model.objects.select_for_update(of=("self",))
                .select_related("person", "site", "tenant")
                .filter(
                    bulk_id=bulk_id,
                    source__in=PRE_REG_SOURCES,
                    approval_status="APPROVED",
                    check_in__isnull=True,
                )
            )
            recs.extend((kind, r) for r in qs)

        if not recs:
            return _fail("No pending approved visitors found for this bulk", 404)

        sites = {r.site_id for _, r in recs}
        if len(sites) > 1:
            return _fail("Bulk upload contains more than one site", 409)

        site = recs[0][1].site
        if not _can_check_in_at(user, site):
            return _fail("You can only check in visitors at your own site", 403)

        today = timezone.localdate()
        for _, r in recs:
            last_day = r.to_date or r.from_date
            if r.from_date and today < r.from_date:
                return _fail(
                    f"This bulk visit starts on {r.from_date.strftime('%d-%m-%Y')}", 409
                )
            if last_day and today > last_day:
                return _fail("This bulk pre-registration has expired", 409)

        # ---- persons ----
        person_ids = [r.person_id for _, r in recs]
        persons = {
            p.pk: p
            for p in VisitorDetail.objects.select_for_update().filter(pk__in=person_ids)
        }

        problems = []
        for _, r in recs:
            p = persons[r.person_id]
            if is_person_banned(p, site):
                problems.append(f"{p.person_name} (banned)")
            elif p.currently_checked_in:
                problems.append(f"{p.person_name} (already checked in)")
        if problems:
            return _fail("Cannot check in bulk: " + ", ".join(problems), 409)

        # ---- one pass / one key for the whole bulk ----
        pass_obj = None
        if pass_no:
            pass_obj = (
                Pass.objects.select_for_update()
                .filter(site=site, pass_no=pass_no, status="Active")
                .first()
            )
            if pass_obj is None:
                return _fail("Selected pass is not available")

        key_obj = None
        if key_no:
            key_obj = (
                Key.objects.select_for_update()
                .filter(site=site, key_no=key_no, status="Available")
                .first()
            )
            if key_obj is None:
                return _fail("Selected key is not available")

        # ---- update all rows ----
        now = timezone.now()
        for _, r in recs:
            r.check_in = now
            r.pass_no = pass_no
            r.key_no = key_no
            r.save()

            p = persons[r.person_id]
            p.currently_checked_in = True
            p.save()

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
        "message": f"{len(recs)} visitor(s) checked in",
        "data": {"count": len(recs), "bulk_id": bulk_id},
    }


# ----------------------------------------------------------------------
# bulk check-out: every checked-in visitor of one bulk_id
# ----------------------------------------------------------------------

def check_out_bulk_pre_registration(user, bulk_id):
    with transaction.atomic():
        recs = []
        for kind, model in KIND_MODELS.items():
            qs = (
                model.objects.select_for_update(of=("self",))
                .select_related("person", "site", "tenant")
                .filter(
                    bulk_id=bulk_id,
                    source__in=PRE_REG_SOURCES,
                    check_in__isnull=False,
                    check_out__isnull=True,
                )
            )
            recs.extend((kind, r) for r in qs)

        if not recs:
            return _fail("No checked-in visitors found for this bulk", 404)

        for site in {r.site for _, r in recs}:
            if not _can_check_in_at(user, site):
                return _fail("You can only check out visitors at your own site", 403)

        now = timezone.now()
        pass_keys, key_keys = set(), set()

        for _, r in recs:
            if r.pass_no:
                pass_keys.add((r.site_id, r.pass_no))
            if r.key_no:
                key_keys.add((r.site_id, r.key_no))
            r.check_out = now
            r.save()

        persons = VisitorDetail.objects.select_for_update().filter(
            pk__in=[r.person_id for _, r in recs]
        )
        for p in persons:
            p.currently_checked_in = False
            p.save()

        # release the shared pass / key
        for site_id, no in pass_keys:
            for obj in Pass.objects.select_for_update().filter(site_id=site_id, pass_no=no):
                obj.status = "Active"
                obj.updated_by = user
                obj.save()
        for site_id, no in key_keys:
            for obj in Key.objects.select_for_update().filter(site_id=site_id, key_no=no):
                obj.status = "Available"
                obj.updated_by = user
                obj.save()

    return {
        "success": True,
        "message": f"{len(recs)} visitor(s) checked out",
        "data": {"count": len(recs), "bulk_id": bulk_id},
    }