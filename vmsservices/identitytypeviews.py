from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    IdentityTypeCreateSerializer,
    IdentityTypeDeleteSerializer,
    IdentityTypeListSerializer,
    IdentityTypeUpdateSerializer,
)
from .identitytypeservices import (
    create_identity_type,
    delete_identity_type,
    list_identity_types,
    update_identity_type,
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


@extend_schema(tags=["Identity Type"], summary="Create identity type",
               request=IdentityTypeCreateSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def identity_type_create_api(request):
    s = IdentityTypeCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_identity_type(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Identity Type"], summary="Update identity type",
               request=IdentityTypeUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def identity_type_update_api(request):
    s = IdentityTypeUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_identity_type(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Identity Type"], summary="Delete identity type",
               request=IdentityTypeDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def identity_type_delete_api(request):
    s = IdentityTypeDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_identity_type(guid=s.validated_data["guid"])
    return _respond(result)


@extend_schema(tags=["Identity Type"], summary="List identity types",
               request=IdentityTypeListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def identity_type_list_api(request):
    s = IdentityTypeListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_identity_types(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
    )
    return _respond(result)