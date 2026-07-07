from rest_framework import serializers, viewsets

from .models import Employee, WorkObject, WorkType


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["id", "full_name", "external_1c_id", "is_active"]


class WorkObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkObject
        fields = ["id", "name", "external_1c_id", "is_active"]


class WorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkType
        fields = ["id", "name", "external_1c_id", "is_active"]


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    search_fields = ["full_name", "external_1c_id"]


class WorkObjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkObject.objects.all()
    serializer_class = WorkObjectSerializer
    search_fields = ["name", "external_1c_id"]


class WorkTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkType.objects.all()
    serializer_class = WorkTypeSerializer
    search_fields = ["name", "external_1c_id"]
