from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    VisitorCheckInSerializer,
    VisitorCheckOutSerializer,
    VisitorIdentitySearchSerializer,
    VisitorListSerializer,
    VisitorPassLookupSerializer,
)
from .visitorcontructorcreationsservices import (
    check_out,
    create_check_in,
    list_visits,
    find_checked_in_by_pass,
    search_persons,
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
    tags=["Visitor"],
    summary="Check in a visitor / contractor",
    request=VisitorCheckInSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_check_in_api(request):
    s = VisitorCheckInSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_check_in(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Visitor"],
    summary="List visitors and contractors",
    request=VisitorListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_list_api(request):
    s = VisitorListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_visits(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Visitor"],
    summary="Check out a visitor / contractor",
    request=VisitorCheckOutSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_check_out_api(request):
    s = VisitorCheckOutSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = check_out(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Visitor"],
    summary="Find existing persons by identity type + number",
    request=VisitorIdentitySearchSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_identity_search_api(request):
    s = VisitorIdentitySearchSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = search_persons(**s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Visitor"],
    summary="Find the checked-in visitor / contractor holding a pass",
    request=VisitorPassLookupSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_pass_lookup_api(request):
    s = VisitorPassLookupSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = find_checked_in_by_pass(user=request.user, **s.validated_data)
    return _respond(result)