from django.core.paginator import Paginator
from django.db import IntegrityError

from .models import IdentityType

NOT_REQUIRED = "Not Required"


def _serialize(obj):
    return {
        "guid": str(obj.guid),
        "identity_type_name": obj.identity_type_name,
        "identity_number_validation": obj.identity_number_validation,
        "identity_number_digits": obj.identity_number_digits,
        "identity_number_alphabets": obj.identity_number_alphabets,
        "identity_number_format": obj.identity_number_format,
        "phone_number_validation": obj.phone_number_validation,
        "phone_number_min": obj.phone_number_min,
        "phone_number_max": obj.phone_number_max,
        "phone_number_starting_with": obj.phone_number_starting_with,
        "phone_number_format": obj.phone_number_format,
        "created_by": obj.created_by.login_id if obj.created_by else None,
        "created_at": obj.created_at,
        "updated_by": obj.updated_by.login_id if obj.updated_by else None,
        "updated_at": obj.updated_at,
    }


def _duplicate(name, exclude_pk=None):
    qs = IdentityType.objects.filter(identity_type_name__iexact=name)

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _clean(fields):
    """'Not Required' means the related detail fields are not stored."""
    if fields["identity_number_validation"] == NOT_REQUIRED:
        fields["identity_number_digits"] = None
        fields["identity_number_alphabets"] = None
        fields["identity_number_format"] = ""

    if fields["phone_number_validation"] == NOT_REQUIRED:
        fields["phone_number_min"] = None
        fields["phone_number_max"] = None
        fields["phone_number_starting_with"] = ""
        fields["phone_number_format"] = ""

    return fields


def _exists_error():
    return {
        "success": False,
        "message": "Identity type already exists",
        "status_code": 409,
    }


def create_identity_type(user, **fields):

    if _duplicate(fields["identity_type_name"]):
        return _exists_error()

    try:
        obj = IdentityType.objects.create(
            created_by=user,
            updated_by=user,
            **_clean(fields),
        )
    except IntegrityError:
        return _exists_error()

    return {
        "success": True,
        "message": "Identity type created",
        "data": _serialize(obj),
    }


def update_identity_type(user, guid, **fields):

    obj = IdentityType.objects.filter(guid=guid).first()

    if obj is None:
        return {
            "success": False,
            "message": "Identity type not found",
            "status_code": 404,
        }

    if _duplicate(fields["identity_type_name"], exclude_pk=obj.pk):
        return _exists_error()

    for key, value in _clean(fields).items():
        setattr(obj, key, value)

    obj.updated_by = user

    try:
        obj.save()
    except IntegrityError:
        return _exists_error()

    return {
        "success": True,
        "message": "Identity type updated",
        "data": _serialize(obj),
    }


def delete_identity_type(guid):

    deleted, _ = IdentityType.objects.filter(guid=guid).delete()

    if not deleted:
        return {
            "success": False,
            "message": "Identity type not found",
            "status_code": 404,
        }

    return {"success": True, "message": "Identity type deleted"}


def list_identity_types(page=None, page_size=None, search=""):

    qs = (
        IdentityType.objects
        .select_related("created_by", "updated_by")
        .order_by("-created_at", "-id")
    )

    search = (search or "").strip()
    if search:
        qs = qs.filter(identity_type_name__icontains=search)

    if page is None and page_size is None:
        return {
            "success": True,
            "message": "Identity types fetched",
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
        "message": "Identity types fetched",
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