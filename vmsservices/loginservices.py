from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import LoginHistory
from .rolepermissionservices import get_user_permissions


def get_logo_url(user, is_super_admin):
    """Super admin -> fixed logo. Others -> their site's image."""
    if is_super_admin:
        return f"{settings.MEDIA_URL}{settings.SUPER_ADMIN_LOGO}"
    if user.site and user.site.site_image:
        return user.site.site_image.url
    return None

def login_user(login_id, password, ip_address=None, user_agent=""):
    user = authenticate(
        username=login_id,
        password=password
    )

    if user is None:
        return {
            "success": False,
            "message": "Invalid login ID or password"
        }

    if not user.is_active:
        return {
            "success": False,
            "message": "User account is inactive"
        }

    refresh = RefreshToken.for_user(user)

    LoginHistory.objects.create(
        user=user,
        login_id=user.login_id,
        refresh_jti=refresh["jti"],
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    permission_data = get_user_permissions(user)["data"]
    is_super_admin = permission_data["is_super_admin"]
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "user_id": user.id,
            "login_id": user.login_id,
            "email": user.email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
            "gender": user.gender,
            "profile_photo": user.profile_photo.url if user.profile_photo else None,
            "role": user.role.name if user.role else None,
            # "site": user.site.site_name if user.site else None,
            "site": user.site.site_name if user.site else None,
            "site_detail": permission_data.get("site"),
            "subsites": permission_data.get("subsites", []),
            "is_super_admin": permission_data["is_super_admin"],
            "site_logo": get_logo_url(user, is_super_admin),
            "permissions": permission_data["permissions"],
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
    }