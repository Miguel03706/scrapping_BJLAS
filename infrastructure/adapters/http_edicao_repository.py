import requests
import re  # <--- Adicione este import
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from core.domain.entities import Edicao, Artigo
from core.domain.repositories import EdicaoRepository
from infrastructure.config import URLS, CSS_SELECTORS, TIMEOUT

class HTTPEdicaoRepository(EdicaoRepository):
    def __init__(self, session: requests.Session):
        self.session = session

    def obter_todas(self) -> list[Edicao]:
        edicoes = []
        for url_base in URLS:
            response = self.session.get(url_base, timeout=TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            for a in soup.select(CSS_SELECTORS["EDICOES"]):
                if href := a.get('href'):
                    edicoes.append(Edicao(url=urljoin(response.url, href)))
        return edicoes

    def obter_artigos(self, edicao: Edicao) -> list[Artigo]:
        response = self.session.get(edicao.url, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        # Extrair data da edição
        data_publicacao = "sem_data"
        published_div = soup.select_one(CSS_SELECTORS.get("DATA_PUBLICACAO", ""))
        
        if published_div:
            value_span = published_div.find("span", class_="value")
            if value_span:
                data_publicacao = value_span.get_text(strip=True)
            else:
                data_publicacao = published_div.get_text(strip=True)

        # Extrair o ANO usando Regex (Procura os 4 primeiros dígitos seguidos na string de data)
        ano_match = re.search(r'\d{4}', data_publicacao)
        ano = ano_match.group(0) if ano_match else "ANO_DESCONHECIDO"

        artigos = []
        for article in soup.select(CSS_SELECTORS["ARTIGOS"]):
            titulo_tag = article.select_one(CSS_SELECTORS["TITULO"])
            pdf_tag = article.select_one(CSS_SELECTORS["PDF_LINK"])

            if titulo_tag and pdf_tag:
                url_view_bruta = pdf_tag['href']
                
                # --- NOVA LÓGICA INTELIGENTE DO DOI ---
                # Extrai o ID numérico que vem logo após "/view/" na URL
                id_match = re.search(r'/view/(\d+)', url_view_bruta)
                id_artigo = id_match.group(1) if id_match else "ID_DESCONHECIDO"
                
                # Constrói o DOI com o padrão fixo da revista PROLAM
                doi_montado = f"https://doi.org/10.11606/issn.1676-6288.prolam.{ano}.{id_artigo}"
                # ---------------------------------------

                artigos.append(Artigo(
                    url_view=urljoin(edicao.url, url_view_bruta),
                    titulo=titulo_tag.get_text(strip=True),
                    data_publicacao=data_publicacao,
                    doi=doi_montado
                ))
                
        return artigos