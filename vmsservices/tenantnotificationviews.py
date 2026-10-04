from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    TenantAvailabilityCheckSerializer,
    TenantNotificationCreateSerializer,
    TenantNotificationDeleteSerializer,
    TenantNotificationListSerializer,
    TenantNotificationUpdateSerializer,
)
from .tenantnotificationservices import (
    check_tenant_availability,
    create_tenant_notification,
    delete_tenant_notification,
    list_tenant_notifications,
    update_tenant_notification,
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
    tags=["Tenant Notification"],
    summary="Create tenant notification",
    request=TenantNotificationCreateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_notification_create_api(request):
    s = TenantNotificationCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_tenant_notification(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Tenant Notification"],
    summary="Update tenant notification",
    request=TenantNotificationUpdateSerializer,
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def tenant_notification_update_api(request):
    s = TenantNotificationUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_tenant_notification(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Tenant Notification"],
    summary="Delete tenant notification",
    request=TenantNotificationDeleteSerializer,
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def tenant_notification_delete_api(request):
    s = TenantNotificationDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_tenant_notification(guid=s.validated_data["guid"], user=request.user)
    return _respond(result)


@extend_schema(
    tags=["Tenant Notification"],
    summary="List tenant notifications",
    request=TenantNotificationListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_notification_list_api(request):
    s = TenantNotificationListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_tenant_notifications(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
        site_guid=s.validated_data.get("site_guid"),
        user=request.user,
    )
    return _respond(result)




@extend_schema(
    tags=["Tenant Notification"],
    summary="Check a location's availability for a date range",
    request=TenantAvailabilityCheckSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def tenant_availability_check_api(request):
    s = TenantAvailabilityCheckSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = check_tenant_availability(
        tenant=s.validated_data["tenant"],
        from_date=s.validated_data["from_date"],
        to_date=s.validated_data["to_date"],
        user=request.user,
    )
    return _respond(result)