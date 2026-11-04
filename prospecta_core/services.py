from leads.models import Lead


def cadastrar_lead(**dados) -> Lead:
    """Cadastra um lead após validar os dados obrigatórios."""
    campos_obrigatorios = (
        "empresa",
        "nicho",
        "cidade",
        "oportunidade",
    )

    for campo in campos_obrigatorios:
        valor = dados.get(campo)

        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(
                f"O campo '{campo}' é obrigatório."
            )

        dados[campo] = valor.strip()

    return Lead.objects.create(**dados)


def atualizar_status_lead(lead: Lead, novo_status: str) -> Lead:
    """Atualiza o status de um lead após validar o valor."""
    status_validos = {
        valor for valor, rotulo in Lead.STATUS_CHOICES
    }

    if novo_status not in status_validos:
        raise ValueError(f"Status inválido: {novo_status}")

    lead.status = novo_status
    lead.save(update_fields=["status", "atualizado_em"])

    return lead