from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    SiteCreateSerializer,
    SiteDeleteSerializer,
    SiteListSerializer,
    SiteParentListSerializer,
    SiteUpdateSerializer,
)
from .sitecreationservices import (
    create_site,
    delete_site,
    list_parent_sites,
    list_site_dropdown,
    list_sites,
    update_site,
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


# create and update accept multipart/form-data because of the image upload
@extend_schema(
    tags=["Site"],
    summary="Create site",
    request={"multipart/form-data": SiteCreateSerializer},
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def site_create_api(request):
    s = SiteCreateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = create_site(user=request.user, **s.validated_data)
    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Site"],
    summary="Update site",
    request={"multipart/form-data": SiteUpdateSerializer},
)
@api_view(["PUT"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def site_update_api(request):
    s = SiteUpdateSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = update_site(user=request.user, **s.validated_data)
    return _respond(result)


@extend_schema(tags=["Site"], summary="Delete site", request=SiteDeleteSerializer)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def site_delete_api(request):
    s = SiteDeleteSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = delete_site(guid=s.validated_data["guid"])
    return _respond(result)


@extend_schema(tags=["Site"], summary="List sites", request=SiteListSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def site_list_api(request):
    s = SiteListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_sites(
        page=s.validated_data.get("page"),
        page_size=s.validated_data.get("page_size"),
        search=s.validated_data.get("search", ""),
        site_guid=s.validated_data.get("site_guid"),
        user=request.user,
    )
    return _respond(result)



@extend_schema(
    tags=["Site"],
    summary="List sites for the parent-site dropdown",
    request=SiteParentListSerializer,
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def site_parent_list_api(request):
    s = SiteParentListSerializer(data=request.data)
    if not s.is_valid():
        return _invalid(s)
    result = list_parent_sites(exclude_guid=s.validated_data.get("exclude"))
    return _respond(result)

@extend_schema(tags=["Site"], summary="List sites for dropdown (guid, name, model)")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def site_dropdown_api(request):
    return _respond(list_site_dropdown())
 