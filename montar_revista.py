#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
montar_revista.py
=================
Monta a Gazeta do Povo Revista a partir de:
  1) uma pasta com os 7 HTMLs das matérias (materia1.html ... materia7.html)
  2) a revista da edição anterior (.docx), usada como modelo

O que ele faz, em linguagem simples:
  - Lê cada HTML e separa título, autor, legenda, foto, intertítulos, citação e texto.
  - Joga fora os blocos "VEJA TAMBÉM", "Leia mais" e os links promocionais.
    (Links no meio de uma frase viram texto comum: a palavra fica, o link some.)
  - Abre o modelo, troca os textos e as fotos de cada matéria e atualiza o índice.
  - Salva uma revista nova, pronta para subir no Google Docs.

Ordem das matérias (igual à revista 204):
  1 editorial | 2 e 3 opinião (com autor) | 4, 5, 6 e 7 reportagens

Uso básico:
  python montar_revista.py --html revista --modelo modelo.docx --saida revista_nova.docx

Veja o LEIAME.md para as opções (fotos, páginas do índice etc.).
"""

import argparse
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from bs4 import BeautifulSoup, NavigableString, Tag
from lxml import etree
from PIL import Image

# ---------------------------------------------------------------------------
# Constantes de XML
# ---------------------------------------------------------------------------
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
W = "{%s}" % NS["w"]
WP = "{%s}" % NS["wp"]
A = "{%s}" % NS["a"]
PIC = "{%s}" % NS["pic"]
R = "{%s}" % NS["r"]
MC = "{%s}" % NS["mc"]
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
REL_IMAGEM = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"

LARGURA_TEXTO_EMU = 5733000  # largura útil da página (A4 com margens de 2,54 cm)
POS_FUNDO_PADRAO = "-965426"  # posição vertical do fundo cinza "da própria página"

# Parágrafos que são propaganda / navegação e devem ser descartados
PADRAO_DESCARTE = re.compile(
    r"^\s*(leia|veja|confira|saiba mais|relembre|whatsapp|telegram|siga |receba|assine|inscreva|"
    r"acesse|clique)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# PARTE 1 - Ler os HTMLs
# ---------------------------------------------------------------------------
def limpar(texto):
    """Troca espaços estranhos e quebras por um espaço simples."""
    texto = (texto or "").replace("\xa0", " ").replace("​", "")
    return re.sub(r"\s+", " ", texto)


def runs_do_html(no):
    """
    Converte o conteúdo de um <p>/<li> em uma lista de pedaços [texto, negrito, italico].
    Links (<a>) viram texto comum: o link some e a palavra fica.
    """
    pedacos = []

    def andar(elemento, neg, ita):
        for filho in elemento.children:
            if isinstance(filho, NavigableString):
                pedacos.append([str(filho), neg, ita])
            elif isinstance(filho, Tag):
                nome = filho.name
                if nome in ("script", "style", "svg", "template", "button"):
                    continue
                if nome == "br":
                    pedacos.append(["\n", neg, ita])
                    continue
                andar(
                    filho,
                    neg or nome in ("strong", "b"),
                    ita or nome in ("em", "i"),
                )

    andar(no, False, False)

    # junta pedaços vizinhos com a mesma formatação e limpa os espaços
    juntos = []
    for texto, neg, ita in pedacos:
        if texto != "\n":
            texto = limpar(texto)
        if juntos and juntos[-1][1] == neg and juntos[-1][2] == ita and texto != "\n" and juntos[-1][0] != "\n":
            juntos[-1][0] += texto
        else:
            juntos.append([texto, neg, ita])
    # tira espaços do começo e do fim do parágrafo
    while juntos and not juntos[0][0].strip():
        juntos.pop(0)
    while juntos and not juntos[-1][0].strip():
        juntos.pop()
    if juntos:
        juntos[0][0] = juntos[0][0].lstrip()
        juntos[-1][0] = juntos[-1][0].rstrip()
    return juntos


def texto_dos_runs(runs):
    return "".join(r[0] for r in runs)


CHAMADA_FINAL = re.compile(
    r"\s*(confira|leia|veja|saiba mais|acesse|clique)[^.!?]*\b(link|aqui|neste endere[cç]o)\b[^.!?]*[.!?]?\s*$",
    re.IGNORECASE,
)


def tirar_chamada_final(runs, descartados):
    """Tira do fim do parágrafo frases como 'Confira outros textos da série neste link.'"""
    if not runs:
        return runs
    texto = texto_dos_runs(runs)
    m = CHAMADA_FINAL.search(texto)
    if not m or m.start() == 0:
        return runs
    descartados.append("[chamada no fim do parágrafo] " + texto[m.start():].strip()[:90])
    corte = m.start()
    novos, usados = [], 0
    for t, neg, ita in runs:
        if usados + len(t) <= corte:
            novos.append([t, neg, ita])
        elif usados < corte:
            novos.append([t[: corte - usados], neg, ita])
        usados += len(t)
    if novos:
        novos[-1][0] = novos[-1][0].rstrip()
    return novos


def eh_descartavel(no_p, runs):
    """Decide se um parágrafo é propaganda/navegação (leia mais, grupo de WhatsApp etc.)."""
    texto = texto_dos_runs(runs).strip()
    if not texto:
        return True
    if PADRAO_DESCARTE.match(texto):
        return True
    links = no_p.find_all("a")
    if links:
        texto_links = "".join(limpar(a.get_text()) for a in links).strip()
        if len(texto_links) >= 0.8 * len(texto) and len(texto) < 220:
            return True
    return False


def achar_classe(raiz, trecho):
    return raiz.find(class_=re.compile(trecho))


def baixar_url_imagem(img):
    """Pega o melhor endereço de um <img> (usa o maior do srcset, se houver)."""
    if img is None:
        return None
    src = img.get("src") or img.get("data-src") or ""
    srcset = img.get("srcset") or ""
    if srcset:
        melhor, largura = None, -1
        for parte in srcset.split(","):
            pedacos = parte.strip().split()
            if not pedacos:
                continue
            w = int(pedacos[1][:-1]) if len(pedacos) > 1 and pedacos[1].endswith("w") else 0
            if w > largura:
                melhor, largura = pedacos[0], w
        if melhor:
            src = melhor
    return src or None


def extrair_materia(caminho):
    """Lê um HTML da Gazeta do Povo e devolve um dicionário com o conteúdo da matéria."""
    with open(caminho, encoding="utf-8", errors="replace") as f:
        sopa = BeautifulSoup(f.read(), "lxml")

    h1 = sopa.find("h1")
    if h1 is None:
        raise ValueError("Não achei o título (h1) em %s" % caminho)
    secao = h1.find_parent("section") or sopa
    conteudo = achar_classe(secao, r"sectionContent") or secao

    # tipo da matéria
    perfil_topo = achar_classe(conteudo, r"headerAuthorProfileContainer")
    overline = ""
    ov = conteudo.find(class_=re.compile(r"overline-module.*overline$"))
    if ov:
        overline = limpar(ov.get_text()).strip()
    if overline.lower() == "editorial":
        tipo = "editorial"
    elif perfil_topo is not None:
        tipo = "opiniao"
    else:
        tipo = "reportagem"

    # autor ("Por Fulano")
    autor = ""
    creditos = achar_classe(conteudo, r"postCredits")
    if creditos:
        itens = [limpar(li.get_text(" ")).strip() for li in creditos.find_all("li")]
        for it in itens:
            if it.lower().startswith("por "):
                autor = it[4:].strip()
                break

    # foto principal e legenda
    legenda = ""
    cap = achar_classe(conteudo, r"postMainImageCaption")
    if cap:
        legenda = limpar(cap.get_text(" ")).strip()
        legenda = re.sub(r"\s+\)", ")", legenda)
        legenda = re.sub(r"\(\s+", "(", legenda)
    imagem_url = None
    area = conteudo.find(class_=re.compile(r"postMainImage$"))
    if area is not None:
        imagem_url = baixar_url_imagem(area.find("img"))
    if not imagem_url:
        og = sopa.find("meta", attrs={"property": "og:image"})
        imagem_url = og.get("content") if og else None

    # foto e biografia do autor (colunas de opinião)
    bio, autor_foto = "", None
    if tipo == "opiniao":
        if perfil_topo is not None:
            autor_foto = baixar_url_imagem(perfil_topo.find("img"))
        rodape = sopa.find(class_=re.compile(r"postAuthorProfileContainer"))
        if rodape is not None:
            for p in rodape.find_all("p"):
                t = limpar(p.get_text()).strip()
                if len(t) > len(bio):
                    bio = t
        if not bio and perfil_topo is not None:
            p = perfil_topo.find("p")
            bio = limpar(p.get_text()).strip() if p else ""

    # corpo
    corpo, descartados = [], []
    corpo_html = achar_classe(conteudo, r"postBodyContainer")
    if corpo_html is None:
        raise ValueError("Não achei o corpo do texto em %s" % caminho)
    for filho in corpo_html.children:
        if not isinstance(filho, Tag) or filho.name in ("template", "script", "style"):
            continue
        classes = " ".join(filho.get("class", []))
        if "postViewMore" in classes:
            descartados.append("[bloco leia mais] " + limpar(filho.get_text(" ")).strip()[:90])
            continue
        if filho.name == "p":
            runs = runs_do_html(filho)
            if eh_descartavel(filho, runs):
                if runs:
                    descartados.append("[parágrafo promocional] " + texto_dos_runs(runs)[:90])
                continue
            runs = tirar_chamada_final(runs, descartados)
            corpo.append({"tipo": "p", "runs": runs})
        elif filho.name in ("h2", "h3"):
            texto = limpar(filho.get_text(" ")).strip()
            if texto:
                corpo.append({"tipo": "h2", "texto": texto})
        elif filho.name == "blockquote":
            ps = filho.find_all("p")
            texto = limpar(ps[-1].get_text(" ") if ps else filho.get_text(" ")).strip()
            if texto:
                corpo.append({"tipo": "citacao", "texto": texto})
        elif filho.name == "ul":
            itens = []
            for li in filho.find_all("li"):
                runs = runs_do_html(li)
                if runs:
                    itens.append(runs)
            if itens:
                corpo.append({"tipo": "lista", "itens": itens})
        elif "postContentImage" in classes or filho.find("img") is not None and "postViewMore" not in classes:
            img = filho.find("img")
            url = baixar_url_imagem(img)
            legenda_img = ""
            for el in filho.find_all(["figcaption", "span", "p"]):
                t = limpar(el.get_text(" ")).strip()
                if len(t) > len(legenda_img):
                    legenda_img = t
            legenda_img = re.sub(r"\s+\)", ")", legenda_img)
            if url:
                corpo.append({"tipo": "imagem", "url": url, "legenda": legenda_img})
        else:
            texto = limpar(filho.get_text(" ")).strip()
            if texto and filho.find("p") is not None:
                # um contêiner com parágrafos dentro: trata cada um
                for p in filho.find_all("p"):
                    runs = runs_do_html(p)
                    if runs and not eh_descartavel(p, runs):
                        corpo.append({"tipo": "p", "runs": runs})

    return {
        "arquivo": os.path.basename(caminho),
        "tipo": tipo,
        "kicker": overline,
        "titulo": limpar(h1.get_text(" ")).strip(),
        "autor": autor,
        "bio": bio,
        "legenda": legenda,
        "imagem_url": imagem_url,
        "autor_foto_url": autor_foto,
        "corpo": corpo,
        "descartados": descartados,
    }


def chave_natural(nome):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", nome)]


def ler_pasta_html(pasta):
    arquivos = sorted(
        [f for f in os.listdir(pasta) if f.lower().endswith((".html", ".htm"))],
        key=chave_natural,
    )
    if len(arquivos) != 7:
        print("AVISO: esperava 7 arquivos HTML e achei %d em %s" % (len(arquivos), pasta))
    return [extrair_materia(os.path.join(pasta, f)) for f in arquivos]


# ---------------------------------------------------------------------------
# PARTE 2 - Fotos
# ---------------------------------------------------------------------------
def abrir_imagem_bytes(dados):
    """Converte qualquer imagem (jpg, png, webp...) em JPEG e devolve (bytes, largura, altura)."""
    im = Image.open(io.BytesIO(dados))
    im.load()
    if im.mode in ("RGBA", "LA", "P"):
        fundo = Image.new("RGB", im.size, (255, 255, 255))
        im_rgba = im.convert("RGBA")
        fundo.paste(im_rgba, mask=im_rgba.split()[-1])
        im = fundo
    else:
        im = im.convert("RGB")
    saida = io.BytesIO()
    im.save(saida, "JPEG", quality=92)
    return saida.getvalue(), im.size[0], im.size[1]


def obter_imagem(url, pasta_imagens, nome_base):
    """
    Procura a foto primeiro na pasta de imagens (nome_base.jpg/.png/.webp).
    Se não achar, baixa da internet. Se nada der certo, devolve None.
    """
    if pasta_imagens and os.path.isdir(pasta_imagens):
        for ext in ("jpg", "jpeg", "png", "webp"):
            cand = os.path.join(pasta_imagens, "%s.%s" % (nome_base, ext))
            if os.path.exists(cand):
                with open(cand, "rb") as f:
                    return abrir_imagem_bytes(f.read())
    if url:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return abrir_imagem_bytes(resp.read())
        except Exception as erro:  # noqa: BLE001
            print("  AVISO: não consegui baixar %s (%s)" % (url, erro))
    return None


# ---------------------------------------------------------------------------
# PARTE 3 - Ferramentas para mexer no XML do Word
# ---------------------------------------------------------------------------
def E(tag, **attrs):
    pref, nome = tag.split(":")
    el = etree.Element("{%s}%s" % (NS[pref], nome))
    for k, v in attrs.items():
        el.set(W + k, v)
    return el


def tem_ancestral(no, *tags):
    return any(a.tag in tags for a in no.iterancestors())


def textos_do_paragrafo(p):
    """Os <w:t> do parágrafo, sem os que estão dentro de desenhos/caixas de texto."""
    return [
        t
        for t in p.iter(W + "t")
        if not tem_ancestral(t, W + "drawing", MC + "AlternateContent", W + "pict")
    ]


def texto_do_paragrafo(p):
    return "".join(t.text or "" for t in textos_do_paragrafo(p))


def definir_texto(p, novo):
    """Troca o texto do parágrafo mantendo a formatação do primeiro pedaço de texto."""
    ts = textos_do_paragrafo(p)
    if not ts:
        raise ValueError("parágrafo sem texto para trocar")
    ts[0].text = novo
    ts[0].set(XML_SPACE, "preserve")
    for t in ts[1:]:
        t.text = ""


def desenhos(p):
    """Desenhos do parágrafo (sem os que estão dentro de caixas de texto)."""
    return [d for d in p.iter(W + "drawing") if not tem_ancestral(d, W + "txbxContent")]


def tem_desenho(p):
    return len(desenhos(p)) > 0


def eh_foto_topo(d):
    return d.find("wp:anchor/wp:wrapTopAndBottom", NS) is not None


def estilo(p):
    st = p.find("w:pPr/w:pStyle", NS)
    return st.get(W + "val") if st is not None else None


def tira_marcadores(p):
    """Remove marcadores (bookmarks) de um parágrafo clonado, para não duplicar."""
    for tag in ("bookmarkStart", "bookmarkEnd"):
        for b in list(p.iter(W + tag)):
            b.getparent().remove(b)


def novo_run(texto, negrito=False, italico=False):
    r = E("w:r")
    rpr = E("w:rPr")
    if negrito:
        rpr.append(E("w:b"))
    if italico:
        rpr.append(E("w:i"))
    rtl = E("w:rtl")
    rtl.set(W + "val", "0")
    rpr.append(rtl)
    r.append(rpr)
    partes = texto.split("\n")
    for i, parte in enumerate(partes):
        if i > 0:
            r.append(E("w:br"))
        if parte:
            t = E("w:t")
            t.text = parte
            t.set(XML_SPACE, "preserve")
            r.append(t)
    return r


def run_tem_desenho(r):
    return r.find(".//w:drawing", NS) is not None or r.find(".//mc:AlternateContent", NS) is not None


def preencher_paragrafo(p, runs):
    """Apaga os pedaços de texto do parágrafo e põe os novos (runs = [[texto, neg, ita], ...])."""
    for r in list(p.findall("w:r", NS)):
        if not run_tem_desenho(r):
            p.remove(r)
    for texto, neg, ita in runs:
        p.append(novo_run(texto, neg, ita))


def clonar(el):
    return copy.deepcopy(el)


def renumerar_desenhos(raiz):
    """Dá um número único para cada desenho (o Word reclama de números repetidos)."""
    contador = [1]
    vistos = set()
    for ac in raiz.iter(MC + "AlternateContent"):
        n = contador[0]
        contador[0] += 1
        for dp in ac.iter(WP + "docPr"):
            dp.set("id", str(n))
            vistos.add(id(dp))
    for dp in raiz.iter(WP + "docPr"):
        if id(dp) in vistos:
            continue
        dp.set("id", str(contador[0]))
        contador[0] += 1


# ---------------------------------------------------------------------------
# PARTE 4 - Entender a estrutura do modelo
# ---------------------------------------------------------------------------
class Slot:
    """Uma 'vaga' de matéria dentro do modelo (índices do corpo do documento)."""

    def __init__(self, inicio, fim_cabecalho, inicio_cauda):
        self.inicio = inicio  # primeiro elemento da matéria
        self.fim_cabecalho = fim_cabecalho  # último elemento do cabeçalho (título etc.)
        self.inicio_cauda = inicio_cauda  # ícone + "Voltar ao índice" (ficam como estão)
        self.cabecalho = []  # preenchido depois
        self.corpo_antigo = []


def eh_icone_pequeno(p):
    for d in desenhos(p):
        e = d.find("wp:anchor", NS)
        e = e if e is not None else d.find("wp:inline", NS)
        ext = e.find("wp:extent", NS)
        if int(ext.get("cx")) < 400000 and int(ext.get("cy")) < 400000:
            return True
    return False


def achar_slots(filhos):
    """Acha as 7 matérias do modelo pela posição dos 'Voltar ao índice'."""
    voltar = [
        i
        for i, el in enumerate(filhos)
        if el.tag == W + "p" and estilo(el) == "Heading5" and texto_do_paragrafo(el).strip() == "Voltar ao índice"
    ]
    if len(voltar) < 7:
        raise ValueError(
            "O modelo não tem 7 matérias com 'Voltar ao índice' (achei %d). "
            "Este script foi feito para a estrutura da revista 204." % len(voltar)
        )
    voltar = voltar[:7]

    # primeira matéria começa no primeiro parágrafo (depois do índice) com foto "topo e base"
    inicio = None
    for i, el in enumerate(filhos):
        if i > 1 and el.tag == W + "p" and any(eh_foto_topo(d) for d in desenhos(el)):
            inicio = i
            break
    if inicio is None:
        raise ValueError("Não achei a foto do editorial no modelo.")

    slots = []
    for k, v in enumerate(voltar):
        # ícone logo antes do "Voltar ao índice"
        cauda = v
        for j in range(v - 1, max(v - 4, -1), -1):
            if filhos[j].tag == W + "p" and eh_icone_pequeno(filhos[j]):
                cauda = j
                break
        # fim do cabeçalho: primeiro parágrafo de texto "comum" depois do primeiro elemento
        corpo_ini = None
        for j in range(inicio + 1, cauda):
            p = filhos[j]
            if (
                p.tag == W + "p"
                and estilo(p) is None
                and texto_do_paragrafo(p).strip()
                and not any(eh_foto_topo(d) for d in desenhos(p))
            ):
                corpo_ini = j
                break
        if corpo_ini is None:
            raise ValueError("Não achei o começo do texto da matéria %d no modelo." % (k + 1))
        slots.append(Slot(inicio, corpo_ini - 1, cauda))

        # onde começa a próxima: depois do "Voltar ao índice" e de separadores vazios
        prox = v + 1
        while prox < len(filhos):
            el = filhos[prox]
            vazio = el.tag == W + "p" and not texto_do_paragrafo(el).strip() and not tem_desenho(el)
            sep = el.find("w:pPr/w:sectPr", NS) is not None or el.find(".//w:br[@w:type='page']", NS) is not None
            sep = sep or el.find("w:pPr/w:pageBreakBefore", NS) is not None
            if vazio and (sep or estilo(el) in ("Heading5",)):
                prox += 1
            else:
                break
        inicio = prox
    return slots


def fundo_cinza_modelo(filhos, slots):
    """Pega uma cópia do 'fundo cinza de página inteira' usado nas colunas de opinião."""
    for el in filhos[slots[1].inicio : slots[1].inicio_cauda]:
        if el.tag != W + "p" or tem_desenho(el) is False:
            continue
        for ac in el.iter(MC + "AlternateContent"):
            anc = ac.find(".//wp:anchor", NS)
            if anc is None:
                continue
            pv = anc.find("wp:positionV/wp:posOffset", NS)
            ext = anc.find("wp:extent", NS)
            if pv is not None and pv.text == POS_FUNDO_PADRAO and int(ext.get("cy")) > 9000000:
                run = ac.getparent()
                if run.tag == W + "r":
                    return clonar(run)
    return None


def tirar_fundos_fora_do_padrao(p):
    """Remove fundos cinza 'soltos' (posições calculadas para a paginação antiga)."""
    for ac in list(p.iter(MC + "AlternateContent")):
        anc = ac.find(".//wp:anchor", NS)
        if anc is None:
            continue
        ext = anc.find("wp:extent", NS)
        if int(ext.get("cx")) < 6000000 or int(ext.get("cy")) < 9000000:
            continue  # é logo/foto, não é fundo
        pv = anc.find("wp:positionV/wp:posOffset", NS)
        if pv is not None and pv.text == POS_FUNDO_PADRAO:
            continue
        run = ac.getparent()
        if run.tag == W + "r":
            run.getparent().remove(run)


# ---------------------------------------------------------------------------
# PARTE 5 - Fotos dentro do Word
# ---------------------------------------------------------------------------
class Pacote:
    """Guarda as fotos novas e as ligações (relationships) que precisam ser criadas."""

    def __init__(self, rels_raiz):
        self.rels = rels_raiz
        self.novos_arquivos = {}  # caminho dentro do zip -> bytes
        self.contador = 0

    def adicionar_imagem(self, jpeg_bytes):
        self.contador += 1
        nome = "media/revista_foto_%02d.jpg" % self.contador
        rid = "rIdFoto%02d" % self.contador
        rel = etree.SubElement(self.rels, "{%s}Relationship" % NS["rel"])
        rel.set("Id", rid)
        rel.set("Type", REL_IMAGEM)
        rel.set("Target", nome)
        self.novos_arquivos["word/" + nome] = jpeg_bytes
        return rid


def trocar_foto(pacote, desenho, imagem):
    """Troca a foto de um desenho do Word mantendo a largura e ajustando a altura."""
    jpeg, w, h = imagem
    rid = pacote.adicionar_imagem(jpeg)
    for blip in desenho.iter(A + "blip"):
        blip.set(R + "embed", rid)
    ancora = desenho.find("wp:anchor", NS)
    ancora = ancora if ancora is not None else desenho.find("wp:inline", NS)
    ext = ancora.find("wp:extent", NS)
    cx = int(ext.get("cx"))
    cy = round(cx * h / w)
    ext.set("cy", str(cy))
    for e in desenho.iter(A + "ext"):
        if e.get("cx") is not None and e.get("cy") is not None:
            e.set("cx", str(cx))
            e.set("cy", str(cy))
    for src in desenho.iter(A + "srcRect"):
        for k in ("l", "t", "r", "b"):
            src.set(k, "0")


def foto_principal(p):
    for d in desenhos(p):
        if eh_foto_topo(d):
            return d
    return None


def desenho_inline_novo(pacote, imagem, nome):
    """Cria um desenho de foto (dentro do texto) a partir do zero."""
    jpeg, w, h = imagem
    rid = pacote.adicionar_imagem(jpeg)
    cx = LARGURA_TEXTO_EMU
    cy = round(cx * h / w)
    xml = (
        '<w:drawing xmlns:w="%(w)s" xmlns:wp="%(wp)s" xmlns:a="%(a)s" xmlns:pic="%(pic)s" xmlns:r="%(r)s">'
        '<wp:inline distT="114300" distB="114300" distL="114300" distR="114300">'
        '<wp:extent cx="%(cx)d" cy="%(cy)d"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="1" name="%(nome)s"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="%(nome)s"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%(rid)s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%(cx)d" cy="%(cy)d"/></a:xfrm>'
        '<a:prstGeom prst="rect"/></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>'
    ) % dict(w=NS["w"], wp=NS["wp"], a=NS["a"], pic=NS["pic"], r=NS["r"], cx=cx, cy=cy, nome=nome, rid=rid)
    return etree.fromstring(xml)


# ---------------------------------------------------------------------------
# PARTE 6 - Montar uma matéria no modelo
# ---------------------------------------------------------------------------
class Moldes:
    """Parágrafos do modelo usados como 'carimbo' para criar os parágrafos novos."""

    def __init__(self, filhos, slots):
        s1 = slots[0]
        corpo1 = filhos[s1.fim_cabecalho + 1 : s1.inicio_cauda]
        self.paragrafo = None
        self.branco = None
        self.citacao = None
        for el in corpo1:
            if el.tag != W + "p":
                continue
            if estilo(el) is None and texto_do_paragrafo(el).strip() and self.paragrafo is None:
                self.paragrafo = clonar(el)
            elif estilo(el) is None and not texto_do_paragrafo(el).strip() and self.branco is None:
                self.branco = clonar(el)
            elif estilo(el) == "Heading4" and self.citacao is None:
                self.citacao = clonar(el)
        # intertítulo: um Heading2 com texto em qualquer matéria
        self.intertitulo = None
        for s in slots:
            for el in filhos[s.fim_cabecalho + 1 : s.inicio_cauda]:
                if el.tag == W + "p" and estilo(el) == "Heading2" and texto_do_paragrafo(el).strip():
                    self.intertitulo = clonar(el)
                    break
            if self.intertitulo is not None:
                break
        # legenda: o parágrafo da foto do editorial (tem o texto da legenda)
        self.legenda = clonar(filhos[s1.inicio])
        tira_marcadores(self.legenda)
        for r in list(self.legenda.findall("w:r", NS)):
            if run_tem_desenho(r):
                self.legenda.remove(r)
        for nome, m in (
            ("parágrafo", self.paragrafo),
            ("espaço", self.branco),
            ("citação", self.citacao),
            ("intertítulo", self.intertitulo),
        ):
            if m is None:
                raise ValueError("Não achei no modelo um parágrafo de exemplo para: " + nome)
        for m in (self.paragrafo, self.branco, self.citacao, self.intertitulo):
            tira_marcadores(m)

    def novo_paragrafo(self, runs):
        p = clonar(self.paragrafo)
        preencher_paragrafo(p, runs)
        return p

    def novo_branco(self):
        return clonar(self.branco)

    def novo_intertitulo(self, texto):
        p = clonar(self.intertitulo)
        preencher_paragrafo(p, [[texto, False, False]])
        return p

    def nova_citacao(self, texto):
        p = clonar(self.citacao)
        preencher_paragrafo(p, [[texto, False, False]])
        # as aspas grandes ficam presas ao parágrafo (no modelo ficavam no topo da página)
        for pv in p.iter(WP + "positionV"):
            pv.set("relativeFrom", "paragraph")
            off = pv.find("wp:posOffset", NS)
            if off is not None:
                off.text = "0"
        return p

    def novo_item(self, runs):
        p = clonar(self.paragrafo)
        ppr = p.find("w:pPr", NS)
        ind = E("w:ind")
        ind.set(W + "left", "425")
        ind.set(W + "hanging", "283")
        jc = ppr.find("w:jc", NS)
        if jc is not None:
            jc.addprevious(ind)
        else:
            ppr.insert(0, ind)
        tab = E("w:r")
        tab.append(E("w:t"))
        tab[0].text = "•"
        tab.append(E("w:tab"))
        p.append(tab)
        for texto, neg, ita in runs:
            p.append(novo_run(texto, neg, ita))
        return p

    def nova_legenda(self, texto):
        p = clonar(self.legenda)
        definir_texto(p, texto)
        return p


def montar_corpo(materia, moldes, pacote, pasta_imagens, indice, fundo_cinza):
    """Cria a lista de parágrafos do corpo da matéria."""
    novos = []
    n_img = 0
    for bloco in materia["corpo"]:
        t = bloco["tipo"]
        if t == "p":
            novos += [moldes.novo_paragrafo(bloco["runs"]), moldes.novo_branco()]
        elif t == "h2":
            novos.append(moldes.novo_intertitulo(bloco["texto"]))
        elif t == "citacao":
            novos += [moldes.nova_citacao(bloco["texto"]), moldes.novo_branco()]
        elif t == "lista":
            for item in bloco["itens"]:
                novos.append(moldes.novo_item(item))
            novos.append(moldes.novo_branco())
        elif t == "imagem":
            n_img += 1
            img = obter_imagem(bloco["url"], pasta_imagens, "materia%d_img%d" % (indice, n_img))
            if img is None:
                print("  AVISO: foto do meio do texto não encontrada (matéria %d, imagem %d); pulei." % (indice, n_img))
                continue
            p = E("w:p")
            ppr = E("w:pPr")
            jc = E("w:jc")
            jc.set(W + "val", "center")
            ppr.append(jc)
            p.append(ppr)
            r = E("w:r")
            r.append(desenho_inline_novo(pacote, img, "foto_materia%d_%d" % (indice, n_img)))
            p.append(r)
            novos.append(p)
            if bloco.get("legenda"):
                novos.append(moldes.nova_legenda(bloco["legenda"]))
            novos.append(moldes.novo_branco())
    return novos


def montar_materia(filhos, slot, materia, k, moldes, pacote, pasta_imagens, fundo_cinza):
    """Troca o conteúdo de uma matéria. k = posição (1 a 7)."""
    cab = filhos[slot.inicio : slot.fim_cabecalho + 1]
    corpo_antigo = filhos[slot.fim_cabecalho + 1 : slot.inicio_cauda]
    opiniao = k in (2, 3)

    # --- legenda e foto principal
    foto_par = next((p for p in cab if p.tag == W + "p" and foto_principal(p) is not None), None)
    if foto_par is None:
        raise ValueError("Matéria %d: não achei a foto principal no modelo." % k)
    if materia.get("legenda"):
        definir_texto(foto_par, materia["legenda"])
    img = obter_imagem(materia.get("imagem_url"), pasta_imagens, "materia%d" % k)
    if img is not None:
        trocar_foto(pacote, foto_principal(foto_par), img)
    else:
        print("  AVISO: matéria %d ficou com a FOTO ANTIGA do modelo (coloque materia%d.jpg na pasta de imagens)." % (k, k))

    # --- kicker, título, autor
    titulos_h1 = [
        p
        for p in cab
        if p.tag == W + "p"
        and estilo(p) == "Heading1"
        and texto_do_paragrafo(p).strip()
        and "OPINIÃO" not in texto_do_paragrafo(p).upper()
        and "EDITORIAL" not in texto_do_paragrafo(p).upper()
    ]
    if k == 1:
        titulo_par = next(p for p in cab if p.tag == W + "p" and estilo(p) == "Title")
        definir_texto(titulo_par, materia["titulo"])
    elif opiniao:
        if len(titulos_h1) < 2:
            raise ValueError("Matéria %d: não achei autor e título no modelo." % k)
        definir_texto(titulos_h1[0], materia["autor"] or "Autor")
        definir_texto(titulos_h1[1], materia["titulo"])
    else:
        definir_texto(titulos_h1[0], materia["titulo"])
        kick = [
            p
            for p in cab
            if p.tag == W + "p" and estilo(p) == "Heading3" and texto_do_paragrafo(p).strip() and p is not foto_par
        ]
        if kick and materia.get("kicker"):
            definir_texto(kick[0], materia["kicker"])
        byline = [
            p
            for p in cab
            if p.tag == W + "p" and estilo(p) in ("Heading5", "Subtitle") and texto_do_paragrafo(p).strip()
        ]
        if byline and materia.get("autor"):
            definir_texto(byline[0], "Por " + materia["autor"])

    # --- opinião: tirar fundos cinza soltos do cabeçalho
    if opiniao:
        for p in cab:
            if p.tag == W + "p" and p is not foto_par:
                tirar_fundos_fora_do_padrao(p)

    # --- foto e texto do autor (só opinião)
    foto_autor_par = None
    autor_par = None
    if opiniao:
        for p in corpo_antigo:
            if p.tag != W + "p":
                continue
            if texto_do_paragrafo(p).strip().startswith("Autor"):
                autor_par = clonar(p)
            for d in desenhos(p):
                e = d.find("wp:anchor", NS)
                if e is not None and e.find("wp:wrapSquare", NS) is not None:
                    ext = e.find("wp:extent", NS)
                    if int(ext.get("cx")) > 600000:
                        foto_autor_par = clonar(p)

    # --- corpo novo
    novos = montar_corpo(materia, moldes, pacote, pasta_imagens, k, fundo_cinza)

    if opiniao:
        if foto_autor_par is not None:
            imga = obter_imagem(materia.get("autor_foto_url"), pasta_imagens, "materia%d_autor" % k)
            for d in desenhos(foto_autor_par):
                e = d.find("wp:anchor", NS)
                if e is not None and e.find("wp:wrapSquare", NS) is not None and imga is not None:
                    trocar_foto(pacote, d, imga)
                    # foto do autor é quadrada: mantém altura = largura
                    ext = e.find("wp:extent", NS)
                    ext.set("cy", ext.get("cx"))
                    for ee in d.iter(A + "ext"):
                        if ee.get("cx") is not None:
                            ee.set("cy", ee.get("cx"))
            if imga is None:
                print("  AVISO: matéria %d ficou com a FOTO DO AUTOR antiga (use materia%d_autor.jpg)." % (k, k))
            # mantém a foto do autor na mesma página do texto "Autor: ..."
            ppr = foto_autor_par.find("w:pPr", NS)
            if ppr is None:
                ppr = E("w:pPr")
                foto_autor_par.insert(0, ppr)
            if ppr.find("w:keepNext", NS) is None:
                kn = E("w:keepNext")
                pos = 1 if ppr.find("w:pStyle", NS) is not None else 0
                ppr.insert(pos, kn)
            novos.append(foto_autor_par)
        if autor_par is not None and materia.get("bio"):
            ts = textos_do_paragrafo(autor_par)
            if len(ts) >= 3:
                ts[0].text = "Autor"
                ts[1].text = ": "
                ts[2].text = materia["bio"]
                for t in ts[3:]:
                    t.text = ""
            elif len(ts) == 2:
                ts[0].text = "Autor"
                ts[1].text = ": " + materia["bio"]
            novos.append(autor_par)
        elif autor_par is not None:
            novos.append(autor_par)
        # fundo cinza em TODOS os parágrafos do corpo (cobre qualquer paginação)
        if fundo_cinza is not None:
            for p in novos:
                if p.tag == W + "p":
                    tirar_fundos_fora_do_padrao(p)
                    ppr = p.find("w:pPr", NS)
                    pos = list(p).index(ppr) + 1 if ppr is not None else 0
                    p.insert(pos, clonar(fundo_cinza))

    return novos


# ---------------------------------------------------------------------------
# PARTE 7 - Índice
# ---------------------------------------------------------------------------
def atualizar_indice(tabela, materias, paginas=None):
    linhas = tabela.findall("w:tr", NS)
    for i, tr in enumerate(linhas[:7]):
        m = materias[i]
        if m["tipo"] == "editorial":
            texto = "Editorial: " + m["titulo"]
        elif m["tipo"] == "opiniao":
            texto = (m["autor"] + ": " if m["autor"] else "") + m["titulo"]
        else:
            texto = m["titulo"]
        hl = tr.find(".//w:hyperlink", NS)
        ts = [t for t in hl.iter(W + "t")]
        ts[0].text = texto
        ts[0].set(XML_SPACE, "preserve")
        for t in ts[1:]:
            t.text = ""
        if paginas and i < len(paginas) and paginas[i]:
            celulas = tr.findall("w:tc", NS)
            tnum = [t for t in celulas[-1].iter(W + "t")]
            if tnum:
                tnum[0].text = "%02d" % int(paginas[i])
                for t in tnum[1:]:
                    t.text = ""


# ---------------------------------------------------------------------------
# PARTE 8 - Montar a revista inteira
# ---------------------------------------------------------------------------
def montar_revista(modelo, materias, pasta_imagens, paginas=None):
    """Devolve os bytes do .docx novo."""
    with zipfile.ZipFile(modelo) as z:
        entradas = {n: z.read(n) for n in z.namelist()}
        ordem = z.namelist()

    doc = etree.fromstring(entradas["word/document.xml"])
    rels = etree.fromstring(entradas["word/_rels/document.xml.rels"])
    corpo = doc.find("w:body", NS)
    filhos = list(corpo)

    slots = achar_slots(filhos)
    if len(materias) < 7:
        raise ValueError("Preciso de 7 matérias, recebi %d." % len(materias))
    esperado = ["editorial", "opiniao", "opiniao", "reportagem", "reportagem", "reportagem", "reportagem"]
    for i, (m, e) in enumerate(zip(materias, esperado), start=1):
        if m["tipo"] != e:
            print(
                "AVISO: a matéria %d (%s) parece ser '%s', mas a vaga %d do modelo é de '%s'. "
                "Confira a ordem dos arquivos." % (i, m.get("arquivo", "?"), m["tipo"], i, e)
            )

    moldes = Moldes(filhos, slots)
    fundo = fundo_cinza_modelo(filhos, slots)
    if fundo is None:
        print("AVISO: não achei o fundo cinza das colunas de opinião no modelo; ficarão sem fundo.")
    pacote = Pacote(rels)

    # monta tudo primeiro (usa os elementos originais) e só depois troca no documento
    resultados = []
    for k, (slot, materia) in enumerate(zip(slots, materias[:7]), start=1):
        print("Montando matéria %d: %s" % (k, materia["titulo"][:70]))
        resultados.append(montar_materia(filhos, slot, materia, k, moldes, pacote, pasta_imagens, fundo))

    for slot, novos in reversed(list(zip(slots, resultados))):
        antigos = filhos[slot.fim_cabecalho + 1 : slot.inicio_cauda]
        ponto = antigos[0]
        for el in novos:
            ponto.addprevious(el)
        for el in antigos:
            corpo.remove(el)

    atualizar_indice(filhos[1], materias, paginas)
    renumerar_desenhos(doc)

    # tipos de arquivo: garante que .jpg está declarado
    tipos = etree.fromstring(entradas["[Content_Types].xml"])
    ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    if not any(d.get("Extension", "").lower() == "jpg" for d in tipos.findall("{%s}Default" % ct_ns)):
        d = etree.SubElement(tipos, "{%s}Default" % ct_ns)
        d.set("Extension", "jpg")
        d.set("ContentType", "image/jpeg")
    entradas["[Content_Types].xml"] = etree.tostring(tipos, xml_declaration=True, encoding="UTF-8", standalone=True)
    entradas["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
    entradas["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    entradas.update(pacote.novos_arquivos)

    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in ordem + [n for n in entradas if n not in ordem]:
            z.writestr(nome, entradas[nome])
    return saida.getvalue()


# ---------------------------------------------------------------------------
# PARTE 9 - Páginas do índice (opcional, usa o LibreOffice)
# ---------------------------------------------------------------------------
def calcular_paginas(docx_bytes, materias, deslocamento=1):
    """
    Converte a revista em PDF com o LibreOffice e procura em que página começa cada título.
    O número impresso no rodapé = página do PDF + deslocamento (a revista começa a contar da 2).
    """
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftotext = shutil.which("pdftotext")
    if not soffice or not pdftotext:
        print("AVISO: precisa de LibreOffice (soffice) e pdftotext para calcular as páginas; mantive o índice.")
        return None
    with tempfile.TemporaryDirectory() as tmp:
        caminho = os.path.join(tmp, "rev.docx")
        with open(caminho, "wb") as f:
            f.write(docx_bytes)
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, caminho],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        pdf = os.path.join(tmp, "rev.pdf")
        if not os.path.exists(pdf):
            print("AVISO: o LibreOffice não gerou o PDF; mantive o índice.")
            return None
        txt = subprocess.run([pdftotext, "-layout", pdf, "-"], capture_output=True, text=True).stdout
        paginas_txt = [re.sub(r"\s+", "", p).lower() for p in txt.split("\f")]
    resultado = []
    for m in materias[:7]:
        alvo = re.sub(r"\s+", "", m["titulo"]).lower()[:45]
        achada = None
        for i, pg in enumerate(paginas_txt, start=1):
            if i <= 2:
                continue  # capa e índice
            if alvo in pg:
                achada = i + deslocamento
                break
        resultado.append(achada)
    return resultado


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Monta a Gazeta do Povo Revista a partir dos HTMLs das matérias.")
    ap.add_argument("--html", help="pasta com os 7 HTMLs (materia1.html ... materia7.html)")
    ap.add_argument("--json", help="usar um conteudo.json já revisado em vez de ler os HTMLs")
    ap.add_argument("--modelo", required=True, help="revista da edição anterior (.docx)")
    ap.add_argument("--saida", default="revista_nova.docx", help="arquivo de saída")
    ap.add_argument("--imagens", help="pasta com as fotos (materia1.jpg, materia2.jpg, materia2_autor.jpg, materia7_img1.jpg...)")
    ap.add_argument("--paginas", help="páginas do índice separadas por vírgula, ex.: 4,10,16,22,30,38,45")
    ap.add_argument("--calcular-paginas", action="store_true", help="calcula as páginas do índice com o LibreOffice")
    ap.add_argument("--deslocamento", type=int, default=1, help="soma ao número da página do PDF (padrão 1)")
    args = ap.parse_args()

    if args.json:
        with open(args.json, encoding="utf-8") as f:
            materias = json.load(f)["materias"]
    elif args.html:
        materias = ler_pasta_html(args.html)
    else:
        ap.error("informe --html ou --json")

    # guarda o conteúdo lido, para você poder revisar/editar
    pasta_saida = os.path.dirname(os.path.abspath(args.saida))
    os.makedirs(pasta_saida, exist_ok=True)
    caminho_json = os.path.splitext(args.saida)[0] + "_conteudo.json"
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump({"materias": materias}, f, ensure_ascii=False, indent=2)

    for i, m in enumerate(materias, start=1):
        print("%d) [%s] %s" % (i, m["tipo"], m["titulo"]))
        for d in m.get("descartados", []):
            print("     descartado:", d)

    paginas = [int(x) for x in args.paginas.split(",")] if args.paginas else None
    dados = montar_revista(args.modelo, materias, args.imagens, paginas)

    if args.calcular_paginas:
        calc = calcular_paginas(dados, materias, args.deslocamento)
        if calc:
            print("Páginas calculadas para o índice:", calc)
            dados = montar_revista(args.modelo, materias, args.imagens, calc)

    with open(args.saida, "wb") as f:
        f.write(dados)
    print("\nPronto! Revista salva em:", args.saida)
    print("Conteúdo lido (para revisar):", caminho_json)


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        print("ERRO:", erro)
        sys.exit(1)
