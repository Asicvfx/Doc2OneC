from django.contrib import admin

from .models import Document, ProcessingLog


class ProcessingLogInline(admin.TabularInline):
    model = ProcessingLog
    extra = 0
    readonly_fields = ("step", "message", "level", "created_at")
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "file_type", "status", "created_at", "updated_at")
    list_filter = ("status", "file_type", "created_at")
    search_fields = ("title", "extracted_text")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProcessingLogInline]


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ("document", "step", "level", "created_at")
    list_filter = ("level", "step")
    search_fields = ("document__title", "message")
