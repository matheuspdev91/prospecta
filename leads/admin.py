from django.contrib import admin
from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "nicho",
        "cidade",
        "status",
        "criado_em",
    )

    list_filter = ("status", "nicho", "cidade")

    search_fields = ("empresa", "nome_contato", "telefone")