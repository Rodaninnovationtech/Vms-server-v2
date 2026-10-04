# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.exceptions import TokenError


# def logout_user(refresh_token):

#     if not refresh_token:
#         return {
#             "success": False,
#             "message": "Refresh token is required"
#         }

#     try:
#         token = RefreshToken(refresh_token)

#         token.blacklist()

#         return {
#             "success": True,
#             "message": "Logout successful"
#         }

#     except TokenError:
#         return {
#             "success": False,
#             "message": "Invalid or expired refresh token"
#         }

#     except Exception:
#         return {
#             "success": False,
#             "message": "Logout failed"
#         }


from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import LoginHistory


def logout_user(refresh_token, user):

    if not refresh_token:
        return {
            "success": False,
            "message": "Refresh token is required"
        }

    try:
        token = RefreshToken(refresh_token)

        # a user can only log out their own session
        if str(token["user_id"]) != str(user.id):
            return {
                "success": False,
                "message": "Invalid or expired refresh token"
            }

        jti = token["jti"]
        token.blacklist()

        LoginHistory.objects.filter(
            refresh_jti=jti, logout_at__isnull=True
        ).update(logout_at=timezone.now())

        return {
            "success": True,
            "message": "Logout successful"
        }

    except TokenError:
        return {
            "success": False,
            "message": "Invalid or expired refresh token"
        }

    except Exception:
        return {
            "success": False,
            "message": "Logout failed"
        }