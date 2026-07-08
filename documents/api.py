from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Document
from .serializers import (
    DocumentActionResultSerializer,
    DocumentCreateSerializer,
    DocumentDetailSerializer,
    DocumentListSerializer,
    ErrorResponseSerializer,
    WorklogReviewSerializer,
)
from .services.export_status import DocumentNotReadyForExport, mark_document_exported
from .services.manual_review import apply_manual_review
from .services.processing_jobs import ProcessingAlreadyActive, enqueue_document_processing
from .services.processing_status import get_processing_issue_payload


DOCUMENT_LIST_PARAMETERS = [
    OpenApiParameter(
        name="status",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filter by document status, e.g. ready_for_1c or needs_review.",
    ),
    OpenApiParameter(
        name="file_type",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Filter by detected file type, e.g. txt, csv, xlsx, pdf, image, unknown.",
    ),
    OpenApiParameter(
        name="search",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Search by title or extracted text.",
    ),
    OpenApiParameter(
        name="ordering",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Ordering: created_at, -created_at, updated_at, -updated_at, title, -title.",
    ),
]


@extend_schema_view(
    list=extend_schema(
        parameters=DOCUMENT_LIST_PARAMETERS,
        responses={200: DocumentListSerializer},
        description="List documents with pagination plus status, file type, search, and ordering query parameters.",
    ),
    create=extend_schema(
        request=DocumentCreateSerializer,
        responses={201: DocumentDetailSerializer},
        examples=[
            OpenApiExample(
                "Multipart upload",
                description="Use multipart/form-data with a title and a document file.",
                value={"title": "Ivanov worklog 2026-07-06", "file": "sample_worklog.txt"},
                request_only=True,
            )
        ],
    ),
    retrieve=extend_schema(responses={200: DocumentDetailSerializer}),
)
class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.prefetch_related("logs").all()
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_value = self.request.query_params.get("status")
        file_type = self.request.query_params.get("file_type")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering")

        if status_value in Document.Status.values:
            queryset = queryset.filter(status=status_value)
        if file_type in Document.FileType.values:
            queryset = queryset.filter(file_type=file_type)
        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(extracted_text__icontains=search)
        if ordering in {"created_at", "-created_at", "updated_at", "-updated_at", "title", "-title"}:
            queryset = queryset.order_by(ordering)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentCreateSerializer
        if self.action == "list":
            return DocumentListSerializer
        return DocumentDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        response_serializer = DocumentDetailSerializer(document, context=self.get_serializer_context())
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        request=None,
        responses={200: DocumentActionResultSerializer, 202: DocumentActionResultSerializer, 409: ErrorResponseSerializer},
        description="Queue document processing. In sync mode the response contains the completed result; in thread mode it returns 202 while background processing runs.",
    )
    @action(detail=True, methods=["post"], url_path="process")
    def process(self, request, pk=None):
        document = self.get_object()
        try:
            document = enqueue_document_processing(document.id, source="API")
        except ProcessingAlreadyActive as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        document.refresh_from_db()
        response_status = status.HTTP_202_ACCEPTED if document.status == Document.Status.QUEUED else status.HTTP_200_OK
        return Response(self._action_payload(document), status=response_status)

    @extend_schema(
        request=WorklogReviewSerializer,
        responses={200: DocumentActionResultSerializer},
        description="Manually correct normalized worklog data and re-run backend validation.",
        examples=[
            OpenApiExample(
                "Reviewed worklog",
                value={
                    "employee_name": "Иванов Иван",
                    "date": "2026-07-06",
                    "object": "Объект №1",
                    "work_type": "Электромонтажные работы",
                    "hours": "7.5",
                    "comment": "Reviewed manually",
                },
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        document = self.get_object()
        serializer = WorklogReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        apply_manual_review(document, serializer.to_review_data())
        document.refresh_from_db()
        return Response(self._action_payload(document), status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={
            200: DocumentActionResultSerializer,
            400: ErrorResponseSerializer,
        },
        description="Mark a processed document as exported to 1C.",
    )
    @action(detail=True, methods=["post"], url_path="mark-exported")
    def mark_exported(self, request, pk=None):
        document = self.get_object()
        try:
            mark_document_exported(document, source="API")
        except DocumentNotReadyForExport as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        document.refresh_from_db()
        return Response(self._action_payload(document), status=status.HTTP_200_OK)

    def _action_payload(self, document: Document) -> dict:
        return {
            "id": document.id,
            "status": document.status,
            "normalized_json": document.normalized_json,
            "validation_errors": document.validation_errors,
            "processing_issue": get_processing_issue_payload(document),
        }


