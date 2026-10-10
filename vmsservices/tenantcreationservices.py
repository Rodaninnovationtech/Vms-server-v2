from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q

from .models import Site, Tenant
# from .rolepermissionservices import can_view_subsites, user_can_view_site
from .rolepermissionservices import user_can_view_site

TENANT_MENU_KEY = "/system-config/tenant"


def _serialize(obj):
    return {
        "guid": str(obj.guid),
        "first_name": obj.first_name,
        "last_name": obj.last_name,
        "contact": obj.contact,
        "email": obj.email,
        "tenant_name": obj.tenant_name,
        "block": obj.block,
        "floor": obj.floor,
        "unit": obj.unit,
        # "site": {
        #     "guid": str(obj.site.guid),
        #     "name": obj.site.site_name,
        # },
        "site": {
            "guid": str(obj.site.guid),
            "name": obj.site.site_name,
            "site_code": obj.site.site_code,
            "site_model": {
                "guid": str(obj.site.site_model.guid),
                "name": obj.site.site_model.site_model,  # Parent site / Sub Site / Individual Site
            },
            "parent": {
                "guid": str(obj.site.parent.guid),
                "name": obj.site.parent.site_name,
            } if obj.site.parent_id else None,
        },
        "created_by": obj.created_by.login_id if obj.created_by else None,
        "created_at": obj.created_at,
        "updated_by": obj.updated_by.login_id if obj.updated_by else None,
        "updated_at": obj.updated_at,
    }


def _forbidden(message="You are not allowed to manage tenants of this site"):
    return {"success": False, "message": message, "status_code": 403}


def _can_manage_site(user, site_obj):
    """Super admin: any site. Others: only their own site (not sub-sites)."""
    if user.is_super_admin():
        return True
    return user.site_id is not None and user.site_id == site_obj.pk


def _resolve_site(site_guid, user):
    site_obj = Site.objects.filter(guid=site_guid).first()

    if site_obj is None:
        return None, {
            "success": False,
            "message": "Selected site does not exist",
            "status_code": 400,
        }

    if not _can_manage_site(user, site_obj):
        return None, _forbidden()

    return site_obj, None


# def create_tenant(
#     first_name, last_name, contact, email, tenant_name,
#     block, floor, unit, site, user,
# ):
#     site_obj, error = _resolve_site(site, user)
#     if error:
#         return error

#     obj = Tenant.objects.create(
#         first_name=first_name,
#         last_name=last_name,
#         contact=contact,
#         email=email,
#         tenant_name=tenant_name,
#         block=block,
#         floor=floor,
#         unit=unit,
#         site=site_obj,
#         created_by=user,
#         updated_by=user,
#     )

#     return {"success": True, "message": "Tenant created", "data": _serialize(obj)}

def create_tenants(items, user):
    """items = list of validated tenant dicts. All-or-nothing:
    if any row has a problem, nothing is saved and per-row errors are returned."""

    # resolve each distinct site only once
    site_cache = {}
    errors = []

    # for index, item in enumerate(items, start=1):
    #     key = str(item["site"])
    #     if key not in site_cache:
    #         site_cache[key] = _resolve_site(item["site"], user)

    #     site_obj, error = site_cache[key]
    #     if error:
    #         errors.append({"row": index, "message": error["message"]})

    seen = set()

    for index, item in enumerate(items, start=1):
        key = str(item["site"])
        if key not in site_cache:
            site_cache[key] = _resolve_site(item["site"], user)

        site_obj, error = site_cache[key]
        if error:
            errors.append({"row": index, "message": error["message"]})
            continue

        # duplicate = same email in the same site
        dup_key = (site_obj.pk, item["email"].strip().lower())
        if dup_key in seen:
            errors.append({"row": index, "message": "Duplicate of an earlier row in this file"})
        elif Tenant.objects.filter(
            site=site_obj, email__iexact=item["email"].strip()
        ).exists():
            errors.append({"row": index, "message": "Tenant with this email already exists in this site"})
        seen.add(dup_key)

    if errors:
        return {
            "success": False,
            "message": "Some rows could not be created",
            "errors": errors,          # [{row, message}]  (row is 1-based)
            "status_code": 400,
        }

    with transaction.atomic():
        created = [
            Tenant.objects.create(
                first_name=item["first_name"],
                last_name=item["last_name"],
                contact=item["contact"],
                email=item["email"],
                tenant_name=item["tenant_name"],
                block=item["block"],
                floor=item["floor"],
                unit=item["unit"],
                site=site_cache[str(item["site"])][0],
                created_by=user,
                updated_by=user,
            )
            for item in items
        ]

    return {
        "success": True,
        "message": f"{len(created)} tenant(s) created",
        "data": [_serialize(obj) for obj in created],
    }

def update_tenant(
    guid, first_name, last_name, contact, email, tenant_name,
    block, floor, unit, site, user,
):
    obj = Tenant.objects.select_related("site").filter(guid=guid).first()

    if obj is None:
        return {"success": False, "message": "Tenant not found", "status_code": 404}

    # the tenant must currently belong to the user's own site ...
    if not _can_manage_site(user, obj.site):
        return _forbidden()

    # ... and can only be moved to the user's own site
    site_obj, error = _resolve_site(site, user)
    if error:
        return error

    obj.first_name = first_name
    obj.last_name = last_name
    obj.contact = contact
    obj.email = email
    obj.tenant_name = tenant_name
    obj.block = block
    obj.floor = floor
    obj.unit = unit
    obj.site = site_obj
    obj.updated_by = user
    obj.save()

    return {"success": True, "message": "Tenant updated", "data": _serialize(obj)}


def delete_tenant(guid, user):
    obj = Tenant.objects.select_related("site").filter(guid=guid).first()

    if obj is None:
        return {"success": False, "message": "Tenant not found", "status_code": 404}

    if not _can_manage_site(user, obj.site):
        return _forbidden()

    obj.delete()

    return {"success": True, "message": "Tenant deleted"}


def list_tenants(page=None, page_size=None, search="", site_guid=None, user=None):

    qs = (
        Tenant.objects
        # .select_related("site", "created_by", "updated_by")
        .select_related(
            "site", "site__site_model", "site__parent",
            "created_by", "updated_by"
        )
        .order_by("-created_at", "-id")
    )

    # include_children = True  # super admin: unchanged behaviour

    if user is not None and not user.is_super_admin():
        own = user.site

        if own is None:
            return _forbidden("No site is assigned to your account")

        if not site_guid:
            site_guid = str(own.guid)

        if str(site_guid) != str(own.guid) and not user_can_view_site(
            user, TENANT_MENU_KEY, site_guid
        ):
            return _forbidden("You are not allowed to view this site")

        # Sub-site tenants are listed only when "view" is true for this menu
    #     include_children = can_view_subsites(user, TENANT_MENU_KEY)

    # if site_guid:
    #     condition = Q(site__guid=site_guid)
    #     if include_children:
    #         condition |= Q(site__parent__guid=site_guid)
    #     qs = qs.filter(condition)

    if site_guid:
        qs = qs.filter(site__guid=site_guid)

    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(tenant_name__icontains=search)
            | Q(email__icontains=search)
            | Q(contact__icontains=search)
        )

    if page is None and page_size is None:
        return {
            "success": True,
            "message": "Tenants fetched",
            "data": {"results": [_serialize(obj) for obj in qs]},
        }

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
        "message": "Tenants fetched",
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