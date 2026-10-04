from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import ProtectedError
from .models import Role


def _serialize(obj):
    return {
        "guid": str(obj.guid),
        "name": obj.name,
        "description": obj.description,
        "is_active": obj.is_active,
        "created_by": obj.created_by.login_id if obj.created_by else None,
        "created_at": obj.created_at,
        "updated_by": obj.updated_by.login_id if obj.updated_by else None,
        "updated_at": obj.updated_at,
    }


def _duplicate(name, exclude_pk=None):
    qs = Role.objects.filter(name__iexact=name)

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _duplicate_description(description, exclude_pk=None):
    # Blank descriptions are allowed to repeat; only non-empty ones are checked.
    if not description or not description.strip():
        return False

    qs = Role.objects.filter(description__iexact=description.strip())

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def create_role(name, description, is_active, user):

    if _duplicate(name):
        return {
            "success": False,
            "message": "Role already exists",
            "status_code": 409,
        }

    if _duplicate_description(description):
        return {
            "success": False,
            "message": "This description is already used by another role",
            "status_code": 409,
        }

    try:
        obj = Role.objects.create(
            name=name,
            description=description,
            is_active=is_active,
            created_by=user,
            updated_by=user,
        )
    except IntegrityError:
        return {
            "success": False,
            "message": "Role already exists",
            "status_code": 409,
        }

    return {
        "success": True,
        "message": "Role created",
        "data": _serialize(obj),
    }


def update_role(guid, name, description, is_active, user):

    obj = Role.objects.filter(guid=guid).first()

    if obj is None:
        return {
            "success": False,
            "message": "Role not found",
            "status_code": 404,
        }

    if _duplicate(name, exclude_pk=obj.pk):
        return {
            "success": False,
            "message": "Role already exists",
            "status_code": 409,
        }

    if _duplicate_description(description, exclude_pk=obj.pk):
        return {
            "success": False,
            "message": "This description is already used by another role",
            "status_code": 409,
        }

    obj.name = name
    obj.description = description
    obj.is_active = is_active
    obj.updated_by = user
    obj.save()

    return {
        "success": True,
        "message": "Role updated",
        "data": _serialize(obj),
    }


def delete_role(guid):

    deleted, _ = Role.objects.filter(guid=guid).delete()

    if not deleted:
        return {
            "success": False,
            "message": "Role not found",
            "status_code": 404,
        }

    return {
        "success": True,
        "message": "Role deleted",
    }


def list_roles(page=None, page_size=None):

    qs = (
        Role.objects
        .select_related("created_by", "updated_by")
        .order_by("-created_at", "-id")
    )

    # --------------------------------
    # FULL DATA
    # --------------------------------
    if page is None and page_size is None:

        return {
            "success": True,
            "message": "Roles fetched",
            "data": {
                "results": [
                    _serialize(obj)
                    for obj in qs
                ]
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
        "message": "Roles fetched",
        "data": {
            "results": [
                _serialize(obj)
                for obj in page_obj.object_list
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": paginator.count,
                "total_pages": paginator.num_pages,
            },
        },
    }