class Edicao:
    def __init__(self, url: str):
        self.url = url


class Artigo:
    # Adicionamos o 'doi' como parâmetro opcional
    def __init__(self, url_view: str, titulo: str, data_publicacao: str, doi: str = "DOI não encontrado"):
        self.url_view = url_view
        self.titulo = titulo
        self.data_publicacao = data_publicacao
        self.doi = doi

    @property
    def url_download(self) -> str:
        return self.url_view.replace("/view/", "/download/")