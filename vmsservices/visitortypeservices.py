from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import ProtectedError

from .models import VisitorType


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
    qs = VisitorType.objects.filter(name__iexact=name)

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _exists_error():
    return {
        "success": False,
        "message": "Visitor type already exists",
        "status_code": 409,
    }


def create_visitor_type(user, **fields):

    fields["name"] = fields["name"].strip()

    if _duplicate(fields["name"]):
        return _exists_error()

    try:
        obj = VisitorType.objects.create(
            created_by=user,
            updated_by=user,
            **fields,
        )
    except IntegrityError:
        return _exists_error()

    return {
        "success": True,
        "message": "Visitor type created",
        "data": _serialize(obj),
    }


def update_visitor_type(user, guid, **fields):

    obj = VisitorType.objects.filter(guid=guid).first()

    if obj is None:
        return {
            "success": False,
            "message": "Visitor type not found",
            "status_code": 404,
        }

    fields["name"] = fields["name"].strip()

    if _duplicate(fields["name"], exclude_pk=obj.pk):
        return _exists_error()

    for key, value in fields.items():
        setattr(obj, key, value)

    obj.updated_by = user

    try:
        obj.save()
    except IntegrityError:
        return _exists_error()

    return {
        "success": True,
        "message": "Visitor type updated",
        "data": _serialize(obj),
    }


def delete_visitor_type(guid):

    try:
        deleted, _ = VisitorType.objects.filter(guid=guid).delete()
    except ProtectedError:
        return {
            "success": False,
            "message": "Visitor type is in use and cannot be deleted",
            "status_code": 409,
        }

    if not deleted:
        return {
            "success": False,
            "message": "Visitor type not found",
            "status_code": 404,
        }

    return {"success": True, "message": "Visitor type deleted"}


def list_visitor_types(page=None, page_size=None, search=""):

    qs = (
        VisitorType.objects
        .select_related("created_by", "updated_by")
        .order_by("-created_at", "-id")
    )

    search = (search or "").strip()
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(description__icontains=search)

    if page is None and page_size is None:
        return {
            "success": True,
            "message": "Visitor types fetched",
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
        "message": "Visitor types fetched",
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