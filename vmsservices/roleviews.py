from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    RoleCreateSerializer,
    RoleDeleteSerializer,
    RoleListSerializer,
    RoleUpdateSerializer,
)
from .roleservices import (
    create_role,
    delete_role,
    list_roles,
    update_role,
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


@extend_schema(tags=["Role"], summary="Create role", request=RoleCreateSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def role_create_api(request):
    s = RoleCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_role(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Role"], summary="Update role", request=RoleUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def role_update_api(request):
    s = RoleUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_role(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Role"], summary="Delete role", request=RoleDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def role_delete_api(request):
    s = RoleDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_role(guid=s.validated_data["guid"])
    return _respond(result)


@extend_schema(tags=["Role"], summary="List roles", request=RoleListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def role_list_api(request):
    s = RoleListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_roles(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
    )
    return _respond(result)