from datetime import date

from django.core.paginator import Paginator
from django.db.models import Q

from .models import Site, Tenant, TenantNotification
from .rolepermissionservices import user_can_view_site

TENANT_NOTIFICATION_MENU_KEY = "/system-config/tenant-notification"


def _status_for(from_date, to_date):
    today = date.today()
    if from_date > today:
        return "Upcoming"
    if to_date < today:
        return "Ended"
    return "Active"


def _serialize(obj):
    return {
        "guid": str(obj.guid),
        "site": {
            "guid": str(obj.site.guid),
            "name": obj.site.site_name,
        },
        "tenant": {
            "guid": str(obj.tenant.guid),
            "name": obj.tenant.tenant_name,
            # matches the "Name - Unit" style label used on the frontend table
            "location": f"{obj.tenant.tenant_name} - {obj.tenant.block}/{obj.tenant.floor}/{obj.tenant.unit}",
        },
        "from_date": obj.from_date.isoformat(),
        "to_date": obj.to_date.isoformat(),
        "message": obj.message,
        "status": _status_for(obj.from_date, obj.to_date),
        "created_by": obj.created_by.login_id if obj.created_by else None,
        "created_at": obj.created_at,
        "updated_by": obj.updated_by.login_id if obj.updated_by else None,
        "updated_at": obj.updated_at,
    }


def _forbidden(message="You are not allowed to manage notifications for this site"):
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


def _resolve_tenant(tenant_guid, site_obj):
    tenant_obj = Tenant.objects.filter(guid=tenant_guid, site=site_obj).first()

    if tenant_obj is None:
        return None, {
            "success": False,
            "message": "Selected location does not belong to the chosen site",
            "status_code": 400,
        }

    return tenant_obj, None


def create_tenant_notification(site, tenant, from_date, to_date, message, user):
    site_obj, error = _resolve_site(site, user)
    if error:
        return error

    tenant_obj, error = _resolve_tenant(tenant, site_obj)
    if error:
        return error

    obj = TenantNotification.objects.create(
        site=site_obj,
        tenant=tenant_obj,
        from_date=from_date,
        to_date=to_date,
        message=message,
        created_by=user,
        updated_by=user,
    )

    return {"success": True, "message": "Tenant notification created", "data": _serialize(obj)}


def update_tenant_notification(guid, site, tenant, from_date, to_date, message, user):
    obj = (
        TenantNotification.objects
        .select_related("site")
        .filter(guid=guid)
        .first()
    )

    if obj is None:
        return {"success": False, "message": "Tenant notification not found", "status_code": 404}

    # the notification must currently belong to a site the user can manage ...
    if not _can_manage_site(user, obj.site):
        return _forbidden()

    # ... and can only be moved to a site the user can manage
    site_obj, error = _resolve_site(site, user)
    if error:
        return error

    tenant_obj, error = _resolve_tenant(tenant, site_obj)
    if error:
        return error

    obj.site = site_obj
    obj.tenant = tenant_obj
    obj.from_date = from_date
    obj.to_date = to_date
    obj.message = message
    obj.updated_by = user
    obj.save()

    return {"success": True, "message": "Tenant notification updated", "data": _serialize(obj)}


def delete_tenant_notification(guid, user):
    obj = (
        TenantNotification.objects
        .select_related("site")
        .filter(guid=guid)
        .first()
    )

    if obj is None:
        return {"success": False, "message": "Tenant notification not found", "status_code": 404}

    if not _can_manage_site(user, obj.site):
        return _forbidden()

    obj.delete()

    return {"success": True, "message": "Tenant notification deleted"}


def list_tenant_notifications(page=None, page_size=None, search="", site_guid=None, user=None):

    qs = (
        TenantNotification.objects
        .select_related("site", "tenant", "created_by", "updated_by")
        .order_by("-created_at", "-id")
    )

    if user is not None and not user.is_super_admin():
        own = user.site

        if own is None:
            return _forbidden("No site is assigned to your account")

        if not site_guid:
            site_guid = str(own.guid)

        if str(site_guid) != str(own.guid) and not user_can_view_site(
            user, TENANT_NOTIFICATION_MENU_KEY, site_guid
        ):
            return _forbidden("You are not allowed to view this site")

    if site_guid:
        qs = qs.filter(site__guid=site_guid)

    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(tenant__tenant_name__icontains=search)
            | Q(site__site_name__icontains=search)
            | Q(message__icontains=search)
        )

    if page is None and page_size is None:
        return {
            "success": True,
            "message": "Tenant notifications fetched",
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
        "message": "Tenant notifications fetched",
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

def check_tenant_availability(tenant, from_date, to_date, user=None):
    try:
        tenant_obj = Tenant.objects.select_related("site").get(guid=tenant)
    except Tenant.DoesNotExist:
        return {
            "success": False,
            "message": "Location not found",
            "status_code": status.HTTP_404_NOT_FOUND,
        }

    overlapping = TenantNotification.objects.filter(
        tenant=tenant_obj,
        from_date__lte=to_date,
        to_date__gte=from_date,
    ).order_by("from_date")

    conflicts = [
        {"from_date": n.from_date.isoformat(), "to_date": n.to_date.isoformat(), "message": n.message}
        for n in overlapping
    ]
    is_available = len(conflicts) == 0

    return {
        "success": True,
        "message": "Available" if is_available else "Not available for the selected dates",
        "data": {"available": is_available, "conflicts": conflicts},
    }