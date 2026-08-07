from django.contrib import admin

from .models import EmotionSnapshot


@admin.register(EmotionSnapshot)
class EmotionSnapshotAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "expression", "identity_placeholder")

    @admin.display(description="identity")
    def identity_placeholder(self, obj):
        return "-"
