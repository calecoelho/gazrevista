"""
Gazeta do Povo Revista - app interno (Streamlit).

Aba 1: monta a revista em .docx a partir dos HTMLs + gera o texto de publicação.
Aba 2: recebe o PDF da revista editada + a capa, coloca o banner, junta tudo e comprime.

Para abrir no seu computador:   streamlit run app.py
"""
import contextlib
import hmac
import io
import os
import tempfile
import time

import pymupdf
import streamlit as st

import config
import finalizar_pdf
import gerar_texto_publicacao as gtp
import montar_revista as mr

st.set_page_config(page_title="Gazeta Revista", page_icon="📰", layout="centered")

# Lê o arquivo .env (quando você roda no seu computador) para ter a chave e a senha por lá.
gtp.carregar_env()


# ---------------------------------------------------------------------------
# Segredos (senha e chave da OpenAI)
# ---------------------------------------------------------------------------
def segredo(nome):
    """Procura primeiro nos 'Secrets' do Streamlit e depois nas variáveis de ambiente (.env)."""
    try:
        valor = st.secrets.get(nome)
    except Exception:  # noqa: BLE001  (sem arquivo de secrets: tudo bem)
        valor = None
    return str(valor) if valor else os.environ.get(nome)


# A chave da OpenAI que está nos Secrets passa a valer para o script que escreve a abertura.
_chave = segredo("OPENAI_API_KEY")
if _chave:
    os.environ["OPENAI_API_KEY"] = _chave


def pedir_senha():
    """Só deixa passar quem digitou a senha certa. Se não houver senha configurada, bloqueia."""
    esperada = segredo("APP_PASSWORD")
    if not esperada:
        st.error(
            "Este app ainda não tem senha configurada. Defina `APP_PASSWORD` nos Secrets "
            "(ou no arquivo .env, se estiver rodando no seu computador)."
        )
        st.stop()
    if st.session_state.get("entrou"):
        return
    st.title("📰 Gazeta Revista")
    with st.form("entrada"):
        digitada = st.text_input("Senha", type="password")
        enviar = st.form_submit_button("Entrar")
    if enviar:
        if hmac.compare_digest(digitada.encode("utf-8"), esperada.encode("utf-8")):
            st.session_state["entrou"] = True
            st.rerun()
        time.sleep(1.5)  # atrapalha quem fica tentando senhas
        st.error("Senha incorreta.")
    st.stop()


pedir_senha()

# ---------------------------------------------------------------------------
# Tela
# ---------------------------------------------------------------------------
col_titulo, col_sair = st.columns([5, 1])
col_titulo.title("📰 Gazeta Revista")
if col_sair.button("Sair"):
    st.session_state.clear()
    st.rerun()

aba1, aba2 = st.tabs(["1. Montar a revista (Word)", "2. Finalizar o PDF"])


def tamanho(n):
    return finalizar_pdf.formatar_tamanho(n)


# ---------------------------------------------------------------------------
# Aba 1 - HTMLs -> .docx + texto de publicação
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def ler_titulos(arquivos):
    """arquivos = tuple de (nome, bytes). Devolve [(posição, nome, tipo, título), ...]."""
    with tempfile.TemporaryDirectory() as pasta:
        for nome, dados in arquivos:
            with open(os.path.join(pasta, nome), "wb") as f:
                f.write(dados)
        itens = []
        for i, caminho in enumerate(gtp.listar_htmls([pasta]), start=1):
            m = mr.extrair_materia(caminho)
            itens.append((i, os.path.basename(caminho), m["tipo"], m["titulo"]))
        return itens


def montar_edicao(htmls, fotos, modelo_bytes, edicao, subtitulo, paginas, principal, usar_ia, modelo_ia, calcular):
    """Faz o trabalho da aba 1 e devolve um dicionário com os arquivos prontos e o relatório."""
    relatorio = io.StringIO()
    with contextlib.redirect_stdout(relatorio), tempfile.TemporaryDirectory() as tmp:
        pasta_html = os.path.join(tmp, "htmls")
        pasta_fotos = os.path.join(tmp, "fotos")
        os.makedirs(pasta_html)
        os.makedirs(pasta_fotos)
        for f in htmls:
            with open(os.path.join(pasta_html, os.path.basename(f.name)), "wb") as saida:
                saida.write(f.getvalue())
        for f in fotos:
            with open(os.path.join(pasta_fotos, os.path.basename(f.name).lower()), "wb") as saida:
                saida.write(f.getvalue())

        materias = mr.ler_pasta_html(pasta_html)
        for i, m in enumerate(materias, start=1):
            print("%d) [%s] %s" % (i, m["tipo"], m["titulo"]))
            for d in m.get("descartados", []):
                print("     descartado:", d)

        lista_paginas = [int(x) for x in paginas.replace(" ", "").split(",") if x] if paginas else None
        docx = mr.montar_revista(io.BytesIO(modelo_bytes), materias, pasta_fotos, lista_paginas)
        if calcular and not lista_paginas:
            calc = mr.calcular_paginas(docx, materias)
            if calc:
                print("Páginas calculadas para o índice:", calc)
                docx = mr.montar_revista(io.BytesIO(modelo_bytes), materias, pasta_fotos, calc)

        print("\nTexto de publicação:")
        texto = gtp.gerar_texto_da_edicao(
            materias, principal, edicao or None, subtitulo or None,
            modelo_ia=modelo_ia, usar_ia=usar_ia,
        )
    return {"docx": docx, "txt": texto, "relatorio": relatorio.getvalue(), "edicao": edicao or "nova"}


with aba1:
    st.write("Suba os HTMLs das matérias. O sistema monta a revista em Word e o texto para publicar no site.")

    htmls = st.file_uploader("HTMLs das matérias (normalmente 7)", type=["html", "htm"], accept_multiple_files=True)
    fotos = st.file_uploader(
        "Fotos (opcional): materia1.jpg, materia2.jpg, materia2_autor.jpg…",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    modelo_bytes = None
    if os.path.isfile(config.CAMINHO_MODELO):
        with open(config.CAMINHO_MODELO, "rb") as f:
            modelo_bytes = f.read()
        st.caption("Modelo da revista: o que está guardado no sistema (modelo/modelo.docx).")
    else:
        enviado = st.file_uploader("Modelo da revista (a edição anterior, em .docx)", type=["docx"])
        modelo_bytes = enviado.getvalue() if enviado else None

    c1, c2 = st.columns(2)
    edicao = c1.text_input("Número da edição", placeholder="205")
    subtitulo = c2.text_input("Subtítulo (opcional)", placeholder="O peso do STF nas eleições")

    principal = None
    if htmls:
        try:
            titulos = ler_titulos(tuple(sorted((os.path.basename(f.name), f.getvalue()) for f in htmls)))
        except Exception as erro:  # noqa: BLE001
            titulos = []
            st.error("Não consegui ler um dos HTMLs: %s" % erro)
        if len(titulos) not in (0, 7):
            st.warning("Esperava 7 matérias e li %d." % len(titulos))
        if titulos:
            padrao = next((i - 1 for i, _, tipo, _ in titulos if tipo == "reportagem"), 0)
            escolha = st.selectbox(
                "Matéria principal (manchete)",
                options=range(len(titulos)),
                index=padrao,
                format_func=lambda k: "%d) %s — %s" % (titulos[k][0], titulos[k][1], titulos[k][3]),
            )
            principal = titulos[escolha][0]

    with st.expander("Opções avançadas"):
        paginas = st.text_input("Páginas do índice (opcional)", placeholder="4,10,19,24,38,53,61")
        pode_calcular = bool(mr.shutil.which("soffice") or mr.shutil.which("libreoffice"))
        calcular = st.checkbox(
            "Calcular as páginas do índice automaticamente",
            value=False,
            disabled=not pode_calcular,
            help=None if pode_calcular else "Precisa do LibreOffice, que não está instalado neste servidor.",
        )
        tem_chave = bool(os.environ.get("OPENAI_API_KEY"))
        usar_ia = st.checkbox(
            "Escrever o texto de abertura com a IA (OpenAI)",
            value=tem_chave,
            disabled=not tem_chave,
            help=None if tem_chave else "Falta a chave OPENAI_API_KEY nos Secrets.",
        )
        modelo_ia = st.text_input("Modelo da OpenAI", value=os.environ.get("OPENAI_MODEL", "gpt-4o"))

    pronto = bool(htmls and modelo_bytes and principal)
    if st.button("Montar revista e texto", type="primary", disabled=not pronto):
        with st.spinner("Montando… isso leva alguns segundos."):
            try:
                st.session_state["res1"] = montar_edicao(
                    htmls, fotos, modelo_bytes, edicao.strip(), subtitulo.strip(),
                    paginas.strip(), principal, usar_ia, modelo_ia.strip() or None, calcular,
                )
            except (ValueError, SystemExit) as erro:
                st.session_state.pop("res1", None)
                st.error("Não deu certo: %s" % erro)
            except Exception as erro:  # noqa: BLE001
                st.session_state.pop("res1", None)
                st.error("Algo inesperado aconteceu: %s" % erro)

    res = st.session_state.get("res1")
    if res:
        st.success("Pronto! Baixe os arquivos abaixo.")
        d1, d2 = st.columns(2)
        d1.download_button(
            "⬇️ Revista (.docx)", res["docx"], file_name="revista_%s.docx" % res["edicao"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        d2.download_button(
            "⬇️ Texto para publicar (.txt)", res["txt"].encode("utf-8"),
            file_name="texto_para_publicar.txt", mime="text/plain",
        )
        with st.expander("Ver o que foi lido e o que foi descartado"):
            st.code(res["relatorio"] or "(sem avisos)")
        st.info(
            "Abra o .docx no Google Docs, faça os ajustes e exporte em PDF. "
            "Depois use a aba 2 para finalizar."
        )

# ---------------------------------------------------------------------------
# Aba 2 - PDF editado + capa -> PDF final
# ---------------------------------------------------------------------------
with aba2:
    st.write(
        "Suba o PDF da revista editada e a capa. O sistema junta tudo, coloca o banner na página "
        "vazia depois do índice e comprime o arquivo."
    )
    corpo = st.file_uploader("PDF da revista editada", type=["pdf"], key="corpo")
    capa = st.file_uploader("PDF da capa", type=["pdf"], key="capa")

    caminho_banner = finalizar_pdf.achar_banner()
    banner_bytes = None
    if caminho_banner:
        with open(caminho_banner, "rb") as f:
            banner_bytes = f.read()
        st.image(finalizar_pdf.previa_banner(banner_bytes), caption="Banner que será usado (assets/%s)" % os.path.basename(caminho_banner), width=300)
    else:
        st.warning("Nenhum banner guardado no sistema (assets/banner.pdf ou banner.png). Envie um abaixo.")
    with st.expander("Usar outro banner só desta vez" if caminho_banner else "Enviar o banner", expanded=not caminho_banner):
        outro = st.file_uploader("Banner (PDF de uma página ou imagem)", type=["pdf", "png", "jpg", "jpeg", "webp"], key="banner")
        if outro:
            banner_bytes = outro.getvalue()
            st.image(finalizar_pdf.previa_banner(banner_bytes), width=300)

    c1, c2 = st.columns(2)
    nivel = c1.radio(
        "Compressão",
        options=list(finalizar_pdf.NIVEIS),
        index=list(finalizar_pdf.NIVEIS).index(config.COMPRESSAO_PADRAO),
        format_func=lambda k: finalizar_pdf.NIVEIS[k]["nome"],
    )
    pagina = c2.number_input(
        "Página do banner (0 = achar sozinho)", min_value=0, value=0, step=1,
        help="É a página vazia depois do índice, contada no PDF da revista (sem a capa). Normalmente é a 2.",
    )

    if st.button("Finalizar PDF", type="primary", disabled=not (corpo and capa and banner_bytes)):
        with st.spinner("Juntando, colocando o banner e comprimindo…"):
            try:
                dados, info = finalizar_pdf.finalizar(
                    corpo.getvalue(), capa.getvalue(), banner_bytes, int(pagina) or None, nivel
                )
                pdf = pymupdf.open(stream=dados, filetype="pdf")
                previa = pdf[info["pagina_banner_no_pdf_final"] - 1].get_pixmap(dpi=60).tobytes("png")
                st.session_state["res2"] = {"pdf": dados, "info": info, "previa": previa}
            except ValueError as erro:
                st.session_state.pop("res2", None)
                st.error(str(erro))
            except Exception as erro:  # noqa: BLE001
                st.session_state.pop("res2", None)
                st.error("Não consegui processar esses PDFs: %s" % erro)

    res2 = st.session_state.get("res2")
    if res2:
        info = res2["info"]
        for aviso in info["avisos"]:
            st.warning(aviso)
        lo, lc = info["links_originais"], info["links_copiados"]
        if lc["internos"] == lo["internos"] and lc["externos"] == lo["externos"]:
            st.success(
                "Links mantidos: %d internos (índice e “voltar ao índice”) e %d externos (sites)."
                % (lc["internos"], lc["externos"])
            )
        if info["links_banner"]:
            st.success("Link(s) do banner ativo(s): " + ", ".join(info["links_banner"]))
        m1, m2, m3 = st.columns(3)
        m1.metric("Páginas", info["paginas_total"])
        m2.metric("Antes", tamanho(info["tamanho_antes"]))
        m3.metric("Depois", tamanho(info["tamanho_depois"]))
        st.download_button(
            "⬇️ Revista final (.pdf)", res2["pdf"], file_name="revista_final.pdf", mime="application/pdf"
        )
        st.image(res2["previa"], caption="Página %d: onde o banner ficou" % info["pagina_banner_no_pdf_final"], width=260)
