"""
Etapa final da revista: junta a capa com a revista editada, coloca o banner na página vazia
que vem logo depois do índice e comprime o PDF.

Pode ser usado pelo app (app.py) ou direto no terminal:

    python finalizar_pdf.py --corpo revista_editada.pdf --capa capa.pdf --saida revista_final.pdf
"""
import argparse
import os
import re
import sys

import pymupdf

import config

# O MuPDF imprime avisos internos sem importância (a página sai igual); aqui eles ficam escondidos.
pymupdf.TOOLS.mupdf_display_errors(False)

# Quanto cada nível mexe nas imagens do PDF.
#   dpi_limite: imagens com resolução acima disso são reduzidas
#   dpi_alvo:   para qual resolução elas são reduzidas
#   qualidade:  qualidade do JPEG (de 1 a 100)
NIVEIS = {
    "leve": {"dpi_limite": 220, "dpi_alvo": 180, "qualidade": 85, "nome": "Leve (melhor qualidade)"},
    "medio": {"dpi_limite": 150, "dpi_alvo": 120, "qualidade": 70, "nome": "Médio (recomendado)"},
    "forte": {"dpi_limite": 110, "dpi_alvo": 96, "qualidade": 55, "nome": "Forte (menor arquivo)"},
}


def achar_banner():
    """Procura o banner dentro da pasta assets. Devolve o caminho ou None."""
    for nome in config.NOMES_BANNER:
        caminho = os.path.join(config.PASTA_ASSETS, nome)
        if os.path.isfile(caminho):
            return caminho
    return None


def _texto_sem_numeros(pagina):
    """Texto da página sem espaços e sem dígitos (o número da página no rodapé não conta)."""
    return re.sub(r"[\s\d]", "", pagina.get_text())


def achar_pagina_vazia(corpo):
    """
    Descobre qual é a página vazia logo depois do índice, no PDF da revista (sem a capa).
    Devolve a posição da página (a primeira é 0) ou None se não achar.
    """
    limite = min(len(corpo), 8)
    indice = None
    for i in range(limite):
        if "índice" in corpo[i].get_text().lower() or "indice" in corpo[i].get_text().lower():
            indice = i
            break
    if indice is None:
        return None
    for j in range(indice + 1, min(indice + 4, len(corpo))):
        if len(_texto_sem_numeros(corpo[j])) <= 3:
            return j
    return None


def _retangulo_do_banner(pagina, banner_e_pdf):
    r = pagina.rect
    modo = config.BANNER_MODO
    if modo == "automatico":
        modo = "pagina_inteira" if banner_e_pdf else "area_livre"
    if modo == "pagina_inteira":
        return r
    return pymupdf.Rect(
        r.x0 + config.MARGEM_LATERAL,
        r.y0 + config.MARGEM_TOPO,
        r.x1 - config.MARGEM_LATERAL,
        r.y1 - config.MARGEM_BASE,
    )


def banner_eh_pdf(banner_bytes):
    """Um PDF sempre começa com os caracteres %PDF."""
    return banner_bytes[:5] == b"%PDF-"


def previa_banner(banner_bytes):
    """Devolve uma imagem (PNG) para mostrar o banner na tela, seja ele imagem ou PDF."""
    if banner_eh_pdf(banner_bytes):
        with pymupdf.open(stream=banner_bytes, filetype="pdf") as doc:
            return doc[0].get_pixmap(dpi=60).tobytes("png")
    return banner_bytes


def colocar_banner(pagina, banner_bytes):
    """
    Coloca o banner na página. Se o banner for uma página de PDF, os links dele continuam
    clicáveis (o MuPDF desenha a página, mas não leva os links junto, então eles são refeitos aqui).
    Devolve a lista de links (endereços) que ficaram ativos.
    """
    destino = _retangulo_do_banner(pagina, banner_eh_pdf(banner_bytes))

    if not banner_eh_pdf(banner_bytes):
        pagina.insert_image(destino, stream=banner_bytes, keep_proportion=True, overlay=True)
        return []

    with pymupdf.open(stream=banner_bytes, filetype="pdf") as origem:
        molde = origem[0]
        pagina.show_pdf_page(destino, origem, 0, keep_proportion=True, overlay=True)

        # Onde a página do banner caiu dentro do destino (ela é centralizada e mantém a proporção)
        escala = min(destino.width / molde.rect.width, destino.height / molde.rect.height)
        x0 = destino.x0 + (destino.width - molde.rect.width * escala) / 2
        y0 = destino.y0 + (destino.height - molde.rect.height * escala) / 2

        enderecos = []
        for link in molde.get_links():
            if link.get("kind") != pymupdf.LINK_URI or not link.get("uri"):
                continue  # só os links para sites interessam aqui
            r = link["from"]
            novo = pymupdf.Rect(
                x0 + r.x0 * escala, y0 + r.y0 * escala,
                x0 + r.x1 * escala, y0 + r.y1 * escala,
            )
            pagina.insert_link({"kind": pymupdf.LINK_URI, "from": novo, "uri": link["uri"]})
            enderecos.append(link["uri"])
        return enderecos


def _nomes_de_destino(doc):
    """Alguns PDFs (como os do Google Docs) guardam o destino do link como um 'nome'. Aqui o nome vira página."""
    try:
        return doc.resolve_names() or {}
    except Exception:  # noqa: BLE001
        return {}


def _link_para_copiar(link, nomes, deslocamento):
    """
    Converte um link lido do PDF de origem no formato que o PDF final aceita.
    Devolve None para links que não dá para levar (por exemplo, para outro arquivo).
    """
    tipo = link.get("kind")
    if tipo == pymupdf.LINK_URI and link.get("uri"):
        return {"kind": pymupdf.LINK_URI, "from": link["from"], "uri": link["uri"]}

    pagina = None
    ponto = None
    zoom = 0
    if tipo in (pymupdf.LINK_GOTO, pymupdf.LINK_NAMED):
        pagina, ponto, zoom = link.get("page", -1), link.get("to"), link.get("zoom", 0)
        nome = link.get("nameddest") or link.get("name")
        if (pagina is None or pagina < 0) and nome in nomes:  # o link só tem o "nome" do destino
            destino = nomes[nome]
            pagina, ponto, zoom = destino.get("page"), destino.get("to"), destino.get("zoom", 0)
    if pagina is None or pagina < 0:
        return None
    return {
        "kind": pymupdf.LINK_GOTO,
        "from": link["from"],
        "page": pagina + deslocamento,
        "to": ponto if ponto is not None else pymupdf.Point(0, 0),
        "zoom": zoom or 0,
    }


def copiar_links(origem, final, deslocamento):
    """
    Refaz, no PDF final, todos os links do PDF de origem.
    `deslocamento` é quantas páginas vieram antes dele (a capa), porque os links internos
    (índice, "voltar ao índice") precisam apontar para a página nova.
    Devolve (copiados, perdidos), cada um com a contagem de internos e externos.
    """
    nomes = _nomes_de_destino(origem)
    copiados = {"internos": 0, "externos": 0}
    perdidos = {"internos": 0, "externos": 0}
    for i, pagina in enumerate(origem):
        for link in pagina.get_links():
            grupo = "externos" if link.get("kind") == pymupdf.LINK_URI else "internos"
            novo = _link_para_copiar(link, nomes, deslocamento)
            if novo is None:
                perdidos[grupo] += 1
                continue
            final[i + deslocamento].insert_link(novo)
            copiados[grupo] += 1
    return copiados, perdidos


def contar_links(doc):
    """Quantos links internos e externos o PDF tem."""
    n = {"internos": 0, "externos": 0}
    for pagina in doc:
        for link in pagina.get_links():
            n["externos" if link.get("kind") == pymupdf.LINK_URI else "internos"] += 1
    return n


def juntar_marcadores(capa, corpo):
    """Os marcadores do menu lateral do leitor de PDF: os da capa e depois os da revista, já na página nova."""
    toc = [list(item) for item in capa.get_toc(simple=True)]
    for nivel, titulo, pagina in corpo.get_toc(simple=True):
        toc.append([nivel, titulo, pagina + len(capa) if pagina > 0 else pagina])
    return toc


def comprimir(doc, nivel):
    """Reduz as imagens do PDF e limpa o que não é usado."""
    n = NIVEIS[nivel]
    doc.rewrite_images(
        dpi_threshold=n["dpi_limite"],
        dpi_target=n["dpi_alvo"],
        quality=n["qualidade"],
    )
    try:
        doc.subset_fonts()
    except Exception:  # noqa: BLE001  (é só um extra; se falhar, segue sem)
        pass


def finalizar(corpo_bytes, capa_bytes, banner_bytes, pagina_banner=None, nivel=None):
    """
    corpo_bytes   : PDF da revista editada (a que sai do Google Docs)
    capa_bytes    : PDF da capa (uma ou mais páginas), vai para o começo
    banner_bytes  : o banner: imagem (png/jpg) ou uma página de PDF (os links dele continuam clicáveis)
    pagina_banner : número da página vazia no PDF da revista (a primeira é 1). Vazio = acha sozinho.
    nivel         : "leve", "medio" ou "forte"

    Devolve (bytes_do_pdf_final, info), onde info tem o resumo do que foi feito.
    """
    nivel = nivel or config.COMPRESSAO_PADRAO
    if nivel not in NIVEIS:
        raise ValueError("Nível de compressão desconhecido: %s" % nivel)
    avisos = []

    corpo = pymupdf.open(stream=corpo_bytes, filetype="pdf")
    capa = pymupdf.open(stream=capa_bytes, filetype="pdf")
    if len(corpo) == 0 or len(capa) == 0:
        raise ValueError("Um dos PDFs está vazio.")

    # 1) Onde vai o banner (contando só as páginas da revista, sem a capa)
    if pagina_banner:
        pos = int(pagina_banner) - 1
        if not 0 <= pos < len(corpo):
            raise ValueError("A revista tem %d páginas; a página %s não existe." % (len(corpo), pagina_banner))
        if len(_texto_sem_numeros(corpo[pos])) > 3:
            avisos.append("A página %s não parece vazia (tem texto). O banner foi colocado mesmo assim." % pagina_banner)
    else:
        pos = achar_pagina_vazia(corpo)
        if pos is None:
            raise ValueError(
                "Não achei a página vazia depois do índice. Digite o número dela no campo "
                "'Página do banner'."
            )

    # 2) Capa + revista
    # Os links são refeitos à mão logo abaixo (links=False), para não perder nenhum tipo.
    final = pymupdf.open()
    final.insert_pdf(capa, links=False)
    final.insert_pdf(corpo, links=False)
    pos_final = len(capa) + pos

    ok_capa, perd_capa = copiar_links(capa, final, 0)
    ok_corpo, perd_corpo = copiar_links(corpo, final, len(capa))
    originais = {g: contar_links(capa)[g] + contar_links(corpo)[g] for g in ("internos", "externos")}
    copiados = {g: ok_capa[g] + ok_corpo[g] for g in ("internos", "externos")}
    perdidos = {g: perd_capa[g] + perd_corpo[g] for g in ("internos", "externos")}
    if perdidos["internos"] or perdidos["externos"]:
        avisos.append(
            "%d link(s) não puderam ser levados para o PDF final (%d internos, %d externos). "
            "Confira no PDF editado se eles estão corretos." % (
                perdidos["internos"] + perdidos["externos"], perdidos["internos"], perdidos["externos"])
        )
    try:
        marcadores = juntar_marcadores(capa, corpo)
        if marcadores:
            final.set_toc(marcadores)
    except Exception:  # noqa: BLE001  (os marcadores são um extra)
        pass

    # 3) Banner na página vazia
    pagina = final[pos_final]
    links_banner = colocar_banner(pagina, banner_bytes)
    if banner_eh_pdf(banner_bytes) and not links_banner:
        avisos.append("O banner (PDF) não tem nenhum link para site; ele entrou só como imagem.")

    # 4) Compressão
    comprimir(final, nivel)
    saida = final.tobytes(garbage=4, deflate=True, clean=True, use_objstms=1)

    info = {
        "paginas_capa": len(capa),
        "paginas_revista": len(corpo),
        "paginas_total": len(final),
        "pagina_banner_no_pdf_final": pos_final + 1,
        "pagina_banner_na_revista": pos + 1,
        "tamanho_antes": len(corpo_bytes) + len(capa_bytes),
        "tamanho_depois": len(saida),
        "nivel": nivel,
        "links_banner": links_banner,
        "links_originais": originais,
        "links_copiados": copiados,
        "links_perdidos": perdidos,
        "avisos": avisos,
    }
    return saida, info


def formatar_tamanho(n):
    return "%.1f MB" % (n / 1024 / 1024) if n >= 1024 * 1024 else "%.0f KB" % (n / 1024)


def main():
    ap = argparse.ArgumentParser(description="Junta capa + revista, coloca o banner e comprime.")
    ap.add_argument("--corpo", required=True, help="PDF da revista editada")
    ap.add_argument("--capa", required=True, help="PDF da capa")
    ap.add_argument("--banner", help="banner: imagem ou PDF de uma página (padrão: o que está em assets/)")
    ap.add_argument("--pagina-banner", type=int, help="página vazia na revista (a primeira é 1); sem isso, acha sozinho")
    ap.add_argument("--nivel", choices=list(NIVEIS), default=config.COMPRESSAO_PADRAO)
    ap.add_argument("--saida", default="revista_final.pdf")
    args = ap.parse_args()

    banner = args.banner or achar_banner()
    if not banner:
        print("ERRO: não achei o banner. Coloque-o em assets/banner.png ou use --banner.")
        sys.exit(1)

    def ler(caminho):
        with open(caminho, "rb") as f:
            return f.read()

    try:
        dados, info = finalizar(ler(args.corpo), ler(args.capa), ler(banner), args.pagina_banner, args.nivel)
    except ValueError as erro:
        print("ERRO:", erro)
        sys.exit(1)
    with open(args.saida, "wb") as f:
        f.write(dados)
    print("Pronto! Salvo em:", args.saida)
    print("Banner na página %d do PDF final. Páginas: %d. Tamanho: %s -> %s" % (
        info["pagina_banner_no_pdf_final"], info["paginas_total"],
        formatar_tamanho(info["tamanho_antes"]), formatar_tamanho(info["tamanho_depois"])))
    lo, lc = info["links_originais"], info["links_copiados"]
    print("Links mantidos: %d de %d internos (índice, voltar ao índice...) e %d de %d externos" % (
        lc["internos"], lo["internos"], lc["externos"], lo["externos"]))
    for l in info["links_banner"]:
        print("Link do banner ativo:", l)
    for a in info["avisos"]:
        print("AVISO:", a)


if __name__ == "__main__":
    main()
