from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    TenantCreateSerializer,
    TenantDeleteSerializer,
    TenantListSerializer,
    TenantUpdateSerializer,
)
from .tenantcreationservices import (
    create_tenant,
    delete_tenant,
    list_tenants,
    update_tenant,
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


@extend_schema(tags=["Tenant"], summary="Create tenant", request=TenantCreateSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_create_api(request):
    s = TenantCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_tenant(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Tenant"], summary="Update tenant", request=TenantUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def tenant_update_api(request):
    s = TenantUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_tenant(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Tenant"], summary="Delete tenant", request=TenantDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def tenant_delete_api(request):
    s = TenantDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_tenant(guid=s.validated_data["guid"], user=request.user)
    return _respond(result)


@extend_schema(tags=["Tenant"], summary="List tenants", request=TenantListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_list_api(request):
    s = TenantListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_tenants(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
        site_guid=s.validated_data.get("site_guid"),
        user=request.user,
    )
    return _respond(result)