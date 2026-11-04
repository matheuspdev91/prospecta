"""Testes unitários para o leitor de CSV, auditoria de páginas e tratamento

de campos vazios em processar_empresas.py, sem dependência de abrir o navegador.
"""

from io import StringIO
import tempfile
import unittest
from unittest.mock import MagicMock
from urllib.parse import urlparse

from processar_empresas import (
    CAMPOS_SAIDA,
    STATUS_ERRO_ACESSO,
    STATUS_SEM_SITE,
    STATUS_SUCESSO,
    WebDriverException,
    auditar_pagina,
    compilar_sinais_revisao,
    exportar_resultados_csv,
    extrair_evidencias_contato,
    ler_empresas_csv,
    normalizar_url,
    processar_registro,
    sanitizar_linha,
    validar_url,
)


def criar_mock_elemento(text: str = "", attrs: dict | None = None) -> MagicMock:
    """Cria um mock representando um WebElement do Selenium."""
    el = MagicMock()
    el.text = text
    atributos = attrs or {}
    el.get_attribute.side_effect = lambda nome: atributos.get(nome)
    return el


class NormalizacaoUrlTests(unittest.TestCase):
    def test_adiciona_https_quando_protocolo_esta_ausente(self):
        url = normalizar_url("exemplo.com.br")
        self.assertEqual(url, "https://exemplo.com.br")

    def test_preserva_https_existente(self):
        url = normalizar_url("https://meusite.com")
        self.assertEqual(url, "https://meusite.com")

    def test_preserva_http_existente(self):
        url = normalizar_url("http://meusite.com")
        self.assertEqual(url, "http://meusite.com")

    def test_trata_url_com_espacos_em_branco(self):
        url = normalizar_url("   exemplo.com   ")
        self.assertEqual(url, "https://exemplo.com")

    def test_retorna_vazio_quando_url_for_nula_ou_vazia(self):
        self.assertEqual(normalizar_url(""), "")
        self.assertEqual(normalizar_url(None), "")
        self.assertEqual(normalizar_url("    "), "")


class ValidacaoUrlTests(unittest.TestCase):
    def test_url_valida_com_dominio(self):
        self.assertTrue(validar_url("https://empresa.com.br"))
        self.assertTrue(validar_url("https://www.exemplo.org"))

    def test_url_invalida_sem_ponto_ou_sem_host(self):
        self.assertFalse(validar_url("https://invalido"))
        self.assertFalse(validar_url("https:///"))


class LeituraCSVTests(unittest.TestCase):
    def test_leitura_csv_basica(self):
        conteudo_csv = (
            "empresa,cidade,nicho,telefone,site\n"
            "Academia Força,Bom Despacho,Academia,37999990001,https://forca.com\n"
        )
        buffer = StringIO(conteudo_csv)
        registros = ler_empresas_csv(buffer)

        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["empresa"], "Academia Força")
        self.assertEqual(registros[0]["cidade"], "Bom Despacho")
        self.assertEqual(registros[0]["nicho"], "Academia")
        self.assertEqual(registros[0]["telefone"], "37999990001")
        self.assertEqual(registros[0]["site"], "https://forca.com")

    def test_remove_espacos_extras_de_chaves_e_valores(self):
        conteudo_csv = (
            "empresa,cidade,nicho,telefone,site\n"
            "  Restaurante Central  ,  Bom Despacho ,  Restaurante , 37999990002 ,  central.com  \n"
        )
        buffer = StringIO(conteudo_csv)
        registros = ler_empresas_csv(buffer)

        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["empresa"], "Restaurante Central")
        self.assertEqual(registros[0]["cidade"], "Bom Despacho")
        self.assertEqual(registros[0]["nicho"], "Restaurante")
        self.assertEqual(registros[0]["telefone"], "37999990002")
        self.assertEqual(registros[0]["site"], "central.com")

    def test_tratamento_de_campos_opcionais_vazios(self):
        conteudo_csv = (
            "empresa,cidade,nicho,telefone,site\n"
            "Padaria da Esquina,Bom Despacho,Padaria,,\n"
        )
        buffer = StringIO(conteudo_csv)
        registros = ler_empresas_csv(buffer)

        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["empresa"], "Padaria da Esquina")
        self.assertEqual(registros[0]["telefone"], "")
        self.assertEqual(registros[0]["site"], "")

    def test_ignora_linhas_totalmente_vazias(self):
        conteudo_csv = (
            "empresa,cidade,nicho,telefone,site\n"
            ",,,,\n"
            "Clínica Exemplo,Nova Serrana,Saúde,37999991234,clinica.com\n"
            "   ,   ,   ,   ,   \n"
        )
        buffer = StringIO(conteudo_csv)
        registros = ler_empresas_csv(buffer)

        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["empresa"], "Clínica Exemplo")

    def test_arquivo_inexistente_lanca_excecao(self):
        with self.assertRaises(FileNotFoundError):
            ler_empresas_csv("arquivo_que_com_certeza_nao_existe.csv")


class RegraEmpresasSemSiteTests(unittest.TestCase):
    def test_empresa_sem_site_nao_gera_erro_de_acesso(self):
        """A ausência de site não deve ser tratada como erro de acesso.

        Deve permanecer no relatório marcada para revisão manual com erro_acesso vazio.
        """
        registro = {
            "empresa": "Bar do Zé",
            "cidade": "Bom Despacho",
            "nicho": "Bar",
            "telefone": "37999993333",
            "site": "",
        }

        resultado = processar_registro(registro, driver=None)

        self.assertEqual(resultado["empresa"], "Bar do Zé")
        self.assertEqual(resultado["status"], STATUS_SEM_SITE)
        self.assertEqual(resultado["erro_acesso"], "")
        self.assertEqual(resultado["url_final"], "")
        self.assertEqual(resultado["titulo"], "")
        self.assertEqual(resultado["meta_description"], "")
        self.assertEqual(resultado["qtd_h1"], "")
        self.assertIn("Sem site informado", resultado["sinais_revisao"])

    def test_empresa_com_site_somente_espacos_eh_tratada_como_sem_site(self):
        registro = {
            "empresa": "Lanchonete 10",
            "cidade": "Araújos",
            "nicho": "Lanches",
            "telefone": "",
            "site": "    ",
        }

        resultado = processar_registro(registro, driver=None)

        self.assertEqual(resultado["status"], STATUS_SEM_SITE)
        self.assertEqual(resultado["erro_acesso"], "")
        self.assertEqual(resultado["url_final"], "")


class ProcessamentoComMockDriverTests(unittest.TestCase):
    def test_site_valido_sucesso_com_mock_driver(self):
        mock_driver = MagicMock()
        mock_driver.current_url = "https://empresa.com.br/home"
        mock_driver.title = "Empresa - Início"

        registro = {
            "empresa": "Empresa Tech",
            "cidade": "Bom Despacho",
            "nicho": "Tecnologia",
            "telefone": "37999994444",
            "site": "empresa.com.br",
        }

        resultado = processar_registro(registro, driver=mock_driver)

        mock_driver.get.assert_called_once_with("https://empresa.com.br")
        self.assertEqual(resultado["status"], STATUS_SUCESSO)
        self.assertEqual(resultado["url_final"], "https://empresa.com.br/home")
        self.assertEqual(resultado["titulo"], "Empresa - Início")
        self.assertEqual(resultado["erro_acesso"], "")

    def test_site_com_falha_de_carregamento_com_mock_driver(self):
        mock_driver = MagicMock()
        erro = WebDriverException("Reached error page: about:neterror?e=dnsNotFound\nExtra details")
        erro.msg = "Reached error page: about:neterror?e=dnsNotFound\nExtra details"
        mock_driver.get.side_effect = erro

        registro = {
            "empresa": "Empresa Fantasma",
            "cidade": "Bom Despacho",
            "nicho": "Comércio",
            "telefone": "",
            "site": "https://dominio-inexistente-1234.com",
        }

        resultado = processar_registro(registro, driver=mock_driver)

        self.assertEqual(resultado["status"], STATUS_ERRO_ACESSO)
        self.assertEqual(resultado["url_final"], "")
        self.assertEqual(resultado["titulo"], "")
        self.assertIn("Reached error page", resultado["erro_acesso"])


class ExportacaoCSVTests(unittest.TestCase):
    def test_exportacao_gera_colunas_esperadas(self):
        resultados = [
            {
                "empresa": "Academia Força",
                "cidade": "Bom Despacho",
                "nicho": "Academia",
                "telefone": "37999990001",
                "site": "https://forca.com",
                "url_final": "https://forca.com/",
                "titulo": "Academia Força - Home",
                "status": STATUS_SUCESSO,
                "erro_acesso": "",
                "meta_description": "Melhor academia de Bom Despacho",
                "qtd_h1": "1",
                "primeiro_h1": "Treine com os melhores",
                "total_imagens": "10",
                "imagens_sem_alt": "2",
                "total_links": "25",
                "links_sem_href": "1",
                "evidencias_contato": "WhatsApp (link direto)",
                "sinais_revisao": "2 de 10 imagens sem atributo alt (avaliar acessibilidade)",
            },
            {
                "empresa": "Padaria da Esquina",
                "cidade": "Bom Despacho",
                "nicho": "Padaria",
                "telefone": "",
                "site": "",
                "url_final": "",
                "titulo": "",
                "status": STATUS_SEM_SITE,
                "erro_acesso": "",
                "meta_description": "",
                "qtd_h1": "",
                "primeiro_h1": "",
                "total_imagens": "",
                "imagens_sem_alt": "",
                "total_links": "",
                "links_sem_href": "",
                "evidencias_contato": "",
                "sinais_revisao": "Sem site informado (oportunidade para criação de presença digital)",
            },
        ]

        buffer = StringIO()
        exportar_resultados_csv(resultados, buffer)
        conteudo = buffer.getvalue()

        linhas = conteudo.strip().split("\r\n") if "\r\n" in conteudo else conteudo.strip().split("\n")
        cabecalho = linhas[0].split(",")
        self.assertEqual(cabecalho, CAMPOS_SAIDA)

        self.assertEqual(len(linhas), 3)
        self.assertIn("Academia Força", linhas[1])
        self.assertIn("Padaria da Esquina", linhas[2])


class AuditoriaTecnicaMockTests(unittest.TestCase):
    """Testes para a função auditar_pagina e extração de sinais técnicos com Mocks."""

    def test_audita_pagina_completa_com_sucesso(self):
        mock_driver = MagicMock()

        meta1 = criar_mock_elemento(attrs={"name": "viewport", "content": "width=device-width"})
        meta2 = criar_mock_elemento(attrs={"name": "description", "content": "Academia moderna e completa"})

        h1 = criar_mock_elemento(text="Bem-vindo à Power Fitness")

        img1 = criar_mock_elemento(attrs={"alt": "Foto da academia"})
        img2 = criar_mock_elemento(attrs={"alt": ""})  # sem alt
        img3 = criar_mock_elemento(attrs={})  # sem alt

        link_zap = criar_mock_elemento(text="Fale no Zap", attrs={"href": "https://wa.me/5537999990000"})
        link_tel = criar_mock_elemento(text="Ligue", attrs={"href": "tel:3739380097"})
        link_matricula = criar_mock_elemento(text="Matricule-se agora", attrs={"href": "https://site.com/planos"})
        link_vazio = criar_mock_elemento(text="Início", attrs={"href": "#"})

        def mock_find_elements(by, valor):
            if valor == "meta":
                return [meta1, meta2]
            if valor == "h1":
                return [h1]
            if valor == "img":
                return [img1, img2, img3]
            if valor == "a":
                return [link_zap, link_tel, link_matricula, link_vazio]
            return []

        mock_driver.find_elements.side_effect = mock_find_elements

        resultado = auditar_pagina(mock_driver, titulo="Power Fitness")

        self.assertEqual(resultado["meta_description"], "Academia moderna e completa")
        self.assertEqual(resultado["qtd_h1"], "1")
        self.assertEqual(resultado["primeiro_h1"], "Bem-vindo à Power Fitness")
        self.assertEqual(resultado["total_imagens"], "3")
        self.assertEqual(resultado["imagens_sem_alt"], "2")
        self.assertEqual(resultado["total_links"], "4")
        self.assertEqual(resultado["links_sem_href"], "1")

        # Evidências de contato encontradas
        self.assertIn("WhatsApp (link direto)", resultado["evidencias_contato"])
        self.assertIn("Telefone (link tel:)", resultado["evidencias_contato"])
        self.assertIn("Matrícula/Planos (link dedicado)", resultado["evidencias_contato"])

        # Sinais de revisão apontam apenas o que necessita de avaliação
        self.assertIn("2 de 3 imagens sem atributo alt", resultado["sinais_revisao"])
        self.assertIn("1 links sem href", resultado["sinais_revisao"])

    def test_audita_pagina_sem_metadados_sem_h1_sem_imagens(self):
        mock_driver = MagicMock()
        mock_driver.find_elements.return_value = []

        resultado = auditar_pagina(mock_driver, titulo="(sem título)")

        self.assertEqual(resultado["meta_description"], "")
        self.assertEqual(resultado["qtd_h1"], "0")
        self.assertEqual(resultado["primeiro_h1"], "")
        self.assertEqual(resultado["total_imagens"], "0")
        self.assertEqual(resultado["imagens_sem_alt"], "0")
        self.assertEqual(resultado["total_links"], "0")
        self.assertEqual(resultado["links_sem_href"], "0")
        self.assertEqual(resultado["evidencias_contato"], "Nenhuma evidência direta identificada")

        # Sinais para revisão manual
        self.assertIn("Sem título na página", resultado["sinais_revisao"])
        self.assertIn("Sem meta description", resultado["sinais_revisao"])
        self.assertIn("Sem tag H1", resultado["sinais_revisao"])
        self.assertIn("Nenhuma imagem detectada", resultado["sinais_revisao"])
        self.assertIn("Sem links claros de contato", resultado["sinais_revisao"])

    def test_multiplos_h1_identificados_no_sinal(self):
        mock_driver = MagicMock()
        h1_a = criar_mock_elemento(text="Primeiro Título")
        h1_b = criar_mock_elemento(text="Segundo Título")

        def mock_find_elements(by, valor):
            if valor == "h1":
                return [h1_a, h1_b]
            return []

        mock_driver.find_elements.side_effect = mock_find_elements

        resultado = auditar_pagina(mock_driver, titulo="Título Válido")

        self.assertEqual(resultado["qtd_h1"], "2")
        self.assertEqual(resultado["primeiro_h1"], "Primeiro Título")
        self.assertIn("Múltiplos H1 (2)", resultado["sinais_revisao"])

    def test_extrair_evidencias_contato_por_texto_e_aria(self):
        link1 = criar_mock_elemento(text="Agende sua aula experimental", attrs={"href": "/agendar"})
        link2 = criar_mock_elemento(text="", attrs={"aria-label": "Entre em contato via WhatsApp", "href": "/chat"})
        link3 = criar_mock_elemento(text="Fale Conosco", attrs={"href": "/contato"})

        evidencias = extrair_evidencias_contato([link1, link2, link3])

        self.assertIn("Agendamento", evidencias)
        self.assertIn("WhatsApp", evidencias)
        self.assertIn("Contato", evidencias)


if __name__ == "__main__":
    unittest.main()
