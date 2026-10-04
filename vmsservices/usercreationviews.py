from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    UserCreateSerializer,
    UserDeleteSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)
from .usercreationservices import (
    create_system_user,
    delete_system_user,
    list_system_users,
    update_system_user,
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


# create and update accept multipart/form-data because of the photo upload
@extend_schema(
    tags=["User"],
    summary="Create user",
    request={"multipart/form-data": UserCreateSerializer},
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def user_create_api(request):
    s = UserCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_system_user(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["User"],
    summary="Update user",
    request={"multipart/form-data": UserUpdateSerializer},
)
@api_view(["PUT"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def user_update_api(request):
    s = UserUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_system_user(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["User"], summary="Delete user", request=UserDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def user_delete_api(request):
    s = UserDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_system_user(
        user_id=s.validated_data["user_id"],
        user=request.user,
    )
    return _respond(result)


@extend_schema(tags=["User"], summary="List users", request=UserListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def user_list_api(request):
    s = UserListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_system_users(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
    )
    return _respond(result)