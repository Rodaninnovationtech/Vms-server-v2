from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import CharField, Count, F, Q, Value
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Ban, Contractor, Key, Pass, Site, Tenant, Visitor
from .rolepermissionservices import can_view_subsites, user_can_view_site
from .sitecreationservices import PARENT_SITE_MODEL_NAME

SITE_MENU_KEY = "/system-config/site"
DEFAULT_RANGE_DAYS = 30
MAX_RANGE_DAYS = 366
MAX_PAGE_SIZE = 100

VISIT_MODELS = {"Visitor": Visitor, "Contractor": Contractor}


def _error(message, status_code=400):
    return {"success": False, "message": message, "status_code": status_code}


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

def _scope_sites(user, site_guid):
    """Sites the dashboard should cover.

    Super admin : no site_guid = every site; a site_guid = that site + its sub-sites.
    Normal user : own site by default; another site only if they may view it.
                  Sub-sites are included only when "view" is true for the site menu
                  (same rule as list_sites).
    Returns (Site queryset, error_dict_or_None).
    """
    qs = Site.objects.all()
    include_children = True

    if user is not None and not user.is_super_admin():
        own = user.site

        if own is None:
            return None, _error("No site is assigned to your account", 403)

        if not site_guid:
            site_guid = str(own.guid)

        if str(site_guid) != str(own.guid) and not user_can_view_site(
            user, SITE_MENU_KEY, site_guid
        ):
            return None, _error("You are not allowed to view this site", 403)

        include_children = can_view_subsites(user, SITE_MENU_KEY)

    # if site_guid:
    #     condition = Q(guid=site_guid)
    #     if include_children:
    #         condition |= Q(parent__guid=site_guid)
    #     qs = qs.filter(condition)


    if site_guid:
       qs = qs.filter(guid=site_guid)
    return qs, None


def _resolve_range(from_date, to_date):
    """Missing dates default to the last 30 days. Returns (start, end, error)."""
    today = timezone.localdate()

    if to_date is None:
        to_date = max(today, from_date) if from_date else today
    if from_date is None:
        from_date = to_date - timedelta(days=DEFAULT_RANGE_DAYS - 1)

    if (to_date - from_date).days >= MAX_RANGE_DAYS:
        return None, None, _error(
            f"Date range cannot be longer than {MAX_RANGE_DAYS} days"
        )

    return from_date, to_date, None


def _daily_counts(model, field, site_ids, start, end):
    """{date: count} of rows whose `field` (check_in / check_out) falls on that day."""
    rows = (
        model.objects
        .filter(
            site_id__in=site_ids,
            **{f"{field}__date__gte": start, f"{field}__date__lte": end},
        )
        .order_by()  # drop Meta ordering, otherwise GROUP BY breaks
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(total=Count("id"))
    )
    return {r["day"]: r["total"] for r in rows}


def _not_checked_out_qs(model, site_ids, start, end):
    """Checked in during the range but never checked out."""
    return model.objects.filter(
        site_id__in=site_ids,
        check_in__isnull=False,
        check_out__isnull=True,
        check_in__date__gte=start,
        check_in__date__lte=end,
    )


# ---------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------

def get_dashboard_summary(user, site_guid=None, from_date=None, to_date=None):

    scope, error = _scope_sites(user, site_guid)
    if error:
        return error

    start, end, error = _resolve_range(from_date, to_date)
    if error:
        return error

    site_ids = list(scope.values_list("id", flat=True))
    today = timezone.localdate()

    # ---- site counts (parent / sub-site / individual) ----
    # is_parent_model = Q(site_model__site_model__iexact=PARENT_SITE_MODEL_NAME)
    # site_counts = scope.aggregate(
    #     parent=Count("id", filter=is_parent_model),
    #     sub=Count("id", filter=Q(parent__isnull=False) & ~is_parent_model),
    #     individual=Count("id", filter=Q(parent__isnull=True) & ~is_parent_model),
    # )

        # ---- site counts (parent / sub-site / individual) ----
    is_parent_model = Q(site_model__site_model__iexact=PARENT_SITE_MODEL_NAME)
    raw_counts = scope.aggregate(
        parent_total=Count("id", filter=is_parent_model),
        sub_total=Count("id", filter=Q(parent__isnull=False) & ~is_parent_model),
        individual_total=Count("id", filter=Q(parent__isnull=True) & ~is_parent_model),
    )
    site_counts = {
        "parent": raw_counts["parent_total"],
        "sub": raw_counts["sub_total"],
        "individual": raw_counts["individual_total"],
    }
    # ---- passes / keys / tenants / banned persons (site based, not date based) ----
    banned = (
        Ban.objects
        .filter(site_id__in=site_ids, is_active=True)
        .filter(
            Q(ban_type="PERMANENT")
            | Q(from_date__lte=today, to_date__gte=today)
        )
        .aggregate(n=Count("person_id", distinct=True))["n"]
    )

    totals = {
        "passes": Pass.objects.filter(site_id__in=site_ids).count(),
        "keys": Key.objects.filter(site_id__in=site_ids).count(),
        "tenants": Tenant.objects.filter(site_id__in=site_ids).count(),
        "banned": banned,
    }

    # ---- check-in / check-out per day ----
    v_in = _daily_counts(Visitor, "check_in", site_ids, start, end)
    v_out = _daily_counts(Visitor, "check_out", site_ids, start, end)
    c_in = _daily_counts(Contractor, "check_in", site_ids, start, end)
    c_out = _daily_counts(Contractor, "check_out", site_ids, start, end)

    daily = []
    day = start
    while day <= end:
        daily.append({
            "date": day.isoformat(),
            "visitor_check_in": v_in.get(day, 0),
            "visitor_check_out": v_out.get(day, 0),
            "contractor_check_in": c_in.get(day, 0),
            "contractor_check_out": c_out.get(day, 0),
        })
        day += timedelta(days=1)

    activity = {
        "visitor_check_in": sum(v_in.values()),
        "visitor_check_out": sum(v_out.values()),
        "contractor_check_in": sum(c_in.values()),
        "contractor_check_out": sum(c_out.values()),
        "visitor_not_checked_out": _not_checked_out_qs(Visitor, site_ids, start, end).count(),
        "contractor_not_checked_out": _not_checked_out_qs(Contractor, site_ids, start, end).count(),
    }

    return {
        "success": True,
        "message": "Dashboard fetched",
        "data": {
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "sites": site_counts,
            "totals": totals,
            "activity": activity,
            "daily": daily,
        },
    }


# ---------------------------------------------------------------------
# list of people who have not checked out
# ---------------------------------------------------------------------

def _pending_rows(kind, model, site_ids, start, end, search):
    qs = _not_checked_out_qs(model, site_ids, start, end)

    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(person__person_name__icontains=search)
            | Q(person__identity_number__icontains=search)
            | Q(person__phone_number__icontains=search)
            | Q(company__icontains=search)
            | Q(tenant__tenant_name__icontains=search)
            | Q(pass_no__icontains=search)
        )

    return (
        qs.order_by()
        .annotate(
            kind=Value(kind, output_field=CharField()),
            person_name=F("person__person_name"),
            identity_number=F("person__identity_number"),
            phone_number=F("person__phone_number"),
            site_name=F("site__site_name"),
            location=F("tenant__tenant_name"),
        )
        .values(
            "guid", "kind", "person_name", "identity_number", "phone_number",
            "company", "site_name", "location", "pass_no", "key_no", "check_in",
        )
    )


def list_not_checked_out(
    user,
    page=None,
    page_size=None,
    search="",
    site_guid=None,
    kind="",
    from_date=None,
    to_date=None,
):

    scope, error = _scope_sites(user, site_guid)
    if error:
        return error

    start, end, error = _resolve_range(from_date, to_date)
    if error:
        return error

    site_ids = list(scope.values_list("id", flat=True))

    parts = [
        _pending_rows(k, m, site_ids, start, end, search)
        for k, m in VISIT_MODELS.items()
        if not kind or kind == k
    ]

    qs = parts[0] if len(parts) == 1 else parts[0].union(parts[1], all=True)
    qs = qs.order_by("-check_in", "guid")

    page = page or 1
    page_size = min(page_size or 10, MAX_PAGE_SIZE)

    paginator = Paginator(qs, page_size)

    if page > paginator.num_pages and paginator.num_pages > 0:
        return _error("Page number out of range", 404)

    page_obj = paginator.page(page)

    results = [
        {**row, "guid": str(row["guid"])}
        for row in page_obj.object_list
    ]

    return {
        "success": True,
        "message": "Pending check-outs fetched",
        "data": {
            "results": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": paginator.count,
                "total_pages": paginator.num_pages,
            },
        },
    }