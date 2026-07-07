from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Document
from .serializers import DocumentActionResultSerializer, DocumentSerializer, WorklogReviewSerializer
from .services.export_status import DocumentNotReadyForExport, mark_document_exported
from .services.manual_review import apply_manual_review
from .services.pipeline import process_document


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.prefetch_related("logs").all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    search_fields = ["title", "extracted_text"]
    filterset_fields = ["status", "file_type"]

    @extend_schema(
        request=None,
        responses={200: DocumentActionResultSerializer},
        description="Run the document processing pipeline synchronously for demo purposes.",
    )
    @action(detail=True, methods=["post"], url_path="process")
    def process(self, request, pk=None):
        document = self.get_object()
        process_document(document.id)
        document.refresh_from_db()
        return Response(self._action_payload(document), status=status.HTTP_200_OK)

    @extend_schema(
        request=WorklogReviewSerializer,
        responses={200: DocumentActionResultSerializer},
        description="Manually correct normalized worklog data and re-run backend validation.",
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
            400: OpenApiResponse(description="Document is not ready for export."),
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
        }
