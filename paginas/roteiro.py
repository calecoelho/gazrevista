"""
Página "Roteiro para redes": ideias de texto curto para divulgar a edição nas redes sociais.
O usuário escolhe a matéria de capa e as outras matérias que quer destacar.
"""
import os

import streamlit as st

import roteiro_redes as rr

st.title("🎬 Roteiro para redes")
st.write(
    "Escolha as matérias que você quer destacar e o sistema sugere textos curtos, no estilo dos "
    "roteiros que a Gazeta já publica. Cada ideia vem com um gancho diferente."
)


@st.cache_data(show_spinner="Lendo as matérias…")
def ler_materias(fontes):
    """fontes = tuple de (nome, bytes). O resultado fica guardado enquanto os arquivos forem os mesmos."""
    return rr.ler_materias_de_arquivos(list(fontes))


# ---------------------------------------------------------------------------
# 1) As matérias
# ---------------------------------------------------------------------------
enviados = st.file_uploader(
    "HTMLs das matérias (normalmente 7)", type=["html", "htm"], accept_multiple_files=True, key="roteiro_htmls"
)
if enviados:
    fontes = [(os.path.basename(f.name), f.getvalue()) for f in enviados]
    st.session_state["htmls_compartilhados"] = fontes  # a página "Montar a revista" também pode usar
else:
    fontes = st.session_state.get("htmls_compartilhados")
    if fontes:
        st.info(
            "Usando os %d HTMLs que você já enviou na página “Montar a revista”. "
            "Para usar outros, envie-os acima." % len(fontes)
        )

materias = []
if fontes:
    try:
        materias = ler_materias(tuple(fontes))
    except Exception as erro:  # noqa: BLE001
        st.error("Não consegui ler um dos HTMLs: %s" % erro)

# ---------------------------------------------------------------------------
# 2) O que destacar
# ---------------------------------------------------------------------------
capa = None
destaques = []
if materias:
    posicoes = list(range(len(materias)))

    def nome(k):
        return "%d) %s" % (k + 1, rr.rotulo(materias[k]))

    primeira_reportagem = next((k for k in posicoes if materias[k]["tipo"] == "reportagem"), 0)
    capa_k = st.selectbox(
        "Tema de capa (a matéria principal do roteiro)", posicoes, index=primeira_reportagem, format_func=nome
    )
    outras_k = st.multiselect(
        "Outras matérias para destacar (opcional, até 4)",
        [k for k in posicoes if k != capa_k],
        format_func=nome,
        max_selections=4,
        placeholder="Escolha as matérias que também devem aparecer no texto",
    )
    capa = capa_k + 1
    destaques = [k + 1 for k in outras_k]

# ---------------------------------------------------------------------------
# 3) Ajustes
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)
edicao = c1.text_input("Número da edição (opcional)", placeholder="205", key="roteiro_edicao")
quantidade = c2.slider("Quantas ideias?", min_value=1, max_value=5, value=3, key="roteiro_qtd")
extras = st.text_input(
    "Algum pedido especial? (opcional)",
    placeholder="Ex.: tom mais direto; começar por uma pergunta; mencionar o colunista logo no início",
    key="roteiro_extras",
)
with st.expander("Opções avançadas"):
    modelo_ia = st.text_input("Modelo da OpenAI", value=os.environ.get("OPENAI_MODEL", "gpt-4o"), key="roteiro_modelo")

tem_chave = bool(os.environ.get("OPENAI_API_KEY"))
if not tem_chave:
    st.warning("Falta a chave da OpenAI (OPENAI_API_KEY) nos Secrets do app. Sem ela não dá para gerar as ideias.")

# ---------------------------------------------------------------------------
# 4) Gerar
# ---------------------------------------------------------------------------
if st.button("Gerar ideias", type="primary", disabled=not (materias and capa and tem_chave)):
    with st.spinner("Escrevendo as ideias…"):
        try:
            ideias = rr.gerar_roteiros(
                materias, capa, destaques, quantidade,
                modelo_ia=modelo_ia.strip() or None, edicao=edicao.strip() or None, extras=extras,
            )
            st.session_state["roteiros"] = {
                "ideias": ideias,
                "capa": rr.rotulo(materias[capa - 1]),
                "destaques": [rr.rotulo(materias[d - 1]) for d in destaques],
            }
        except RuntimeError as erro:
            st.session_state.pop("roteiros", None)
            st.error(str(erro))

resultado = st.session_state.get("roteiros")
if resultado:
    st.success("Pronto! Passe o mouse sobre um texto e clique no ícone para copiar.")
    st.caption(
        "Capa: %s%s" % (
            resultado["capa"],
            " · Destaques: " + "; ".join(resultado["destaques"]) if resultado["destaques"] else "",
        )
    )
    for n, ideia in enumerate(resultado["ideias"], start=1):
        with st.container(border=True):
            st.markdown("**Ideia %d**" % n)
            st.code(ideia, language=None, wrap_lines=True)
            palavras = rr.contar_palavras(ideia)
            st.caption("%d palavras" % palavras)
            if palavras > rr.LIMITE_PALAVRAS_AVISO:
                st.warning("Esta ideia ficou mais longa que os exemplos. Vale encurtar ou gerar de novo.")
    todas = "\n\n".join("IDEIA %d\n\n%s" % (n, t) for n, t in enumerate(resultado["ideias"], start=1))
    st.download_button("⬇️ Baixar todas (.txt)", todas.encode("utf-8"), file_name="roteiros_redes.txt", mime="text/plain")
