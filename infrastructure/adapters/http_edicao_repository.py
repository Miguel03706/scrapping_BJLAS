import requests
import re
import unicodedata  # <--- Adicionado para remover acentos
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from core.domain.entities import Edicao, Artigo
from core.domain.repositories import EdicaoRepository
from infrastructure.config import URLS, CSS_SELECTORS, TIMEOUT

def formatar_nome_arquivo(texto: str, limite: int = 50) -> str:
    """
    Padroniza o nome: tudo minúsculo, sem acentos, sem caracteres especiais, 
    espaços substituídos por '_' e tamanho limitado.
    """
    # 1. Tudo minúsculo
    texto = texto.lower()
    
    # 2. Remove acentos (ex: á -> a, ç -> c)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    
    # 3. Substitui um ou mais espaços e hífens por underscore (_)
    texto = re.sub(r'[\s\-]+', '_', texto)
    
    # 4. Remove qualquer caractere que não seja letra, número ou underscore
    texto = re.sub(r'[^a-z0-9_]', '', texto)
    
    # 5. Limita aos primeiros X caracteres e remove underscore extra no final, se houver
    return texto[:limite].rstrip('_')


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

        # Extrair o ANO usando Regex
        ano_match = re.search(r'\d{4}', data_publicacao)
        ano = ano_match.group(0) if ano_match else "ANO_DESCONHECIDO"

        artigos = []
        for article in soup.select(CSS_SELECTORS["ARTIGOS"]):
            titulo_tag = article.select_one(CSS_SELECTORS["TITULO"])
            pdf_tag = article.select_one(CSS_SELECTORS["PDF_LINK"])

            if titulo_tag and pdf_tag:
                url_view_bruta = pdf_tag['href']
                
                # --- LÓGICA INTELIGENTE DO DOI ---
                id_match = re.search(r'/view/(\d+)', url_view_bruta)
                id_artigo = id_match.group(1) if id_match else "ID_DESCONHECIDO"
                doi_montado = f"https://doi.org/10.11606/issn.1676-6288.prolam.{ano}.{id_artigo}"
                
                # --- APLICA A FORMATAÇÃO DO TÍTULO ---
                titulo_original = titulo_tag.get_text(strip=True)
                titulo_formatado = formatar_nome_arquivo(titulo_original)

                artigos.append(Artigo(
                    url_view=urljoin(edicao.url, url_view_bruta),
                    titulo=titulo_formatado,  # Passando o título já padronizado
                    data_publicacao=data_publicacao,
                    doi=doi_montado
                ))
                
        return artigos