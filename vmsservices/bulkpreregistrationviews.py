from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .bulkpreregistrationservices import (
    create_bulk_pre_registration,
    list_bulk_approved,
    list_bulk_ids,
    validate_bulk_pre_registration,
)
from .serializers import (
    BulkIdListSerializer,
    BulkPreRegistrationApprovedListSerializer,
    BulkPreRegistrationCreateSerializer,
    BulkPreRegistrationValidateSerializer,
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
    tags=["Bulk Pre-Registration"],
    summary="Validate the Excel rows (nothing is saved)",
    request=BulkPreRegistrationValidateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_pre_registration_validate_api(request):
    s = BulkPreRegistrationValidateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = validate_bulk_pre_registration(user=request.user, data=s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Bulk Pre-Registration"],
    summary="Create all rows as pending pre-registrations under one bulk id",
    request=BulkPreRegistrationCreateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_pre_registration_create_api(request):
    s = BulkPreRegistrationCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_bulk_pre_registration(user=request.user, data=s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Bulk Pre-Registration"],
    summary="Approved bulk pre-registrations (filter by bulk_id)",
    request=BulkPreRegistrationApprovedListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_pre_registration_approved_list_api(request):
    s = BulkPreRegistrationApprovedListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_bulk_approved(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Bulk Pre-Registration"],
    summary="Bulk ids with pending / approved / rejected counts",
    request=BulkIdListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_id_list_api(request):
    s = BulkIdListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_bulk_ids(user=request.user, **s.validated_data)
    return _respond(result)