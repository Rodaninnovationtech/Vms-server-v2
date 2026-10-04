from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    VisitorTypeCreateSerializer,
    VisitorTypeDeleteSerializer,
    VisitorTypeListSerializer,
    VisitorTypeUpdateSerializer,
)
from .visitortypeservices import (
    create_visitor_type,
    delete_visitor_type,
    list_visitor_types,
    update_visitor_type,
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


@extend_schema(tags=["Visitor Type"], summary="Create visitor type",
               request=VisitorTypeCreateSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_type_create_api(request):
    s = VisitorTypeCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_visitor_type(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(tags=["Visitor Type"], summary="Update visitor type",
               request=VisitorTypeUpdateSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def visitor_type_update_api(request):
    s = VisitorTypeUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_visitor_type(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Visitor Type"], summary="Delete visitor type",
               request=VisitorTypeDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def visitor_type_delete_api(request):
    s = VisitorTypeDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_visitor_type(guid=s.validated_data["guid"])
    return _respond(result)


@extend_schema(tags=["Visitor Type"], summary="List visitor types",
               request=VisitorTypeListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visitor_type_list_api(request):
    s = VisitorTypeListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_visitor_types(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
    )
    return _respond(result)