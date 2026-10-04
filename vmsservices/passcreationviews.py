from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .passcreationservices import create_passes, delete_pass, list_passes, update_pass
from .serializers import (
    PassCreateSerializer,
    PassDeleteSerializer,
    PassListSerializer,
    PassUpdateSerializer,
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
    tags=["Pass"],
    summary="Create passes (bulk)",
    request=PassCreateSerializer(many=True),
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pass_create_api(request):
    data = request.data
    if isinstance(data, dict):
        data = [data]

    s = PassCreateSerializer(data=data, many=True, allow_empty=False)
    if not s.is_valid():
        return _invalid(s)

    result = create_passes(items=s.validated_data, user=request.user)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Pass"], summary="Update pass", request=PassUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def pass_update_api(request):
    s = PassUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_pass(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Pass"], summary="Delete pass", request=PassDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def pass_delete_api(request):
    s = PassDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_pass(guid=s.validated_data["guid"], user=request.user)
    return _respond(result)


@extend_schema(tags=["Pass"], summary="List passes", request=PassListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pass_list_api(request):
    s = PassListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_passes(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
        site_guid=s.validated_data.get("site_guid"),
        status=s.validated_data.get("status", ""),
        visitor_type_guid=s.validated_data.get("visitor_type_guid"),
        user=request.user,
    )
    return _respond(result)