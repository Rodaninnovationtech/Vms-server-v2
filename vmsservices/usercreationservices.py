from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q

from .models import Role, Site, User


def _serialize(obj):
    return {
        "id": obj.id,
        "login_id": obj.login_id,
        "first_name": obj.first_name,
        "last_name": obj.last_name,
        "full_name": f"{obj.first_name} {obj.last_name}".strip(),
        "email": obj.email,
        "job_title": obj.job_title,
        "gender": obj.gender,
        "role": {
            "guid": str(obj.role.guid),
            "name": obj.role.name,
        } if obj.role_id else None,
        "site": {
            "guid": str(obj.site.guid),
            "name": obj.site.site_name,
        } if obj.site_id else None,
        # relative URL, e.g. /media/user_photos/2026/09/x.jpg
        "profile_photo": obj.profile_photo.url if obj.profile_photo else None,
        "is_active": obj.is_active,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _duplicate_login(login_id, exclude_pk=None):
    qs = User.objects.filter(login_id__iexact=login_id)

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _duplicate_email(email, exclude_pk=None):
    qs = User.objects.filter(email__iexact=email)

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


def _resolve_role(role_guid, current_role_id=None):
    role_obj = Role.objects.filter(guid=role_guid).first()

    if role_obj is None:
        return None, {
            "success": False,
            "message": "Selected role does not exist",
            "status_code": 400,
        }

    # An inactive role can only be kept, not newly assigned.
    if not role_obj.is_active and role_obj.pk != current_role_id:
        return None, {
            "success": False,
            "message": "Selected role is inactive",
            "status_code": 400,
        }

    return role_obj, None


def _resolve_site(site_guid):
    if not site_guid:
        return None, None

    site_obj = Site.objects.filter(guid=site_guid).first()

    if site_obj is None:
        return None, {
            "success": False,
            "message": "Selected site does not exist",
            "status_code": 400,
        }

    return site_obj, None


def create_system_user(
    login_id,
    password,
    email,
    role,
    user,
    first_name="",
    last_name="",
    job_title="",
    gender="",
    site=None,
    is_active=True,
    profile_photo=None,
):

    if _duplicate_login(login_id):
        return {
            "success": False,
            "message": "Login ID already exists",
            "status_code": 409,
        }

    if _duplicate_email(email):
        return {
            "success": False,
            "message": "Email already exists",
            "status_code": 409,
        }

    role_obj, error = _resolve_role(role)
    if error:
        return error

    site_obj, error = _resolve_site(site)
    if error:
        return error

    try:
        # create_user hashes the password, so this user can log in right away.
        # is_staff / is_superuser are never set here: created users are
        # always normal (role based) users.
        obj = User.objects.create_user(
            login_id=login_id,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            job_title=job_title,
            gender=gender,
            role=role_obj,
            site=site_obj,
            is_active=is_active,
            profile_photo=profile_photo,
        )
    except IntegrityError:
        return {
            "success": False,
            "message": "Login ID or email already exists",
            "status_code": 409,
        }

    return {
        "success": True,
        "message": "User created",
        "data": _serialize(obj),
    }


def update_system_user(
    user_id,
    login_id,
    email,
    role,
    user,
    first_name="",
    last_name="",
    job_title="",
    gender="",
    site=None,
    is_active=True,
    password="",
    profile_photo=None,
):

    # Super admins are not managed from this screen.
    obj = User.objects.filter(pk=user_id, is_superuser=False).first()

    if obj is None:
        return {
            "success": False,
            "message": "User not found",
            "status_code": 404,
        }

    if obj.pk == user.pk and not is_active:
        return {
            "success": False,
            "message": "You cannot deactivate your own account",
            "status_code": 400,
        }

    if _duplicate_login(login_id, exclude_pk=obj.pk):
        return {
            "success": False,
            "message": "Login ID already exists",
            "status_code": 409,
        }

    if _duplicate_email(email, exclude_pk=obj.pk):
        return {
            "success": False,
            "message": "Email already exists",
            "status_code": 409,
        }

    role_obj, error = _resolve_role(role, current_role_id=obj.role_id)
    if error:
        return error

    site_obj, error = _resolve_site(site)
    if error:
        return error

    obj.login_id = login_id
    obj.email = User.objects.normalize_email(email)
    obj.first_name = first_name
    obj.last_name = last_name
    obj.job_title = job_title
    obj.gender = gender
    obj.role = role_obj
    obj.site = site_obj
    obj.is_active = is_active

    # Only change the password when a new one was typed.
    if password:
        obj.set_password(password)

    # Only replace the photo when a new one was uploaded.
    if profile_photo:
        if obj.profile_photo:
            obj.profile_photo.delete(save=False)  # remove old file from disk
        obj.profile_photo = profile_photo

    try:
        obj.save()
    except IntegrityError:
        return {
            "success": False,
            "message": "Login ID or email already exists",
            "status_code": 409,
        }

    return {
        "success": True,
        "message": "User updated",
        "data": _serialize(obj),
    }


def delete_system_user(user_id, user):

    obj = User.objects.filter(pk=user_id, is_superuser=False).first()

    if obj is None:
        return {
            "success": False,
            "message": "User not found",
            "status_code": 404,
        }

    if obj.pk == user.pk:
        return {
            "success": False,
            "message": "You cannot delete your own account",
            "status_code": 400,
        }

    photo = obj.profile_photo
    obj.delete()

    # Clean the uploaded file off disk after the row is gone.
    if photo:
        photo.delete(save=False)

    return {
        "success": True,
        "message": "User deleted",
    }


def list_system_users(page=None, page_size=None, search=""):

    qs = (
        User.objects
        .filter(is_superuser=False)
        .select_related("role", "site")
        .order_by("-created_at", "-id")
    )

    search = (search or "").strip()
    if search:
        qs = qs.filter(
            Q(login_id__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )

    # --------------------------------
    # FULL DATA
    # --------------------------------
    if page is None and page_size is None:

        return {
            "success": True,
            "message": "Users fetched",
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
        "message": "Users fetched",
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