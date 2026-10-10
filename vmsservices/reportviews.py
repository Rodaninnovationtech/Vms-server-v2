# from rest_framework import status
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response

# from .reportservices import ReportAccessDenied, report_list
# from .serializers import ReportListSerializer


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def report_list_api(request):
#     serializer = ReportListSerializer(data=request.data)
#     if not serializer.is_valid():
#         return Response(
#             {
#                 "success": False,
#                 "message": "Validation failed",
#                 "errors": serializer.errors,
#             },
#             status=status.HTTP_400_BAD_REQUEST,
#         )

#     try:
#         rows, pagination = report_list(request.user, serializer.validated_data)
#     except ReportAccessDenied as e:
#         return Response(
#             {"success": False, "message": str(e)},
#             status=status.HTTP_403_FORBIDDEN,
#         )

#     return Response(
#         {
#             "success": True,
#             "message": "Report fetched successfully",
#             "data": {"results": rows, "pagination": pagination},
#         },
#         status=status.HTTP_200_OK,
#     )


from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .reportexport import REPORT_TZ, build_excel, build_pdf, build_subtitle
from .reportservices import ReportAccessDenied, report_list
from .serializers import ReportListSerializer

EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report_list_api(request):
    serializer = ReportListSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    filters = dict(serializer.validated_data)
    is_excel = filters.pop("isexcel", None)   # None = list, True = excel, False = pdf

    # an export always contains every matching row
    if is_excel is not None:
        filters["page"] = None
        filters["page_size"] = None

    try:
        rows, pagination = report_list(request.user, filters)
    except ReportAccessDenied as e:
        return Response(
            {"success": False, "message": str(e)},
            status=status.HTTP_403_FORBIDDEN,
        )

    # ---------------- export ----------------
    if is_excel is not None:
        subtitle = build_subtitle(filters, pagination["total_records"])
        stamp = datetime.now(REPORT_TZ).strftime("%Y-%m-%d")

        if is_excel:
            content = build_excel(rows, subtitle)
            content_type = EXCEL_CONTENT_TYPE
            filename = f"visitor_report_{stamp}.xlsx"
        else:
            content = build_pdf(rows, subtitle)
            content_type = "application/pdf"
            filename = f"visitor_report_{stamp}.pdf"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ---------------- normal list ----------------
    return Response(
        {
            "success": True,
            "message": "Report fetched successfully",
            "data": {"results": rows, "pagination": pagination},
        },
        status=status.HTTP_200_OK,
    )