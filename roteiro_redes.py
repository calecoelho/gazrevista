"""
Ideias de roteiro curto para as redes sociais, no estilo dos exemplos em exemplos/exemplos_roteiro.txt.

Quem usa escolhe a matéria de capa e, se quiser, outras matérias para destacar.
A IA (OpenAI) escreve algumas versões curtas, cada uma com um gancho diferente.

Este arquivo não depende do Streamlit: dá para testar no terminal também.
"""
import os
import re
import tempfile

import gerar_texto_publicacao as gtp
import montar_revista as mr

PASTA = os.path.dirname(os.path.abspath(__file__))
CAMINHO_EXEMPLOS = os.path.join(PASTA, "exemplos", "exemplos_roteiro.txt")

SEPARADOR = "==="
PAPEIS = {"editorial": "EDITORIAL", "opiniao": "COLUNA DE OPINIÃO", "reportagem": "REPORTAGEM"}
LIMITE_PALAVRAS_AVISO = 150  # acima disso o texto já não é "curto" como os exemplos


# ---------------------------------------------------------------------------
# Exemplos
# ---------------------------------------------------------------------------
def carregar_exemplos(caminho=CAMINHO_EXEMPLOS):
    """
    Lê o arquivo de exemplos. Cada exemplo começa com uma linha "EXEMPLO 1:", "EXEMPLO 2:"...
    Devolve a lista de textos, com os parágrafos separados por uma linha em branco.
    """
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            bruto = f.read()
    except OSError:
        return []
    pedacos = re.split(r"^\s*EXEMPLO\s*\d*\s*:?\s*$", bruto, flags=re.M | re.I)
    exemplos = []
    for pedaco in pedacos:
        paragrafos = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n|\n[ \t]+\n", pedaco)]
        paragrafos = [p for p in paragrafos if p]
        if paragrafos:
            exemplos.append("\n\n".join(paragrafos))
    return exemplos


# ---------------------------------------------------------------------------
# Ler as matérias dos HTMLs
# ---------------------------------------------------------------------------
def ler_materias_de_arquivos(arquivos):
    """arquivos = lista de (nome, bytes). Devolve as matérias na ordem natural dos nomes (materia1, materia2...)."""
    ordenados = sorted(arquivos, key=lambda a: mr.chave_natural(a[0]))
    materias = []
    with tempfile.TemporaryDirectory() as pasta:
        for nome, dados in ordenados:
            caminho = os.path.join(pasta, os.path.basename(nome))
            with open(caminho, "wb") as f:
                f.write(dados)
            materias.append(mr.extrair_materia(caminho))
    return materias


def rotulo(materia):
    """Texto curto para mostrar nas listas de escolha: tipo e título."""
    nomes = {"editorial": "editorial", "opiniao": "opinião", "reportagem": "reportagem"}
    autor = " — %s" % materia["autor"] if materia.get("autor") and materia["tipo"] == "opiniao" else ""
    return "[%s] %s%s" % (nomes.get(materia["tipo"], materia["tipo"]), materia["titulo"], autor)


# ---------------------------------------------------------------------------
# Pedido à IA
# ---------------------------------------------------------------------------
def _bloco(materia, limite):
    autor = " | autor: %s" % materia["autor"] if materia.get("autor") and materia["tipo"] != "editorial" else ""
    return "%s%s\nTítulo: %s\nTexto: %s" % (
        PAPEIS.get(materia["tipo"], materia["tipo"].upper()), autor, materia["titulo"],
        gtp.texto_da_materia(materia, limite),
    )


def montar_prompt(materias, capa, destaques, quantidade, edicao=None, extras=None, exemplos=None):
    """
    capa      = posição (a primeira é 1) da matéria de capa
    destaques = posições das outras matérias que devem aparecer no roteiro
    Devolve (instruções_do_sistema, pedido).
    """
    exemplos = exemplos if exemplos is not None else carregar_exemplos()
    exemplos_txt = "\n\n---\n\n".join(exemplos) if exemplos else "(sem exemplos)"

    capa_txt = _bloco(materias[capa - 1], 5000)
    destaques = [d for d in destaques if d != capa]
    if destaques:
        outras_txt = "\n\n".join("- " + _bloco(materias[d - 1], 1800).replace("\n", "\n  ") for d in destaques)
    else:
        outras_txt = "(nenhuma: o roteiro deve falar só da matéria de capa)"

    sistema = (
        "Você é editor de redes sociais da Gazeta do Povo e escreve textos curtos de divulgação da "
        "Gazeta do Povo Revista, revista semanal em PDF exclusiva para assinantes. Escreve em português do "
        "Brasil, em tom jornalístico, direto e convidativo."
    )
    edicao_txt = "Número da edição: %s.\n" % edicao if edicao else "O número da edição não foi informado: não cite número.\n"
    extras_txt = "\nPEDIDO EXTRA DO EDITOR (siga, sem quebrar as regras acima): %s\n" % extras.strip() if extras and extras.strip() else ""
    usuario = (
        "Escreva %d ideias de roteiro curto para divulgar esta edição nas redes sociais. "
        "Cada ideia deve ter um gancho diferente das outras (por exemplo: abrir por um dado forte, por uma "
        "pergunta, pela consequência para o leitor ou pela polêmica do tema).\n\n"
        "FORMATO DE CADA IDEIA\n"
        "- Entre 80 e 130 palavras, em 2 ou 3 parágrafos curtos, no mesmo estilo e tamanho dos exemplos.\n"
        "- O primeiro parágrafo apresenta a MATÉRIA DE CAPA e o que está em jogo nela.\n"
        "- Os demais parágrafos citam, em poucas frases, as MATÉRIAS EM DESTAQUE (e só elas). Em coluna de opinião, "
        "cite o colunista pelo nome; em editorial, diga que o editorial defende a tese.\n"
        "- Termine com uma frase curta convidando o assinante a baixar a edição (varie a frase entre as ideias; "
        "pode ser algo como \"A Gazeta do Povo Revista é exclusiva para assinantes. Baixe a sua e boa leitura!\").\n\n"
        "REGRAS\n"
        "- Use só fatos, números e nomes que estão nos textos abaixo. Não invente nada.\n"
        "- Não copie frases dos exemplos nem dos textos; reescreva.\n"
        "- Não use hashtags, emojis, títulos, listas, markdown, aspas em volta do texto nem rótulos como \"Ideia 1\".\n"
        "- Separe as ideias com uma linha contendo apenas %s\n\n" % (quantidade, SEPARADOR)
        + edicao_txt
        + extras_txt
        + "\nEXEMPLOS DE TEXTOS QUE JÁ PUBLICAMOS (imite o tom e o tamanho, não copie o conteúdo):\n\n"
        + exemplos_txt
        + "\n\n=====\nMATÉRIA DE CAPA:\n\n"
        + capa_txt
        + "\n\n=====\nMATÉRIAS EM DESTAQUE:\n\n"
        + outras_txt
    )
    return sistema, usuario


def limpar_ideia(texto):
    """Tira markdown, rótulos soltos e espaços a mais de uma ideia."""
    texto = re.sub(r"^```.*?\n|\n```$", "", (texto or "").strip(), flags=re.S).strip()
    paragrafos = [re.sub(r"[ \t]+", " ", p).strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    paragrafos = [re.sub(r"^[#>*\-\s]+", "", p).replace("**", "") for p in paragrafos]
    # rótulos que a IA às vezes escreve antes do texto (ex.: "Ideia 1:" ou "Roteiro:")
    paragrafos = [p for p in paragrafos if not (len(p) < 60 and p.endswith(":"))]
    paragrafos = [re.sub(r"^(ideia|roteiro|opção|opcao)\s*(\d+|[a-z])?\s*[:.\-–]\s*", "", p, flags=re.I) for p in paragrafos]
    return "\n\n".join(p for p in (q.strip() for q in paragrafos) if p)


def separar_ideias(resposta, quantidade):
    """Divide a resposta da IA nas ideias (separadas por ===) e limpa cada uma."""
    partes = re.split(r"^\s*={3,}\s*$", resposta or "", flags=re.M)
    ideias = [limpar_ideia(p) for p in partes]
    return [i for i in ideias if i][:quantidade]


def contar_palavras(texto):
    return len(re.findall(r"\S+", texto))


def gerar_roteiros(materias, capa, destaques, quantidade, modelo_ia=None, edicao=None, extras=None, cliente=None):
    """
    Pede as ideias à OpenAI. Devolve a lista de textos.
    Levanta RuntimeError, com uma mensagem em português, se não for possível gerar.
    """
    sistema, usuario = montar_prompt(materias, capa, destaques, quantidade, edicao, extras)
    if cliente is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("Falta a chave da OpenAI (OPENAI_API_KEY) nos Secrets do app.")
        try:
            from openai import OpenAI
        except ImportError as erro:
            raise RuntimeError("A biblioteca 'openai' não está instalada no servidor.") from erro
        cliente = OpenAI()
    try:
        resposta = cliente.chat.completions.create(
            model=modelo_ia or os.environ.get("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
            temperature=0.9,
        )
    except Exception as erro:  # noqa: BLE001
        raise RuntimeError("Não consegui falar com a OpenAI: %s" % erro) from erro
    ideias = separar_ideias(resposta.choices[0].message.content, quantidade)
    if not ideias:
        raise RuntimeError("A IA devolveu uma resposta vazia. Tente de novo.")
    return ideias
