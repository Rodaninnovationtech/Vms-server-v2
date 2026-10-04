from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    SiteTypeCreateSerializer,
    SiteTypeUpdateSerializer,
    SiteTypeDeleteSerializer,
    SiteTypeListSerializer,
)

from .loginservices import login_user
from .logoutservices import logout_user
from .sitetypeservices import (
    create_site_type,
    update_site_type,
    delete_site_type,
    list_site_types,
)
from .utils import get_client_ip




# LoginApi
@extend_schema(
    tags=["Authentication"],
    summary="User Login",
    description="Login using login ID and password.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            description="Login successful"
        ),
        400: OpenApiResponse(
            description="Validation failed"
        ),
        401: OpenApiResponse(
            description="Invalid login ID or password"
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):

    serializer = LoginSerializer(
        data=request.data
    )

    if not serializer.is_valid():

        return Response(
            {
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    login_id = serializer.validated_data["login_id"]
    password = serializer.validated_data["password"]

    result = login_user(
        login_id=login_id,
        password=password,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )

    if not result["success"]:

        return Response(
            result,
            status=status.HTTP_401_UNAUTHORIZED
        )

    return Response(
        result,
        status=status.HTTP_200_OK
    )


# Logout api

@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def logout_api(request):
    serializer = LogoutSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    result = logout_user(
        refresh_token=serializer.validated_data["refresh_token"],
        user=request.user,
    )

    if not result["success"]:
        return Response(
            result,
            status=status.HTTP_401_UNAUTHORIZED
        )

    return Response(
        result,
        status=status.HTTP_200_OK
    )




def _invalid(serializer):
    return Response(
        {
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


def _respond(result, ok_status=status.HTTP_200_OK):
    if result["success"]:
        return Response(result, status=ok_status)

    code = result.pop("status_code", status.HTTP_400_BAD_REQUEST)
    return Response(result, status=code)


@extend_schema(
    tags=["Site Type"],
    summary="Create site type",
    request=SiteTypeCreateSerializer,
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def site_type_create_api(request):

    serializer = SiteTypeCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return _invalid(serializer)

    result = create_site_type(
        site_type=serializer.validated_data["site_type"],
        site_type_description=serializer.validated_data["site_type_description"],
        user=request.user,
    )

    return _respond(result, status.HTTP_201_CREATED)


@extend_schema(
    tags=["Site Type"],
    summary="Update site type",
    request=SiteTypeUpdateSerializer,
)
@api_view(["PUT"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def site_type_update_api(request):

    serializer = SiteTypeUpdateSerializer(data=request.data)

    if not serializer.is_valid():
        return _invalid(serializer)

    result = update_site_type(
        guid=serializer.validated_data["guid"],
        site_type=serializer.validated_data["site_type"],
        site_type_description=serializer.validated_data["site_type_description"],
        user=request.user,
    )

    return _respond(result)


@extend_schema(
    tags=["Site Type"],
    summary="Delete site type",
    request=SiteTypeDeleteSerializer,
)
@api_view(["DELETE"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def site_type_delete_api(request):

    serializer = SiteTypeDeleteSerializer(data=request.data)

    if not serializer.is_valid():
        return _invalid(serializer)

    result = delete_site_type(guid=serializer.validated_data["guid"])

    return _respond(result)


@extend_schema(
    tags=["Site Type"],
    summary="List site types",
    request=SiteTypeListSerializer,
)
@api_view(["POST"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def site_type_list_api(request):

    serializer = SiteTypeListSerializer(data=request.data)

    if not serializer.is_valid():
        return _invalid(serializer)

    result = list_site_types(
        page=serializer.validated_data.get("page"),
        page_size=serializer.validated_data.get("page_size"),
    )

    return _respond(result)