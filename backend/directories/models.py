from django.db import models


class ActiveDirectoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Employee(models.Model):
    full_name = models.CharField(max_length=255, unique=True)
    external_1c_id = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveDirectoryQuerySet.as_manager()

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class WorkObject(models.Model):
    name = models.CharField(max_length=255, unique=True)
    external_1c_id = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveDirectoryQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    external_1c_id = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveDirectoryQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
