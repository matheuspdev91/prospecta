
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import WebDriverException


def analisar_site(url):
    if not url.startswith(("https://", "http://")):
        url = "https://" + url

    dominio = urlparse(url).hostname

    if not dominio or "." not in dominio:
        print("Endereço inválido.")
        return

    driver = None

    try:
        driver = webdriver.Firefox()
        driver.set_page_load_timeout(20)
        driver.get(url)

        print("\n--- ANÁLISE DO SITE ---")
        print(f"URL informada: {url}")
        print(f"URL acessada:  {driver.current_url}")
        print(f"Título:        {driver.title or '(sem título)'}")
        print(f"Status:        Página carregada pelo navegador")

    except WebDriverException as erro:
        print(f"\nNão foi possível analisar o site: {erro.msg}")

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    endereco = input("Cole o endereço do site da empresa: ").strip()
    analisar_site(endereco)
2