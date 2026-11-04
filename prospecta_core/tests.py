from django.test import TestCase
from leads.models import Lead
from prospecta_core.filters import filtrar_leads
from prospecta_core.services import (
    atualizar_status_lead,
    cadastrar_lead,
)
class FiltrarLeadsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lead1 = Lead.objects.create(
            empresa="Academia Força Total",
            nome_contato="Carlos",
            nicho="Academia",
            cidade="Bom Despacho",
            oportunidade="Site desatualizado",
            status="novo",
        )

        Lead.objects.create(
            empresa="Academia Energia",
            nome_contato="Ana",
            nicho="Academia",
            cidade="Araújos",
            oportunidade="Não possui site",
            status="contatado",
        )

        Lead.objects.create(
            empresa="Restaurante Sabor",
            nome_contato="João",
            nicho="Restaurante",
            cidade="Bom Despacho",
            oportunidade="Precisa de presença digital",
            status="novo",
        )



    def test_filtra_por_cidade(self):
        self.assertEqual(filtrar_leads(cidade="Bom Despacho").count(), 2)

    def test_filtra_por_nicho(self):
        self.assertEqual(filtrar_leads(nicho="academia").count(), 2)

    def test_filtra_por_status(self):
        self.assertEqual(filtrar_leads(status="novo").count(), 2)

    def test_filtra_por_empresa(self):
        resultado = filtrar_leads(empresa="força total")
        self.assertEqual(resultado.count(), 1)
        self.assertEqual(resultado.first(), self.lead1)

    def test_combina_multiplos_filtros(self):
        resultado = filtrar_leads(
            cidade="Bom Despacho",
            nicho="Academia",
            status="novo",
        )
        self.assertEqual(resultado.count(), 1)
        self.assertEqual(resultado.first(), self.lead1)

    def test_ignora_filtros_vazios(self):
        resultado = filtrar_leads(
            cidade="",
            nicho=" ",
            status=None,
            empresa="",
        )
        self.assertEqual(resultado.count(), 3)

    def test_retorna_vazio_quando_nao_encontra(self):
        resultado = filtrar_leads(cidade="Cidade Inexistente")
        self.assertEqual(resultado.count(), 0)

class CadastrarLeadTests(TestCase):
    def test_cadastra_lead_valido(self):
        lead = cadastrar_lead(
            empresa="Clínica Exemplo",
            nicho="Saúde",
            cidade="Bom Despacho",
            oportunidade="Precisa de um site",
        )

        self.assertEqual(lead.empresa, "Clínica Exemplo")
        self.assertEqual(lead.status, "novo")
        self.assertEqual(Lead.objects.count(), 1)

    def test_remove_espacos_dos_campos_obrigatorios(self):
        lead = cadastrar_lead(
            empresa="  Clínica Exemplo  ",
            nicho=" Saúde ",
            cidade=" Bom Despacho ",
            oportunidade=" Precisa de um site ",
        )

        self.assertEqual(lead.empresa, "Clínica Exemplo")
        self.assertEqual(lead.nicho, "Saúde")

    def test_rejeita_empresa_vazia(self):
        with self.assertRaisesMessage(
            ValueError,
            "O campo 'empresa' é obrigatório.",
        ):
            cadastrar_lead(
                empresa=" ",
                nicho="Saúde",
                cidade="Bom Despacho",
                oportunidade="Precisa de um site",
            )

        self.assertEqual(Lead.objects.count(), 0)


class AtualizarStatusLeadTests(TestCase):
    def setUp(self):
        self.lead = Lead.objects.create(
            empresa="Academia Teste",
            nicho="Academia",
            cidade="Bom Despacho",
            oportunidade="Site desatualizado",
        )

    def test_atualiza_status_valido(self):
        lead = atualizar_status_lead(
            self.lead,
            "contatado",
        )

        self.assertEqual(lead.status, "contatado")

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "contatado")

    def test_rejeita_status_invalido(self):
        with self.assertRaisesMessage(
            ValueError,
            "Status inválido: inexistente",
        ):
            atualizar_status_lead(
                self.lead,
                "inexistente",
            )

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "novo")