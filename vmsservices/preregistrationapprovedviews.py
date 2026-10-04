from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .preregistrationapprovedservices import (
    check_in_pre_registration,
    list_approved_pre_registrations,
)
from .preregistrationcreationviews import _invalid, _respond
from .serializers import (
    PreRegistrationApprovedListSerializer,
    PreRegistrationCheckInSerializer,
)


@extend_schema(
    tags=["Pre-Registration"],
    summary="List approved pre-registrations (check-in / check-out page)",
    request=PreRegistrationApprovedListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_registration_approved_list_api(request):
    s = PreRegistrationApprovedListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_approved_pre_registrations(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Pre-Registration"],
    summary="Check in an approved pre-registration",
    request=PreRegistrationCheckInSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pre_registration_check_in_api(request):
    s = PreRegistrationCheckInSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = check_in_pre_registration(user=request.user, **s.validated_data)
    return _respond(result)