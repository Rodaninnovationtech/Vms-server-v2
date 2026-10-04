from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q
from django.db.models.functions import Lower

from .models import Key, Site
# from .rolepermissionservices import can_view_subsites, user_can_view_site
from .rolepermissionservices import user_can_view_site

# must match the menu_key stored in RolePermission for the Key page
KEY_MENU_KEY = "/property-management/key"


def _serialize(obj):
    return {
        "guid": str(obj.guid),
        "key_no": obj.key_no,
        "key_name": obj.key_name,
        "status": obj.status,
        "site": {
            "guid": str(obj.site.guid),
            "name": obj.site.site_name,
            "site_code": obj.site.site_code,
        },
        "created_by": obj.created_by.login_id if obj.created_by else None,
        "created_at": obj.created_at,
        "updated_by": obj.updated_by.login_id if obj.updated_by else None,
        "updated_at": obj.updated_at,
    }


def _forbidden():
    return {
        "success": False,
        "message": "You are not allowed to manage keys for this site",
        "status_code": 403,
    }


def _can_access_site(user, site_obj):
    """Super admin: any site. Others: own site, or a sub-site they may view."""

    if user is None or user.is_super_admin():
        return True

    own = user.site
    if own is None:
        return False

    if site_obj.pk == own.pk:
        return True

    return user_can_view_site(user, KEY_MENU_KEY, str(site_obj.guid))


def _resolve_site(site_guid):
    site_obj = Site.objects.filter(guid=site_guid).first()

    if site_obj is None:
        return None, {
            "success": False,
            "message": "Selected site does not exist",
            "status_code": 400,
        }

    return site_obj, None


def _duplicate_key_no(site_obj, key_no, exclude_pk=None):
    qs = Key.objects.filter(site=site_obj, key_no__iexact=key_no)

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _duplicate_response():
    return {
        "success": False,
        "message": "Key number already exists for this site",
        "status_code": 409,
    }


# def create_key(key_no, key_name, site, user, status="Available"):

#     key_no = key_no.strip()
#     key_name = key_name.strip()

#     site_obj, error = _resolve_site(site)
#     if error:
#         return error

#     if not _can_access_site(user, site_obj):
#         return _forbidden()

#     if _duplicate_key_no(site_obj, key_no):
#         return _duplicate_response()

#     try:
#         obj = Key.objects.create(
#             key_no=key_no,
#             key_name=key_name,
#             site=site_obj,
#             status=status,
#             created_by=user,
#             updated_by=user,
#         )
#     except IntegrityError:
#         return _duplicate_response()

#     return {
#         "success": True,
#         "message": "Key created",
#         "data": _serialize(obj),
#     }


# def create_keys(items, user):
#     """Create many keys in one request. All-or-nothing."""

#     if not items:
#         return {
#             "success": False,
#             "message": "At least one key is required",
#             "status_code": 400,
#         }

#     site_cache = {}
#     seen = set()            # (site_pk, lower key_no) inside this request
#     prepared = []           # (row_no, site_obj, key_no, key_name, status)

#     for idx, item in enumerate(items, start=1):
#         key_no = item["key_no"].strip()
#         key_name = item["key_name"].strip()
#         status = item.get("status", "Available")
#         site_guid = str(item["site"])

#         if site_guid not in site_cache:
#             site_obj, error = _resolve_site(site_guid)
#             if error:
#                 error["message"] = f"Row {idx}: {error['message']}"
#                 return error
#             if not _can_access_site(user, site_obj):
#                 err = _forbidden()
#                 err["message"] = f"Row {idx}: {err['message']}"
#                 return err
#             site_cache[site_guid] = site_obj

#         site_obj = site_cache[site_guid]

#         marker = (site_obj.pk, key_no.lower())
#         if marker in seen:
#             return {
#                 "success": False,
#                 "message": f"Row {idx}: key number '{key_no}' is repeated in the request",
#                 "status_code": 409,
#             }
#         seen.add(marker)
#         prepared.append((idx, site_obj, key_no, key_name, status))

#     # duplicates already in the database (one query per site)
#     for site_obj in site_cache.values():
#         wanted = {k for (pk, k) in seen if pk == site_obj.pk}
#         existing = set(
#             Key.objects.filter(site=site_obj)
#             .annotate(k=Lower("key_no"))
#             .filter(k__in=wanted)
#             .values_list("k", flat=True)
#         )
#         if existing:
#             for idx, s, key_no, _n, _st in prepared:
#                 if s.pk == site_obj.pk and key_no.lower() in existing:
#                     return {
#                         "success": False,
#                         "message": f"Row {idx}: key number '{key_no}' already exists for this site",
#                         "status_code": 409,
#                     }

#     objs = [
#         Key(
#             key_no=key_no,
#             key_name=key_name,
#             site=site_obj,
#             status=status,
#             created_by=user,
#             updated_by=user,
#         )
#         for (_idx, site_obj, key_no, key_name, status) in prepared
#     ]

#     try:
#         with transaction.atomic():
#             Key.objects.bulk_create(objs)
#     except IntegrityError:
#         return _duplicate_response()

#     return {
#         "success": True,
#         "message": f"{len(objs)} key(s) created",
#         "data": {"results": [_serialize(o) for o in objs]},
#     }


def create_keys(items, user):
    """Create many keys in one request. All-or-nothing, but reports every bad row."""

    if not items:
        return {"success": False, "message": "At least one key is required", "status_code": 400}

    site_cache = {}
    seen = set()
    prepared = []
    errors = []

    def add_error(idx, key_no, message):
        errors.append({"row": idx, "key_no": key_no, "message": message})

    for idx, item in enumerate(items, start=1):
        key_no = item["key_no"].strip()
        key_name = item["key_name"].strip()
        status = item.get("status", "Available")
        site_guid = str(item["site"])

        if site_guid not in site_cache:
            site_obj, error = _resolve_site(site_guid)
            if error:
                error["message"] = f"Row {idx}: {error['message']}"
                return error
            if not _can_access_site(user, site_obj):
                err = _forbidden()
                err["message"] = f"Row {idx}: {err['message']}"
                return err
            site_cache[site_guid] = site_obj

        site_obj = site_cache[site_guid]

        marker = (site_obj.pk, key_no.lower())
        if marker in seen:
            add_error(idx, key_no, "Repeated in the file")
            continue
        seen.add(marker)
        prepared.append((idx, site_obj, key_no, key_name, status))

    # duplicates already in the database
    for site_obj in site_cache.values():
        wanted = {k for (pk, k) in seen if pk == site_obj.pk}
        existing = set(
            Key.objects.filter(site=site_obj)
            .annotate(k=Lower("key_no"))
            .filter(k__in=wanted)
            .values_list("k", flat=True)
        )
        if existing:
            for idx, s, key_no, _n, _st in prepared:
                if s.pk == site_obj.pk and key_no.lower() in existing:
                    add_error(idx, key_no, "Already exists for this site")

    if errors:
        errors.sort(key=lambda e: e["row"])
        return {
            "success": False,
            "message": f"{len(errors)} row(s) have errors",
            "errors": errors,
            "status_code": 409,
        }

    objs = [
        Key(
            key_no=key_no,
            key_name=key_name,
            site=site_obj,
            status=status,
            created_by=user,
            updated_by=user,
        )
        for (_idx, site_obj, key_no, key_name, status) in prepared
    ]

    try:
        with transaction.atomic():
            Key.objects.bulk_create(objs)
    except IntegrityError:
        return _duplicate_response()

    return {
        "success": True,
        "message": f"{len(objs)} key(s) created",
        "data": {"results": [_serialize(o) for o in objs]},
    }

def update_key(guid, key_no, key_name, site, user, status="Available"):

    obj = Key.objects.select_related("site").filter(guid=guid).first()

    if obj is None:
        return {
            "success": False,
            "message": "Key not found",
            "status_code": 404,
        }

    # the user must be allowed to touch the key's current site ...
    if not _can_access_site(user, obj.site):
        return _forbidden()

    key_no = key_no.strip()
    key_name = key_name.strip()

    site_obj, error = _resolve_site(site)
    if error:
        return error

    # ... and the site it is being moved to
    if not _can_access_site(user, site_obj):
        return _forbidden()

    if _duplicate_key_no(site_obj, key_no, exclude_pk=obj.pk):
        return _duplicate_response()

    obj.key_no = key_no
    obj.key_name = key_name
    obj.site = site_obj
    obj.status = status
    obj.updated_by = user

    try:
        obj.save()
    except IntegrityError:
        return _duplicate_response()

    return {
        "success": True,
        "message": "Key updated",
        "data": _serialize(obj),
    }


def delete_key(guid, user=None):

    obj = Key.objects.select_related("site").filter(guid=guid).first()

    if obj is None:
        return {
            "success": False,
            "message": "Key not found",
            "status_code": 404,
        }

    if not _can_access_site(user, obj.site):
        return _forbidden()

    try:
        obj.delete()
    except ProtectedError:
        return {
            "success": False,
            "message": "Key is in use and cannot be deleted",
            "status_code": 409,
        }

    return {
        "success": True,
        "message": "Key deleted",
    }


def list_keys(page=None, page_size=None, search="", site_guid=None, status="", user=None):

    qs = (
        Key.objects
        .select_related("site", "created_by", "updated_by")
        .order_by("-created_at", "-id")
    )

    # include_children = True  # super admin / no user: unchanged behaviour

    if user is not None and not user.is_super_admin():
        own = user.site

        if own is None:
            return {
                "success": False,
                "message": "No site is assigned to your account",
                "status_code": 403,
            }

        # default to the user's own site
        if not site_guid:
            site_guid = str(own.guid)

        if str(site_guid) != str(own.guid) and not user_can_view_site(
            user, KEY_MENU_KEY, site_guid
        ):
            return {
                "success": False,
                "message": "You are not allowed to view this site",
                "status_code": 403,
            }

        # keys of sub-sites are listed only when "view" is true for this menu
        # include_children = can_view_subsites(user, KEY_MENU_KEY)

    # if site_guid:
    #     condition = Q(site__guid=site_guid)
    #     if include_children:
    #         condition |= Q(site__parent__guid=site_guid)
    #     qs = qs.filter(condition)

    if site_guid:
        qs = qs.filter(site__guid=site_guid)

    if status:
        qs = qs.filter(status=status)

    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(key_no__icontains=search)
            | Q(key_name__icontains=search)
            | Q(site__site_name__icontains=search)
        )

    # --------------------------------
    # FULL DATA
    # --------------------------------
    if page is None and page_size is None:

        return {
            "success": True,
            "message": "Keys fetched",
            "data": {
                "results": [_serialize(obj) for obj in qs]
            },
        }

    # --------------------------------
    # PAGINATION
    # --------------------------------
    page = page or 1
    page_size = page_size or 10

    paginator = Paginator(qs, page_size)

    if page > paginator.num_pages and paginator.num_pages > 0:
        return {
            "success": False,
            "message": "Page number out of range",
            "status_code": 404,
        }

    page_obj = paginator.page(page)

    return {
        "success": True,
        "message": "Keys fetched",
        "data": {
            "results": [_serialize(obj) for obj in page_obj.object_list],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": paginator.count,
                "total_pages": paginator.num_pages,
            },
        },
    }