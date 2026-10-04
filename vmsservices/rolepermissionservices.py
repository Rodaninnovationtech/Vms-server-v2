from django.db import transaction

from .models import Role, RolePermission


def _serialize_rows(rows):
    return [
        {
            "menu_key": r.menu_key,
            "view": r.can_view_subsites,
            "enabled": r.menu_enabled,
        }
        for r in rows
    ]


def _site_brief(site):
    return {
        "id": site.id,
        "guid": str(site.guid),
        "site_code": site.site_code,
        "name": site.site_name,
    }


def get_user_site_data(user):
    """Own site + direct sub-sites (only when the user's site is a parent site)."""
    site = user.site

    if site is None:
        return None, []

    subsites = []
    if site.parent_id is None:
        subsites = [
            _site_brief(s)
            for s in site.subsites.order_by("site_name")
        ]

    return _site_brief(site), subsites


def _attach_subsites(permission_rows, subsites):
    for p in permission_rows:
        p["subsites"] = subsites if p["view"] else []
    return permission_rows


def get_role_permissions(role_guid):
    """Saved permissions of one role (used by the Role Permission page)."""

    role = Role.objects.filter(guid=role_guid).first()

    if role is None:
        return {
            "success": False,
            "message": "Role not found",
            "status_code": 404,
        }

    return {
        "success": True,
        "message": "Role permissions fetched",
        "data": {
            "role_guid": str(role.guid),
            "permissions": _serialize_rows(role.permissions.all()),
        },
    }


def save_role_permissions(role_guid, permissions, user):
    """Create or update one row per (role, menu_key)."""

    role = Role.objects.filter(guid=role_guid).first()

    if role is None:
        return {
            "success": False,
            "message": "Role not found",
            "status_code": 404,
        }

    with transaction.atomic():
        for item in permissions:
            RolePermission.objects.update_or_create(
                role=role,
                menu_key=item["menu_key"],
                defaults={
                    "menu_enabled": item["enabled"],
                    "can_view_subsites": item["view"],
                    "updated_by": user,
                },
            )

    return {
        "success": True,
        "message": "Permissions saved",
    }


def get_user_permissions(user):
    """Permissions of the logged-in user, based on user.role."""

    # Super admin sees everything, no rows needed.
    if user.is_super_admin():
        return {
            "success": True,
            "message": "Permissions fetched",
            "data": {
                "is_super_admin": True,
                "role": None,
                "site": None,
                "subsites": [],
                "permissions": [],
            },
        }

    role = user.role

    # No role, or role disabled: no access.
    if role is None or not role.is_active:
        return {
            "success": True,
            "message": "Permissions fetched",
            "data": {
                "is_super_admin": False,
                "role": role.name if role else None,
                "site": None,
                "subsites": [],
                "permissions": [],
            },
        }

    site_data, subsites = get_user_site_data(user)

    return {
        "success": True,
        "message": "Permissions fetched",
        "data": {
            "is_super_admin": False,
            "role": role.name,
            "site": site_data,
            "subsites": subsites,
            "permissions": _attach_subsites(
                _serialize_rows(role.permissions.all()), subsites
            ),
        },
    }


def can_view_subsites(user, menu_key):
    """
    Server-side check. Call this inside APIs (e.g. site list):

        if not can_view_subsites(user, "/system-config/site"):
            qs = qs.filter(parent__isnull=True)
    """

    if user.is_super_admin():
        return True

    if not user.role_id:
        return False

    if not user.role.is_active:
        return False

    return RolePermission.objects.filter(
        role_id=user.role_id,
        menu_key=menu_key,
        can_view_subsites=True,
    ).exists()


def user_can_view_site(user, menu_key, site_guid):
    """True if site_guid is one of the user's sub-sites and view is allowed."""
    if user.is_super_admin():
        return True

    if not can_view_subsites(user, menu_key):
        return False

    _, subsites = get_user_site_data(user)
    return str(site_guid) in {s["guid"] for s in subsites}