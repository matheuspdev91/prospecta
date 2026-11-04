"""Script para processar lista de empresas a partir de um CSV, analisar

seus sites com Selenium (Firefox), auditar indicadores técnicos e exportar os resultados.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlparse

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By
except ImportError:  # pragma: no cover
    webdriver = None  # type: ignore

    class By:  # type: ignore
        TAG_NAME = "tag name"
        XPATH = "xpath"
        CSS_SELECTOR = "css selector"

    class WebDriverException(Exception):  # type: ignore
        """Fallback quando Selenium não estiver instalado no ambiente atual."""
        msg: str = ""

CAMPOS_ENTRADA = ["empresa", "cidade", "nicho", "telefone", "site"]

CAMPOS_SAIDA = [
    "empresa",
    "cidade",
    "nicho",
    "telefone",
    "site",
    "url_final",
    "titulo",
    "status",
    "erro_acesso",
    "meta_description",
    "qtd_h1",
    "primeiro_h1",
    "total_imagens",
    "imagens_sem_alt",
    "total_links",
    "links_sem_href",
    "evidencias_contato",
    "sinais_revisao",
]

STATUS_SUCESSO = "sucesso"
STATUS_SEM_SITE = "sem_site"
STATUS_ERRO_ACESSO = "erro_acesso"


def normalizar_url(url: str | None) -> str:
    """Normaliza o endereço do site garantindo protocolo e removendo espaços."""
    if not url:
        return ""

    url_limpa = url.strip()
    if not url_limpa:
        return ""

    if not url_limpa.startswith(("https://", "http://")):
        url_limpa = "https://" + url_limpa

    return url_limpa


def validar_url(url: str) -> bool:
    """Verifica se a URL possui estrutura mínima com domínio válido."""
    dominio = urlparse(url).hostname
    return bool(dominio and "." in dominio)


def sanitizar_linha(linha: dict[str, str | None]) -> dict[str, str]:
    """Sanitiza os campos da linha removendo espaços extras e tratando nulos."""
    return {
        campo: (linha.get(campo) or "").strip()
        for campo in CAMPOS_ENTRADA
    }


def ler_empresas_csv(origem: str | Path | TextIO) -> list[dict[str, str]]:
    """Lê um arquivo ou buffer CSV e retorna a lista de empresas sanitizada."""
    if isinstance(origem, (str, Path)):
        caminho = Path(origem)
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        with caminho.open(mode="r", encoding="utf-8-sig") as arquivo:
            return _ler_leitor_csv(arquivo)

    return _ler_leitor_csv(origem)


def _ler_leitor_csv(arquivo: TextIO) -> list[dict[str, str]]:
    leitor = csv.DictReader(arquivo)
    registros: list[dict[str, str]] = []

    for linha in leitor:
        registro = sanitizar_linha(linha)
        # Ignora linhas totalmente vazias
        if any(registro.values()):
            registros.append(registro)

    return registros


def _obter_elementos(driver, by: str, valor: str) -> list:
    """Busca elementos no driver com segurança contra erros ou mocks incompletos."""
    if driver is None or not hasattr(driver, "find_elements"):
        return []
    try:
        elementos = driver.find_elements(by, valor)
        if isinstance(elementos, (list, tuple)):
            return list(elementos)
        return []
    except Exception:
        return []


def extrair_evidencias_contato(links: list) -> str:
    """Identifica evidências de canais de contato, WhatsApp, telefone ou agendamento."""
    evidencias: set[str] = set()

    termos_contato = ("contato", "fale conosco", "fale com", "atendimento", "entre em contato")
    termos_agendamento = ("agendar", "agendamento", "agende", "marque sua visita", "marque")
    termos_matricula = ("matricula", "matrícula", "matricule-se", "inscreva-se", "planos", "assinar")

    for link in links:
        try:
            href = (link.get_attribute("href") or "").strip().lower()
            texto = (getattr(link, "text", "") or "").strip().lower()
            aria = (link.get_attribute("aria-label") or "").strip().lower()
            title = (link.get_attribute("title") or "").strip().lower()
        except Exception:
            continue

        conteudo = f"{texto} {aria} {title}".strip()

        # WhatsApp
        if any(w in href for w in ("wa.me", "whatsapp.com", "api.whatsapp.com")):
            evidencias.add("WhatsApp (link direto)")
        elif "whatsapp" in conteudo or "zap" in conteudo:
            evidencias.add("WhatsApp (menção em link/texto)")

        # Telefone
        if href.startswith("tel:"):
            evidencias.add("Telefone (link tel:)")
        elif any(t in conteudo for t in ("telefone", "ligue", "ligar")):
            evidencias.add("Telefone (menção em link/texto)")

        # E-mail
        if href.startswith("mailto:"):
            evidencias.add("E-mail (mailto)")

        # Agendamento
        if any(t in href for t in ("agendamento", "agendar")):
            evidencias.add("Agendamento (link dedicado)")
        elif any(t in conteudo for t in termos_agendamento):
            evidencias.add("Agendamento (texto do link)")

        # Matrícula / Planos
        if any(t in href for t in ("matricula", "matricular", "planos")):
            evidencias.add("Matrícula/Planos (link dedicado)")
        elif any(t in conteudo for t in termos_matricula):
            evidencias.add("Matrícula/Planos (texto do link)")

        # Contato geral
        if any(c in href for c in ("/contato", "fale-conosco", "faleconosco")):
            evidencias.add("Contato (página de contato)")
        elif any(c in conteudo for c in termos_contato):
            evidencias.add("Contato (texto do link)")

    if not evidencias:
        return "Nenhuma evidência direta identificada"

    return " ; ".join(sorted(evidencias))


def compilar_sinais_revisao(
    titulo: str,
    meta_description: str,
    qtd_h1: int,
    total_imagens: int,
    imagens_sem_alt: int,
    links_sem_href: int,
    evidencias_contato: str,
) -> str:
    """Compila pontos para revisão técnica manual de forma neutra e descritiva."""
    sinais: list[str] = []

    if not titulo or titulo == "(sem título)":
        sinais.append("Sem título na página (avaliar SEO e identificação)")

    if not meta_description:
        sinais.append("Sem meta description (avaliar descrição nos buscadores)")

    if qtd_h1 == 0:
        sinais.append("Sem tag H1 (avaliar estrutura e hierarquia de conteúdo)")
    elif qtd_h1 > 1:
        sinais.append(f"Múltiplos H1 ({qtd_h1}) (avaliar hierarquia)")

    if total_imagens > 0 and imagens_sem_alt > 0:
        sinais.append(f"{imagens_sem_alt} de {total_imagens} imagens sem atributo alt (avaliar acessibilidade)")
    elif total_imagens == 0:
        sinais.append("Nenhuma imagem detectada na página inicial")

    if links_sem_href > 0:
        sinais.append(f"{links_sem_href} links sem href válido (avaliar navegação)")

    if evidencias_contato == "Nenhuma evidência direta identificada":
        sinais.append("Sem links claros de contato/WhatsApp/agendamento identificados (avaliar canais de conversão)")

    return " ; ".join(sinais) if sinais else "Nenhum sinal crítico para revisão imediata"


def auditar_pagina(driver, titulo: str = "") -> dict[str, Any]:
    """Audita a página aberta pelo Selenium capturando indicadores técnicos."""
    # 1. Meta Description
    meta_description = ""
    for meta in _obter_elementos(driver, By.TAG_NAME, "meta"):
        try:
            name = (meta.get_attribute("name") or "").strip().lower()
            if name == "description":
                meta_description = (meta.get_attribute("content") or "").strip()
                break
        except Exception:
            continue

    # 2. H1
    elementos_h1 = _obter_elementos(driver, By.TAG_NAME, "h1")
    qtd_h1 = len(elementos_h1)
    primeiro_h1 = ""
    if elementos_h1:
        try:
            primeiro_h1 = (getattr(elementos_h1[0], "text", "") or "").strip()
        except Exception:
            primeiro_h1 = ""

    # 3. Imagens
    elementos_img = _obter_elementos(driver, By.TAG_NAME, "img")
    total_imagens = len(elementos_img)
    imagens_sem_alt = 0
    for img in elementos_img:
        try:
            alt = img.get_attribute("alt")
            if alt is None or not alt.strip():
                imagens_sem_alt += 1
        except Exception:
            imagens_sem_alt += 1

    # 4. Links
    elementos_a = _obter_elementos(driver, By.TAG_NAME, "a")
    total_links = len(elementos_a)
    links_sem_href = 0
    for a in elementos_a:
        try:
            href = a.get_attribute("href")
            if href is None or not href.strip() or href.strip() == "#":
                links_sem_href += 1
        except Exception:
            links_sem_href += 1

    # 5. Evidências de contato
    evidencias_contato = extrair_evidencias_contato(elementos_a)

    # 6. Sinais para revisão manual
    sinais_revisao = compilar_sinais_revisao(
        titulo=titulo,
        meta_description=meta_description,
        qtd_h1=qtd_h1,
        total_imagens=total_imagens,
        imagens_sem_alt=imagens_sem_alt,
        links_sem_href=links_sem_href,
        evidencias_contato=evidencias_contato,
    )

    return {
        "meta_description": meta_description,
        "qtd_h1": str(qtd_h1),
        "primeiro_h1": primeiro_h1,
        "total_imagens": str(total_imagens),
        "imagens_sem_alt": str(imagens_sem_alt),
        "total_links": str(total_links),
        "links_sem_href": str(links_sem_href),
        "evidencias_contato": evidencias_contato,
        "sinais_revisao": sinais_revisao,
    }


def analisar_site_com_driver(
    driver,
    url: str,
    timeout: int = 20,
) -> tuple[str, str, str, str, dict[str, str]]:
    """Navega até a URL usando o WebDriver e captura título, URL e auditoria técnica.

    Retorna uma tupla contendo: (url_final, titulo, status, erro_acesso, dados_auditoria).
    """
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        url_final = driver.current_url or url
        titulo = driver.title or "(sem título)"
        dados_auditoria = auditar_pagina(driver, titulo=titulo)
        return url_final, titulo, STATUS_SUCESSO, "", dados_auditoria
    except WebDriverException as erro:
        mensagem_erro = erro.msg.strip() if hasattr(erro, "msg") and erro.msg else str(erro)
        mensagem_resumida = mensagem_erro.split("\n")[0]
        return "", "", STATUS_ERRO_ACESSO, mensagem_resumida, {}
    except Exception as erro:  # noqa: BLE001
        return "", "", STATUS_ERRO_ACESSO, str(erro), {}


def _preencher_campos_auditoria_em_branco(dados: dict[str, str], sinal: str = "") -> dict[str, str]:
    dados["meta_description"] = ""
    dados["qtd_h1"] = ""
    dados["primeiro_h1"] = ""
    dados["total_imagens"] = ""
    dados["imagens_sem_alt"] = ""
    dados["total_links"] = ""
    dados["links_sem_href"] = ""
    dados["evidencias_contato"] = ""
    dados["sinais_revisao"] = sinal
    return dados


def processar_registro(
    registro: dict[str, str],
    driver=None,
    timeout: int = 20,
) -> dict[str, str]:
    """Processa um registro individual de empresa.

    Se a empresa não possuir site, ela permanece no relatório como oportunidade
    para revisão manual e NENHUM erro de acesso é registrado.
    """
    dados = dict(registro)
    site_informado = dados.get("site", "").strip()

    if not site_informado:
        dados["url_final"] = ""
        dados["titulo"] = ""
        dados["status"] = STATUS_SEM_SITE
        dados["erro_acesso"] = ""
        return _preencher_campos_auditoria_em_branco(
            dados,
            sinal="Sem site informado (oportunidade para criação de presença digital)",
        )

    url_normalizada = normalizar_url(site_informado)

    if not validar_url(url_normalizada):
        dados["url_final"] = url_normalizada
        dados["titulo"] = ""
        dados["status"] = STATUS_ERRO_ACESSO
        dados["erro_acesso"] = "Endereço de site inválido."
        return _preencher_campos_auditoria_em_branco(
            dados,
            sinal="Endereço de site inválido (avaliar formatação)",
        )

    if driver is None:
        # Modo simulação / teste unitário sem driver
        dados["url_final"] = url_normalizada
        dados["titulo"] = ""
        dados["status"] = STATUS_SUCESSO
        dados["erro_acesso"] = ""
        return _preencher_campos_auditoria_em_branco(dados)

    url_final, titulo, status, erro_acesso, dados_auditoria = analisar_site_com_driver(
        driver,
        url_normalizada,
        timeout=timeout,
    )
    dados["url_final"] = url_final
    dados["titulo"] = titulo
    dados["status"] = status
    dados["erro_acesso"] = erro_acesso

    if status == STATUS_SUCESSO:
        dados.update(dados_auditoria)
    else:
        _preencher_campos_auditoria_em_branco(
            dados,
            sinal="Erro de acesso ao site (avaliar conectividade e domínio)",
        )

    return dados


def exportar_resultados_csv(
    resultados: list[dict[str, str]],
    destino: str | Path | TextIO,
) -> None:
    """Exporta a lista de resultados consolidados para arquivo ou buffer CSV."""
    if isinstance(destino, (str, Path)):
        caminho = Path(destino)
        with caminho.open(mode="w", encoding="utf-8-sig", newline="") as arquivo:
            _escrever_csv(arquivo, resultados)
    else:
        _escrever_csv(destino, resultados)


def _escrever_csv(arquivo: TextIO, resultados: list[dict[str, str]]) -> None:
    escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_SAIDA)
    escritor.writeheader()
    for item in resultados:
        linha = {campo: item.get(campo, "") for campo in CAMPOS_SAIDA}
        escritor.writerow(linha)


def processar_empresas(
    caminho_entrada: str | Path = "empresas.csv",
    caminho_saida: str | Path = "empresas_analisadas.csv",
    headless: bool = False,
    timeout: int = 20,
) -> list[dict[str, str]]:
    """Lê o arquivo de entrada, analisa os sites com Selenium e gera o CSV de saída."""
    print(f"Lendo empresas de: {caminho_entrada}")
    registros = ler_empresas_csv(caminho_entrada)
    print(f"Total de registros encontrados: {len(registros)}")

    precisa_navegador = any(bool(r.get("site")) for r in registros)
    driver = None
    resultados: list[dict[str, str]] = []

    try:
        if precisa_navegador:
            if webdriver is None:
                raise RuntimeError(
                    "Selenium não está disponível no ambiente Python atual. "
                    "Execute o script com o Python que possui Selenium instalado."
                )
            opcoes = webdriver.FirefoxOptions()
            if headless:
                opcoes.add_argument("-headless")
            print("Iniciando navegador Firefox com Selenium...")
            driver = webdriver.Firefox(options=opcoes)

        for index, item in enumerate(registros, start=1):
            empresa = item.get("empresa", "Empresa")
            site = item.get("site", "")
            print(f"[{index}/{len(registros)}] Analisando: {empresa} (site: {site or 'sem site'})...")

            resultado = processar_registro(item, driver=driver, timeout=timeout)
            resultados.append(resultado)

            if resultado["status"] == STATUS_SEM_SITE:
                print(" -> Sem site informado: marcada para revisão manual.")
            elif resultado["status"] == STATUS_SUCESSO:
                print(f" -> Sucesso: {resultado['titulo']} ({resultado['url_final']})")
                print(f"    H1: {resultado.get('qtd_h1')} | Imagens: {resultado.get('total_imagens')} ({resultado.get('imagens_sem_alt')} sem alt)")
                print(f"    Evidências: {resultado.get('evidencias_contato')}")
            else:
                print(f" -> Erro de acesso: {resultado['erro_acesso']}")

    finally:
        if driver:
            print("Fechando navegador...")
            driver.quit()

    exportar_resultados_csv(resultados, caminho_saida)
    print(f"Exportação concluída com sucesso em: {caminho_saida}")
    return resultados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analisa sites de empresas a partir de um CSV e exporta resultados.",
    )
    parser.add_argument(
        "--entrada",
        default="empresas.csv",
        help="Caminho do CSV de entrada (padrão: empresas.csv)",
    )
    parser.add_argument(
        "--saida",
        default="empresas_analisadas.csv",
        help="Caminho do CSV de saída (padrão: empresas_analisadas.csv)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o Firefox em modo headless (sem janela visível)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Tempo limite em segundos para carregamento de cada página (padrão: 20)",
    )

    args = parser.parse_args()
    processar_empresas(
        caminho_entrada=args.entrada,
        caminho_saida=args.saida,
        headless=args.headless,
        timeout=args.timeout,
    )
