# from django.core.paginator import Paginator
# from django.db import IntegrityError

# from .models import SiteType


# def _serialize(obj):
#     return {
#         "guid": str(obj.guid),
#         "site_type": obj.site_type,
#         "site_type_description": obj.site_type_description,
#         "created_by": obj.created_by.login_id if obj.created_by else None,
#         "created_at": obj.created_at,
#         "updated_by": obj.updated_by.login_id if obj.updated_by else None,
#         "updated_at": obj.updated_at,
#     }


# def _duplicate(site_type, exclude_pk=None):
#     qs = SiteType.objects.filter(
#         site_type__iexact=site_type
#     )

#     if exclude_pk:
#         qs = qs.exclude(pk=exclude_pk)

#     return qs.exists()


# def create_site_type(site_type, site_type_description, user):

#     if _duplicate(site_type):
#         return {
#             "success": False,
#             "message": "Site type already exists",
#             "status_code": 409,
#         }

#     try:
#         obj = SiteType.objects.create(
#             site_type=site_type,
#             site_type_description=site_type_description,
#             created_by=user,
#             updated_by=user,
#         )
#     except IntegrityError:
#         return {
#             "success": False,
#             "message": "Site type already exists",
#             "status_code": 409,
#         }

#     return {
#         "success": True,
#         "message": "Site type created",
#         "data": _serialize(obj),
#     }


# def update_site_type(guid, site_type, site_type_description, user):

#     obj = SiteType.objects.filter(guid=guid).first()

#     if obj is None:
#         return {
#             "success": False,
#             "message": "Site type not found",
#             "status_code": 404,
#         }

#     if _duplicate(site_type, exclude_pk=obj.pk):
#         return {
#             "success": False,
#             "message": "Site type already exists",
#             "status_code": 409,
#         }

#     obj.site_type = site_type
#     obj.site_type_description = site_type_description
#     obj.updated_by = user
#     obj.save()

#     return {
#         "success": True,
#         "message": "Site type updated",
#         "data": _serialize(obj),
#     }


# def delete_site_type(guid):

#     deleted, _ = SiteType.objects.filter(guid=guid).delete()

#     if not deleted:
#         return {
#             "success": False,
#             "message": "Site type not found",
#             "status_code": 404,
#         }

#     return {
#         "success": True,
#         "message": "Site type deleted",
#     }


# def list_site_types(page=None, page_size=None):

#     qs = (
#         SiteType.objects
#         .select_related("created_by", "updated_by")
#         .order_by("-created_at", "-id")
#     )

#     # --------------------------------
#     # FULL DATA
#     # --------------------------------
#     if page is None and page_size is None:

#         return {
#             "success": True,
#             "message": "Site types fetched",
#             "data": {
#                 "results": [
#                     _serialize(obj)
#                     for obj in qs
#                 ]
#             },
#         }

#     # --------------------------------
#     # PAGINATION
#     # --------------------------------
#     paginator = Paginator(qs, page_size)

#     if page > paginator.num_pages and paginator.num_pages > 0:
#         return {
#             "success": False,
#             "message": "Page number out of range",
#             "status_code": 404,
#         }

#     page_obj = paginator.page(page)

#     return {
#         "success": True,
#         "message": "Site types fetched",
#         "data": {
#             "results": [
#                 _serialize(obj)
#                 for obj in page_obj.object_list
#             ],
#             "pagination": {
#                 "page": page,
#                 "page_size": page_size,
#                 "total_records": paginator.count,
#                 "total_pages": paginator.num_pages,
#             },
#         },
#     }

from django.core.paginator import Paginator
from django.db import IntegrityError

from .models import SiteType


def _serialize(obj):
    return {
        "guid": str(obj.guid),
        "site_type": obj.site_type,
        "site_type_description": obj.site_type_description,
        "created_by": obj.created_by.login_id if obj.created_by else None,
        "created_at": obj.created_at,
        "updated_by": obj.updated_by.login_id if obj.updated_by else None,
        "updated_at": obj.updated_at,
    }


def _duplicate(site_type, exclude_pk=None):
    qs = SiteType.objects.filter(
        site_type__iexact=site_type
    )

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _duplicate_description(site_type_description, exclude_pk=None):
    # Blank descriptions are allowed to repeat (many site types can have no
    # description) — only a non-empty description is checked for duplicates.
    if not site_type_description or not site_type_description.strip():
        return False

    qs = SiteType.objects.filter(
        site_type_description__iexact=site_type_description.strip()
    )

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def create_site_type(site_type, site_type_description, user):

    if _duplicate(site_type):
        return {
            "success": False,
            "message": "Site type already exists",
            "status_code": 409,
        }

    if _duplicate_description(site_type_description):
        return {
            "success": False,
            "message": "This description is already used by another site type",
            "status_code": 409,
        }

    try:
        obj = SiteType.objects.create(
            site_type=site_type,
            site_type_description=site_type_description,
            created_by=user,
            updated_by=user,
        )
    except IntegrityError:
        return {
            "success": False,
            "message": "Site type already exists",
            "status_code": 409,
        }

    return {
        "success": True,
        "message": "Site type created",
        "data": _serialize(obj),
    }


def update_site_type(guid, site_type, site_type_description, user):

    obj = SiteType.objects.filter(guid=guid).first()

    if obj is None:
        return {
            "success": False,
            "message": "Site type not found",
            "status_code": 404,
        }

    if _duplicate(site_type, exclude_pk=obj.pk):
        return {
            "success": False,
            "message": "Site type already exists",
            "status_code": 409,
        }

    if _duplicate_description(site_type_description, exclude_pk=obj.pk):
        return {
            "success": False,
            "message": "This description is already used by another site type",
            "status_code": 409,
        }

    obj.site_type = site_type
    obj.site_type_description = site_type_description
    obj.updated_by = user
    obj.save()

    return {
        "success": True,
        "message": "Site type updated",
        "data": _serialize(obj),
    }


def delete_site_type(guid):

    deleted, _ = SiteType.objects.filter(guid=guid).delete()

    if not deleted:
        return {
            "success": False,
            "message": "Site type not found",
            "status_code": 404,
        }

    return {
        "success": True,
        "message": "Site type deleted",
    }


def list_site_types(page=None, page_size=None):

    qs = (
        SiteType.objects
        .select_related("created_by", "updated_by")
        .order_by("-created_at", "-id")
    )

    # --------------------------------
    # FULL DATA
    # --------------------------------
    if page is None and page_size is None:

        return {
            "success": True,
            "message": "Site types fetched",
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
        "message": "Site types fetched",
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