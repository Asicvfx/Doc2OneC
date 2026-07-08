from django.contrib import admin

from .models import Employee, WorkObject, WorkType


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "external_1c_id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "external_1c_id")


@admin.register(WorkObject)
class WorkObjectAdmin(admin.ModelAdmin):
    list_display = ("name", "external_1c_id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "external_1c_id")


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "external_1c_id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "external_1c_id")
