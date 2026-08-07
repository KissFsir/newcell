from django.contrib import admin

from .models import PhysioRecord


@admin.register(PhysioRecord)
class PhysioRecordAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "hr_avg", "temp_avg", "skin_humidity_avg")
