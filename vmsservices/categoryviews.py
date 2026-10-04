from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    CategoryCreateSerializer,
    CategoryDeleteSerializer,
    CategoryListSerializer,
    CategoryUpdateSerializer,
)
from .categoryservices import (
    create_category,
    delete_category,
    list_categories,
    update_category,
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


@extend_schema(tags=["Category"], summary="Create category", request=CategoryCreateSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def category_create_api(request):
    s = CategoryCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_category(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Category"], summary="Update category", request=CategoryUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def category_update_api(request):
    s = CategoryUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_category(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Category"], summary="Delete category", request=CategoryDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def category_delete_api(request):
    s = CategoryDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_category(guid=s.validated_data["guid"])
    return _respond(result)


@extend_schema(tags=["Category"], summary="List categories", request=CategoryListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def category_list_api(request):
    s = CategoryListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_categories(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
    )
    return _respond(result)