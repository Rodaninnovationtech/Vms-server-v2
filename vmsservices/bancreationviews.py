from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    BanCreateSerializer,
    BanDeleteSerializer,
    BanLiftSerializer,
    BanListSerializer,
    BanUpdateSerializer,
)
from .bancreationservices import (
    create_bans,
    delete_ban,
    lift_ban,
    list_bans,
    update_ban,
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
    tags=["Ban"],
    summary="Ban a visitor / contractor at one or more sites",
    request=BanCreateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ban_create_api(request):
    s = BanCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_bans(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Ban"],
    summary="List bans",
    request=BanListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ban_list_api(request):
    s = BanListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_bans(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Ban"],
    summary="Update a ban",
    request=BanUpdateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ban_update_api(request):
    s = BanUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_ban(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Ban"],
    summary="Lift a ban",
    request=BanLiftSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ban_lift_api(request):
    s = BanLiftSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = lift_ban(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Ban"],
    summary="Delete a ban",
    request=BanDeleteSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ban_delete_api(request):
    s = BanDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_ban(user=request.user, **s.validated_data)
    return _respond(result)