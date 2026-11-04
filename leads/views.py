from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from django.contrib import messages

from leads.models import Lead
from prospecta_core.services import (
    cadastrar_lead,
    atualizar_status_lead,
)


def dashboard(request):

    contagens = {
        item['status']: item['total']
        for item in Lead.objects.values("status").annotate(total=Count("id"))
    }
    
    total_leads = Lead.objects.count()
    leads_novos = contagens.get("novo", 0)
    leads_contatados = contagens.get("contatado", 0)
    leads_respondeu = contagens.get("respondeu", 0)
    leads_negociando = contagens.get("negociando", 0)
    leads_convertidos = contagens.get("convertido", 0)
    leads_perdidos = contagens.get("perdido", 0)
    

    return render(
        request,
        "dashboard.html",
        {
            "total_leads": total_leads,
            "leads_novos": leads_novos,
            "leads_contatados": leads_contatados,
            "leads_negociando": leads_negociando,
            "leads_convertidos": leads_convertidos,
            "leads_respondeu": leads_respondeu,
            "leads_perdidos": leads_perdidos,
        }
    )

    

def cadastrar_lead_view(request):
    if request.method == "POST":
        try:
            cadastrar_lead(
                empresa=request.POST.get("empresa", ""),
                nome_contato=request.POST.get("nome_contato", ""),
                nicho=request.POST.get("nicho", ""),
                cidade=request.POST.get("cidade", ""),
                telefone=request.POST.get("telefone", ""),
                site_atual=request.POST.get("site_atual", ""),
                oportunidade=request.POST.get("oportunidade", ""),
            )
            messages.success(request, "Lead cadastrado com sucesso!")
            return redirect("dashboard")

        except ValueError as erro:
            messages.error(request, str(erro))

    return render(request, "cadastrar_leads.html")

def listar_leads(request):
    leads = Lead.objects.all().order_by("-criado_em")

    return render(
      request,
        "listar_leads.html",
        {
            "leads": leads,
            "status_choices": Lead.STATUS_CHOICES,
        },
    )


def atualizar_status_lead_view(request, lead_id):
    if request.method != "POST":
        return redirect("listar_leads")

    lead = get_object_or_404(Lead, pk=lead_id)
    novo_status = request.POST.get("status", "")

    try:
        atualizar_status_lead(lead, novo_status)
        messages.success(
            request,
            f"Status de '{lead.empresa}' atualizado com sucesso!",
        )
    except ValueError as erro:
        messages.error(request, str(erro))

    return redirect("listar_leads")


def relatorios(request):
    contagens = {
        item["status"]: item["total"]
        for item in Lead.objects.values("status").annotate(total=Count("id"))
    }

    total_leads = Lead.objects.count()
    leads_convertidos = contagens.get("convertido", 0)
    leads_contatados = contagens.get("contatado", 0)
    leads_negociando = contagens.get("negociando", 0)
    leads_perdidos = contagens.get("perdido", 0)

    taxa_conversao = (
        leads_convertidos / total_leads * 100
        if total_leads > 0
        else 0
    )

    rotulos_status = dict(Lead.STATUS_CHOICES)

    etapas = []
    for status, rotulo in Lead.STATUS_CHOICES:
        total = contagens.get(status, 0)
        percentual = total / total_leads * 100 if total_leads else 0

        etapas.append({
            "rotulo": rotulo,
            "total": total,
            "percentual": round(percentual, 1),
        })

    return render(
        request,
        "relatorios.html",
        {
            "total_leads": total_leads,
            "leads_convertidos": leads_convertidos,
            "leads_contatados": leads_contatados,
            "leads_negociando": leads_negociando,
            "leads_perdidos": leads_perdidos,
            "taxa_conversao": round(taxa_conversao, 1),
        },
    )

