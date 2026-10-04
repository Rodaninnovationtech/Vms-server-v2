from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .keycreationservices import create_keys, delete_key, list_keys, update_key
from .serializers import (
    KeyCreateSerializer,
    KeyDeleteSerializer,
    KeyListSerializer,
    KeyUpdateSerializer,
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


# @extend_schema(tags=["Key"], summary="Create key", request=KeyCreateSerializer)
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def key_create_api(request):
#     s = KeyCreateSerializer(data=request.data)
#     if not s.is_valid():
#         return _invalid(s)
#     result = create_key(user=request.user, **s.validated_data)
#     return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Key"],
    summary="Create keys (bulk)",
    request=KeyCreateSerializer(many=True),
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def key_create_api(request):
    data = request.data
    if isinstance(data, dict):          
        data = [data]

    s = KeyCreateSerializer(data=data, many=True, allow_empty=False)
    if not s.is_valid():
        return _invalid(s)

    result = create_keys(items=s.validated_data, user=request.user)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Key"], summary="Update key", request=KeyUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def key_update_api(request):
    s = KeyUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_key(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Key"], summary="Delete key", request=KeyDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def key_delete_api(request):
    s = KeyDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_key(guid=s.validated_data["guid"], user=request.user)
    return _respond(result)


@extend_schema(tags=["Key"], summary="List keys", request=KeyListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def key_list_api(request):
    s = KeyListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_keys(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
        site_guid=s.validated_data.get("site_guid"),
        status=s.validated_data.get("status", ""),
        user=request.user,
    )
    return _respond(result)