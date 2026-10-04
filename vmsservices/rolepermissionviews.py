from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    RolePermissionGetSerializer,
    RolePermissionSaveSerializer,
)
from .rolepermissionservices import (
    get_role_permissions,
    save_role_permissions,
    get_user_permissions,
)


def _invalid(serializer):
    return Response(
        {"success": False, "message": "Validation failed", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _respond(result, ok_status=status.HTTP_200_OK):
    if result["success"]:
        return Response(result, status=ok_status)
    code = result.pop("status_code", status.HTTP_400_BAD_REQUEST)
    return Response(result, status=code)


@extend_schema(
    tags=["Role Permission"],
    summary="Get permissions of a role",
    request=RolePermissionGetSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def role_permission_get_api(request):
    s = RolePermissionGetSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = get_role_permissions(role_guid=s.validated_data["role_guid"])
    return _respond(result)


@extend_schema(
    tags=["Role Permission"],
    summary="Save permissions of a role",
    request=RolePermissionSaveSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def role_permission_save_api(request):
    s = RolePermissionSaveSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = save_role_permissions(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Role Permission"],
    summary="Permissions of the logged-in user",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_permissions_api(request):
    result = get_user_permissions(request.user)
    return _respond(result)