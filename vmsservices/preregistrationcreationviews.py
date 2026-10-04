from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .preregistrationcreationservices import (
    create_pre_registration,
    delete_pre_registration,
    list_pre_registrations,
    update_pre_registration,
)
from .serializers import (
    PreRegistrationCreateSerializer,
    PreRegistrationDeleteSerializer,
    PreRegistrationListSerializer,
    PreRegistrationUpdateSerializer,
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
    tags=["Pre-Registration"],
    summary="Create a pre-registration request",
    request=PreRegistrationCreateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_registration_create_api(request):
    s = PreRegistrationCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_pre_registration(user=request.user, data=s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Pre-Registration"],
    summary="List pre-registration requests",
    request=PreRegistrationListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_registration_list_api(request):
    s = PreRegistrationListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_pre_registrations(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Pre-Registration"],
    summary="Edit a pending pre-registration request",
    request=PreRegistrationUpdateSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_registration_update_api(request):
    s = PreRegistrationUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_pre_registration(user=request.user, data=s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Pre-Registration"],
    summary="Delete a pending / rejected pre-registration request",
    request=PreRegistrationDeleteSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_registration_delete_api(request):
    s = PreRegistrationDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_pre_registration(user=request.user, guid=s.validated_data["guid"])
    return _respond(result)