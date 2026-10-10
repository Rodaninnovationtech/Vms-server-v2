from itertools import chain
from math import ceil

from django.db.models import Q
from django.db.models.functions import Coalesce

from .models import Contractor, RolePermission, Site, Visitor, VisitorType

# must match the menu_key saved in RolePermission for the Reports page
REPORT_MENU_KEY = "/report"

# same rule as pre-registration ("contructor" matches the spelling in the data)
COMPANY_VISITOR_TYPES = ("contractor", "contructor")


class ReportAccessDenied(Exception):
    pass


def _kinds_for(visitor_type_guid):
    """Which tables to read for the selected visitor type."""
    if not visitor_type_guid:
        return {"Visitor", "Contractor"}
    vt = VisitorType.objects.filter(guid=visitor_type_guid).first()
    if vt is None:
        return set()
    if vt.name.strip().lower() in COMPANY_VISITOR_TYPES:
        return {"Contractor"}
    return {"Visitor"}


# ---------------------------------------------------------------------
# which sites may this user see?  None = all sites (super admin)
# ---------------------------------------------------------------------

def _with_descendants(root_ids):
    seen = set(root_ids)
    frontier = list(root_ids)
    while frontier:
        children = Site.objects.filter(parent_id__in=frontier).values_list("id", flat=True)
        frontier = [c for c in children if c not in seen]
        seen.update(frontier)
    return seen


def allowed_site_ids(user):
    if user.is_super_admin():
        return None

    if not user.role_id:
        raise ReportAccessDenied("You do not have access to reports.")

    perm = RolePermission.objects.filter(
        role_id=user.role_id, menu_key=REPORT_MENU_KEY, menu_enabled=True
    ).first()
    if not perm:
        raise ReportAccessDenied("You do not have access to reports.")

    if not user.site_id:
        return set()

    ids = {user.site_id}
    # sub-sites only when "view" (can_view_subsites) is true
    if perm.can_view_subsites:
        ids = _with_descendants(ids)
    return ids


# ---------------------------------------------------------------------
# queryset + row builders
# ---------------------------------------------------------------------

# def _build_queryset(model, site_ids, f):
#     qs = (
#         model.objects
#         .select_related("person", "site", "tenant")
#         .filter(check_in__isnull=False)
#     )

#     if site_ids is not None:
#         qs = qs.filter(site_id__in=site_ids)

#     if f.get("site_guid"):
#         qs = qs.filter(site__guid=f["site_guid"])

#     if f.get("from_date"):
#         qs = qs.filter(check_in__date__gte=f["from_date"])

#     if f.get("to_date"):
#         qs = qs.filter(check_in__date__lte=f["to_date"])
def _build_queryset(model, site_ids, f):
    qs = (
        model.objects
        .select_related("person", "site", "tenant")
        # hide requests still waiting for approval or rejected
        # (walk-ins have approval_status = NULL, so they are kept)
        .exclude(approval_status__in=["PENDING", "REJECTED"])
        # date used for sorting: check-in time, or created time if not checked in yet
        .annotate(sort_at=Coalesce("check_in", "created_at"))
    )

    if site_ids is not None:
        qs = qs.filter(site_id__in=site_ids)

    if f.get("site_guid"):
        qs = qs.filter(site__guid=f["site_guid"])

    if f.get("from_date"):
        qs = qs.filter(sort_at__date__gte=f["from_date"])

    if f.get("to_date"):
        qs = qs.filter(sort_at__date__lte=f["to_date"])

    term = (f.get("search") or "").strip()
    if term:
        qs = qs.filter(
            Q(person__person_name__icontains=term)
            | Q(person__phone_number__icontains=term)
            | Q(person__identity_number__icontains=term)
            | Q(person__email__icontains=term)
            | Q(company__icontains=term)
        )

    return qs


def _row(kind, obj):
    return {
        "guid": str(obj.guid),
        "kind": kind,
        "person_name": obj.person.person_name,
        "identity_type": obj.person.identity_type,
        "identity_number": obj.person.identity_number,
        "phone_number": obj.person.phone_number,
        "email": obj.person.email or "",
        "visitor_type_name": kind,
        "company": obj.company,
        "company_phone": obj.company_phone,
        "site_name": obj.site.site_name,
        "location": obj.tenant.tenant_name if obj.tenant else "",
        "pass_no": obj.pass_no,
        "key_no": obj.key_no,
        "source": obj.source or "",
        "vehicle_number": obj.vehicle_number,
        # "check_in": obj.check_in.isoformat() if obj.check_in else None,
        # "check_out": obj.check_out.isoformat() if obj.check_out else None,
        # "status": "Checked Out" if obj.check_out else "Checked In",
        "check_in": obj.check_in.isoformat() if obj.check_in else None,
        "check_out": obj.check_out.isoformat() if obj.check_out else None,
        "status": (
            "Checked Out" if obj.check_out
            else "Checked In" if obj.check_in
            else "Pending"
        ),
    }


# ---------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------

def report_list(user, filters):
    """Returns (rows, pagination). Raises ReportAccessDenied."""
    site_ids = allowed_site_ids(user)

    kinds = _kinds_for(filters.get("visitor_type_guid"))

    visitors = (
        # _build_queryset(Visitor, site_ids, filters).order_by("-check_in")
        _build_queryset(Visitor, site_ids, filters).order_by("-sort_at")
        if "Visitor" in kinds
        else Visitor.objects.none()
    )
    contractors = (
        # _build_queryset(Contractor, site_ids, filters).order_by("-check_in")
         _build_queryset(Contractor, site_ids, filters).order_by("-sort_at")
        if "Contractor" in kinds
        else Contractor.objects.none()
    )

    total = visitors.count() + contractors.count()

    page = filters.get("page")
    page_size = filters.get("page_size")

    # no paging requested -> everything (export)
    if not page or not page_size:
        merged = sorted(
            chain(
                (("Visitor", o) for o in visitors),
                (("Contractor", o) for o in contractors),
            ),
            # key=lambda x: x[1].check_in,
            key=lambda x: x[1].sort_at,
            reverse=True,
        )
        rows = [_row(k, o) for k, o in merged]
        return rows, {
            "total_records": total,
            "total_pages": 1,
            "page": 1,
            "page_size": total,
        }

    page = max(1, page)
    page_size = max(1, page_size)
    offset = (page - 1) * page_size
    limit = offset + page_size

    # take the newest `limit` rows from each table, merge, then cut the page
    # merged = sorted(
    #     chain(
    #         (("Visitor", o) for o in visitors[:limit]),
    #         (("Contractor", o) for o in contractors[:limit]),
    #     ),
    #     key=lambda x: x[1].check_in,
    #     reverse=True,
    # )[offset:limit]
    merged = sorted(
        chain(
            (("Visitor", o) for o in visitors[:limit]),
            (("Contractor", o) for o in contractors[:limit]),
        ),
        key=lambda x: x[1].sort_at,
        reverse=True,
    )[offset:limit]

    rows = [_row(k, o) for k, o in merged]
    return rows, {
        "total_records": total,
        "total_pages": max(1, ceil(total / page_size)),
        "page": page,
        "page_size": page_size,
    }