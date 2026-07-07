from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from core.views import dashboard
from directories.api import EmployeeViewSet, WorkObjectViewSet, WorkTypeViewSet
from documents.api import DocumentViewSet


router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="api-documents")
router.register("employees", EmployeeViewSet, basename="api-employees")
router.register("work-objects", WorkObjectViewSet, basename="api-work-objects")
router.register("work-types", WorkTypeViewSet, basename="api-work-types")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("documents/", include("documents.urls")),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
