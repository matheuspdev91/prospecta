
from django.test import TestCase

from leads.models import Lead
from prospecta_core.filters import filtrar_leads


class FiltrarLeadsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lead1 = Lead.objects.create(
            empresa="Academia Força Total",
            nome_contato="Carlos",
            nicho="Academia",
            cidade="Bom Despacho",
            telefone="37999990000",
            site_atual="https://forcatotal.com.br",
            oportunidade="Site desatualizado",
            status="novo",
        )

        cls.lead2 = Lead.objects.create(
            empresa="Academia Energia",
            nome_contato="Ana",
            nicho="Academia",
            cidade="Araújos",
            telefone="37999991111",
            site_atual="https://academiaenergia.com.br",
            oportunidade="Não possui site",
            status="contatado",
        )

        cls.lead3 = Lead.objects.create(
            empresa="Restaurante Sabor",
            nome_contato="João",
            nicho="Restaurante",
            cidade="Bom Despacho",
            telefone="37999992222",
            site_atual="",
            oportunidade="Precisa de presença digital",
            status="novo",
        )

    def test_filtra_por_cidade(self):
        resultado = filtrar_leads(cidade="Bom Despacho")

        self.assertEqual(resultado.count(), 2)

    def test_filtra_por_nicho(self):
        resultado = filtrar_leads(nicho="academia")

        self.assertEqual(resultado.count(), 2)

    def test_filtra_por_status(self):
        resultado = filtrar_leads(status="novo")

        self.assertEqual(resultado.count(), 2)

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

    def test_retorna_queryset_vazio_quando_nao_encontra(self):
        resultado = filtrar_leads(cidade="Cidade Inexistente")

        self.assertEqual(resultado.count(), 0)
