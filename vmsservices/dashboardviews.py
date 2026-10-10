from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .dashboardservices import get_dashboard_summary, list_not_checked_out
from .serializers import (
    DashboardNotCheckedOutSerializer,
    DashboardSummarySerializer,
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
    tags=["Dashboard"],
    summary="Dashboard summary (site counts, totals, check-in / check-out per day)",
    request=DashboardSummarySerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def dashboard_summary_api(request):
    s = DashboardSummarySerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = get_dashboard_summary(
        user=request.user,
        site_guid=s.validated_data.get("site_guid"),
        from_date=s.validated_data.get("from_date"),
        to_date=s.validated_data.get("to_date"),
    )
    return _respond(result)


@extend_schema(
    tags=["Dashboard"],
    summary="Visitors / contractors who checked in but have not checked out",
    request=DashboardNotCheckedOutSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def dashboard_not_checked_out_api(request):
    s = DashboardNotCheckedOutSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_not_checked_out(
        user=request.user,
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
        site_guid=s.validated_data.get("site_guid"),
        kind=s.validated_data.get("kind", ""),
        from_date=s.validated_data.get("from_date"),
        to_date=s.validated_data.get("to_date"),
    )
    return _respond(result)