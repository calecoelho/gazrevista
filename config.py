"""
Configurações simples do sistema. Pode mexer aqui sem medo.
"""
import os

PASTA = os.path.dirname(os.path.abspath(__file__))

# Onde ficam o banner e o modelo da revista dentro do projeto.
PASTA_ASSETS = os.path.join(PASTA, "assets")
PASTA_MODELO = os.path.join(PASTA, "modelo")
CAMINHO_MODELO = os.path.join(PASTA_MODELO, "modelo.docx")

# O banner é procurado com um destes nomes dentro da pasta assets.
# Pode ser uma página de PDF (os links dela continuam clicáveis) ou uma imagem.
NOMES_BANNER = ["banner.pdf", "banner.png", "banner.jpg", "banner.jpeg", "banner.webp"]

# Como o banner entra na página vazia depois do índice:
#   "automatico"     -> banner em PDF cobre a página inteira; banner em imagem cabe na área livre
#   "area_livre"     -> cabe entre o logo do topo e o número da página, sem cobrir nenhum dos dois
#   "pagina_inteira" -> cobre a página toda (cobre também o logo e o número)
BANNER_MODO = "automatico"

# Só vale para "area_livre": espaço deixado (em pontos; 72 pontos = 2,5 cm) em volta do banner.
MARGEM_TOPO = 70
MARGEM_BASE = 60
MARGEM_LATERAL = 20

# Nível de compressão que aparece marcado por padrão: "leve", "medio" ou "forte".
COMPRESSAO_PADRAO = "medio"
