
from django.db.models import QuerySet

from leads.models import Lead


def filtrar_leads(
    *,
    cidade: str | None = None,
    nicho: str | None = None,
    status: str | None = None,
    empresa: str | None = None,
) -> QuerySet[Lead]:
    """Filtra leads pelos critérios informados."""

    queryset = Lead.objects.all()

    if cidade and cidade.strip():
        queryset = queryset.filter(cidade__icontains=cidade.strip())

    if nicho and nicho.strip():
        queryset = queryset.filter(nicho__icontains=nicho.strip())

    if status and status.strip():
        queryset = queryset.filter(status=status.strip())

    if empresa and empresa.strip():
        queryset = queryset.filter(empresa__icontains=empresa.strip())

    return queryset
