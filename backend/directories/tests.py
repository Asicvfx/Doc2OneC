from django.core.management import call_command
from django.test import TestCase

from directories.models import Employee, WorkObject, WorkType


class SeedDemoDataCommandTests(TestCase):
    def test_seed_demo_data_creates_russian_demo_directories(self):
        call_command("seed_demo_data")

        self.assertTrue(Employee.objects.filter(full_name="Иванов Иван").exists())
        self.assertTrue(WorkObject.objects.filter(name="Объект №1").exists())
        self.assertTrue(WorkType.objects.filter(name="Электромонтажные работы").exists())
