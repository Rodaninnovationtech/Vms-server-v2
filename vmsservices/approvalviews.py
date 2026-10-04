# from drf_spectacular.utils import extend_schema
# from rest_framework import status
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response

# from .approvalservices import list_site_approvers
# from .serializers import ApproverListSerializer


# def _invalid(serializer):
#     return Response(
#         {"success": False, "message": "Validation failed", "errors": serializer.errors},
#         status=status.HTTP_400_BAD_REQUEST,
#     )


# def _respond(result, ok_status=status.HTTP_200_OK):
#     if result["success"]:
#         return Response(result, status=ok_status)
#     code = result.pop("status_code", status.HTTP_400_BAD_REQUEST)
#     return Response(result, status=code)


# @extend_schema(
#     tags=["Approval"],
#     summary="List approvers (email, role, site) of a site",
#     request=ApproverListSerializer,
# )
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def approver_list_api(request):
#     s = ApproverListSerializer(data=request.data)
#     if not s.is_valid():
#         return _invalid(s)
#     result = list_site_approvers(
#         site_guid=s.validated_data["site_guid"],
#         user=request.user,
#     )
#     return _respond(result)



from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .approvalservices import (
    act_on_request,
    list_approval_history,
    list_approvals,
    list_site_approvers,
)
from .serializers import (
    ApprovalActionSerializer,
    ApprovalHistoryListSerializer,
    ApprovalListSerializer,
    ApproverListSerializer,
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
    tags=["Approval"],
    summary="List approvers (email, role, site) of a site",
    request=ApproverListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approver_list_api(request):
    s = ApproverListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_site_approvers(
        site_guid=s.validated_data["site_guid"],
        user=request.user,
    )
    return _respond(result)


@extend_schema(
    tags=["Approval"],
    summary="List PENDING pre-registration requests for approval (site wise)",
    request=ApprovalListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approval_list_api(request):
    s = ApprovalListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_approvals(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Approval"],
    summary="Approval history: approved and rejected requests (site wise)",
    request=ApprovalHistoryListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approval_history_api(request):
    s = ApprovalHistoryListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_approval_history(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(
    tags=["Approval"],
    summary="Approve or reject a pre-registration request",
    request=ApprovalActionSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approval_action_api(request):
    s = ApprovalActionSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = act_on_request(user=request.user, **s.validated_data)
    return _respond(result)