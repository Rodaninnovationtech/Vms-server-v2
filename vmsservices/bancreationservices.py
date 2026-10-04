from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Ban, Site, VisitorDetail
from .rolepermissionservices import can_view_subsites, user_can_view_site

BAN_MENU_KEY = "/ban"

TEMPORARY = "TEMPORARY"
PERMANENT = "PERMANENT"


def _fail(message, status_code=400):
    return {"success": False, "message": message, "status_code": status_code}


# ----------------------------------------------------------------------
# status (computed, never stored)
#   Lifted   : an admin lifted it (is_active = False)
#   Upcoming : temporary, starts in the future
#   Active   : permanent, or temporary and today is inside from..to
#   Expired  : temporary, to_date is in the past
# ----------------------------------------------------------------------

def _status(ban, today):
    if not ban.is_active:
        return "Lifted"
    if ban.ban_type == PERMANENT:
        return "Active"
    if ban.to_date < today:
        return "Expired"
    if ban.from_date > today:
        return "Upcoming"
    return "Active"


def _in_effect_q(today):
    return Q(is_active=True) & (
        Q(ban_type=PERMANENT) | Q(from_date__lte=today, to_date__gte=today)
    )


def _status_q(status, today):
    if status == "Lifted":
        return Q(is_active=False)
    live = Q(is_active=True)
    if status == "Active":
        return _in_effect_q(today)
    if status == "Upcoming":
        return live & Q(ban_type=TEMPORARY, from_date__gt=today)
    if status == "Expired":
        return live & Q(ban_type=TEMPORARY, to_date__lt=today)
    return Q()


# ----------------------------------------------------------------------
# used by the visitor check-in flow
# ----------------------------------------------------------------------

def is_person_banned(person, site=None):
    """True if the person has a ban in effect today.
    With a site: only bans at that site. Without: bans at any site."""
    qs = Ban.objects.filter(_in_effect_q(timezone.localdate()), person=person)
    if site is not None:
        qs = qs.filter(site=site)
    return qs.exists()


# ----------------------------------------------------------------------
# serializer
# ----------------------------------------------------------------------

def _serialize(ban, today):
    return {
        "guid": str(ban.guid),
        "id": ban.id,
        "person": {
            "id": ban.person.id,
            "person_name": ban.person.person_name,
            "identity_type": ban.person.identity_type,
            "identity_number": ban.person.identity_number,
            "phone_number": ban.person.phone_number,
            "email": ban.person.email,
        },
        "site": {
            "guid": str(ban.site.guid),
            "name": ban.site.site_name,
            "site_code": ban.site.site_code,
        },
        "ban_type": ban.ban_type,
        "from_date": ban.from_date,
        "to_date": ban.to_date,
        "reason": ban.reason or "",
        "is_active": ban.is_active,
        "status": _status(ban, today),
        "created_at": ban.created_at,
        "updated_at": ban.updated_at,
    }


# ----------------------------------------------------------------------
# permissions
# ----------------------------------------------------------------------

def _can_manage_site(user, site_obj):
    """Super admin: any site. Others: own site, or a sub-site they may view."""
    if user.is_super_admin():
        return True
    own = user.site
    if own is None:
        return False
    if own.pk == site_obj.pk:
        return True
    return user_can_view_site(user, BAN_MENU_KEY, str(site_obj.guid))


def _site_scope(user, site_guid):
    """Returns (Q for the site filter, error_dict_or_None). Same rules as visitors."""
    # include_children = True

    if user is not None and not user.is_super_admin():
        own = user.site

        if own is None:
            return None, _fail("No site is assigned to your account", 403)

        if not site_guid:
            site_guid = str(own.guid)

        if str(site_guid) != str(own.guid) and not user_can_view_site(
            user, BAN_MENU_KEY, site_guid
        ):
            return None, _fail("You are not allowed to view this site", 403)

        include_children = can_view_subsites(user, BAN_MENU_KEY)

    # if not site_guid:
    #     return Q(), None

    # condition = Q(site__guid=site_guid)
    # if include_children:
    #     condition |= Q(site__parent__guid=site_guid)
    # return condition, None

    if not site_guid:
        return Q(), None

    return Q(site__guid=site_guid), None


# ----------------------------------------------------------------------
# overlap check: one person cannot have two live bans covering the same days
# at the same site
# ----------------------------------------------------------------------

def _overlapping(person, site, ban_type, from_date, to_date, exclude_pk=None):
    qs = Ban.objects.filter(person=person, site=site, is_active=True)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if ban_type == PERMANENT:
        # clashes with any permanent ban, or a temporary ban that has not ended
        return qs.filter(Q(ban_type=PERMANENT) | Q(to_date__gte=timezone.localdate()))

    return qs.filter(
        Q(ban_type=PERMANENT) | Q(from_date__lte=to_date, to_date__gte=from_date)
    )


# ----------------------------------------------------------------------
# list
# ----------------------------------------------------------------------

def list_bans(
    page=None,
    page_size=None,
    search="",
    site_guid=None,
    ban_type="",
    status="",
    from_date=None,
    to_date=None,
    user=None,
):
    scope_q, error = _site_scope(user, site_guid)
    if error:
        return error

    today = timezone.localdate()

    qs = (
        Ban.objects
        .select_related("person", "site")
        .filter(scope_q)
    )

    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(person__person_name__icontains=search)
            | Q(person__phone_number__icontains=search)
            | Q(person__email__icontains=search)
            | Q(person__identity_type__icontains=search)
            | Q(person__identity_number__icontains=search)
        )

    if ban_type:
        qs = qs.filter(ban_type=ban_type)

    if status:
        qs = qs.filter(_status_q(status, today))

    # Overlap with the filter range. A null date means "no limit" (permanent).
    if from_date:
        qs = qs.filter(Q(to_date__isnull=True) | Q(to_date__gte=from_date))
    if to_date:
        qs = qs.filter(Q(from_date__isnull=True) | Q(from_date__lte=to_date))

    qs = qs.order_by("-created_at", "-id")

    if page is None and page_size is None:
        return {
            "success": True,
            "message": "Bans fetched",
            "data": {"results": [_serialize(b, today) for b in qs]},
        }

    page = page or 1
    page_size = page_size or 10
    paginator = Paginator(qs, page_size)

    if page > paginator.num_pages and paginator.num_pages > 0:
        return _fail("Page number out of range", 404)

    page_obj = paginator.page(page)

    return {
        "success": True,
        "message": "Bans fetched",
        "data": {
            "results": [_serialize(b, today) for b in page_obj.object_list],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": paginator.count,
                "total_pages": paginator.num_pages,
            },
        },
    }


# ----------------------------------------------------------------------
# create (one ban row per selected site, all or nothing)
# ----------------------------------------------------------------------

def create_bans(user, person_id, sites, ban_type, from_date, to_date, reason):
    person = VisitorDetail.objects.filter(pk=person_id).first()
    if person is None:
        return _fail("Selected person not found", 404)

    site_objs = list(Site.objects.filter(guid__in=sites))
    if len(site_objs) != len(sites):
        return _fail("One or more selected sites do not exist")

    for s in site_objs:
        if not _can_manage_site(user, s):
            return _fail(f"You are not allowed to ban at {s.site_name}", 403)

    with transaction.atomic():
        # serialise concurrent bans for the same person
        VisitorDetail.objects.select_for_update().filter(pk=person.pk).first()

        clashes = [
            s.site_name
            for s in site_objs
            if _overlapping(person, s, ban_type, from_date, to_date).exists()
        ]
        if clashes:
            return _fail(
                "Already banned for these dates at: " + ", ".join(clashes), 409
            )

        created = [
            Ban.objects.create(
                person=person,
                site=s,
                ban_type=ban_type,
                from_date=from_date,
                to_date=to_date,
                reason=reason.strip(),
                created_by=user,
                updated_by=user,
            )
            for s in site_objs
        ]

    today = timezone.localdate()
    return {
        "success": True,
        "message": "Ban created",
        "data": {"results": [_serialize(b, today) for b in created]},
    }


# ----------------------------------------------------------------------
# update
# ----------------------------------------------------------------------

def update_ban(user, guid, site, ban_type, from_date, to_date, reason, is_active=None):
    new_site = Site.objects.filter(guid=site).first()
    if new_site is None:
        return _fail("Selected site does not exist")

    with transaction.atomic():
        ban = (
            Ban.objects.select_for_update(of=("self",))
            .select_related("person", "site")
            .filter(guid=guid)
            .first()
        )
        if ban is None:
            return _fail("Ban not found", 404)

        if not _can_manage_site(user, ban.site) or not _can_manage_site(user, new_site):
            return _fail("You are not allowed to change bans at this site", 403)

        will_be_active = ban.is_active if is_active is None else is_active

        if will_be_active and _overlapping(
            ban.person, new_site, ban_type, from_date, to_date, exclude_pk=ban.pk
        ).exists():
            return _fail(
                f"This person already has a ban at {new_site.site_name} for these dates",
                409,
            )

        ban.site = new_site
        ban.ban_type = ban_type
        ban.from_date = from_date
        ban.to_date = to_date
        ban.reason = reason.strip()
        ban.is_active = will_be_active
        ban.updated_by = user
        ban.save()

    return {
        "success": True,
        "message": "Ban updated",
        "data": _serialize(ban, timezone.localdate()),
    }


# ----------------------------------------------------------------------
# lift (keeps the record, switches the ban off)
# ----------------------------------------------------------------------

def lift_ban(user, guid):
    with transaction.atomic():
        ban = (
            Ban.objects.select_for_update(of=("self",))
            .select_related("person", "site")
            .filter(guid=guid)
            .first()
        )
        if ban is None:
            return _fail("Ban not found", 404)

        if not _can_manage_site(user, ban.site):
            return _fail("You are not allowed to change bans at this site", 403)

        if not ban.is_active:
            return _fail("This ban is already lifted", 409)

        ban.is_active = False
        ban.updated_by = user
        ban.save()

    return {
        "success": True,
        "message": "Ban lifted",
        "data": _serialize(ban, timezone.localdate()),
    }


# ----------------------------------------------------------------------
# delete
# ----------------------------------------------------------------------

def delete_ban(user, guid):
    ban = Ban.objects.select_related("site").filter(guid=guid).first()
    if ban is None:
        return _fail("Ban not found", 404)

    if not _can_manage_site(user, ban.site):
        return _fail("You are not allowed to delete bans at this site", 403)

    ban.delete()
    return {"success": True, "message": "Ban deleted"}