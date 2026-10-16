#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_texto_publicacao.py
=========================
Gera o texto de publicação da Gazeta do Povo Revista no site (blocos do WordPress),
no mesmo formato dos três exemplos que você enviou.

O arquivo de saída, texto_para_publicar.txt, tem esta ordem:
  1. Texto de abertura (escrito por uma IA da OpenAI, com base nas matérias)
  2. Frase fixa "A Gazeta do Povo Revista é exclusiva para assinantes. Baixe a sua:"
  3. Link "BAIXE A NOVA EDIÇÃO DA GAZETA REVISTA EM PDF"
  4. "Nessa edição você vai ler:" + lista (montada sozinha a partir dos títulos dos HTMLs)
  5. Título "EDIÇÃO NNN: ..." (subtítulo)
  6. Foto com legenda
  7. Parágrafo fixo sobre como receber a revista

O que não dá para saber de antemão fica com um aviso entre parênteses, por exemplo
"(poste a foto aqui)", para você trocar na hora de publicar.

Uso básico:
  python gerar_texto_publicacao.py --html htmls --edicao 205

Antes, na primeira vez:
  pip install openai
e configure a chave da OpenAI (veja o LEIAME_PUBLICACAO.md).

Este script usa as funções de leitura de HTML do montar_revista.py.
Deixe os dois arquivos na mesma pasta.
"""

import argparse
import html
import os
import re
import sys
import unicodedata

try:
    from montar_revista import chave_natural, extrair_materia, texto_dos_runs
except ImportError:
    print("ERRO: não achei o montar_revista.py. Deixe os dois scripts na mesma pasta.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Textos fixos (iguais nos três exemplos)
# ---------------------------------------------------------------------------
FRASE_ASSINANTES = "A Gazeta do Povo Revista é exclusiva para assinantes. Baixe a sua:"
TEXTO_LINK_PDF = "BAIXE A NOVA EDIÇÃO DA GAZETA REVISTA EM PDF"
TITULO_LISTA = "Nessa edição você vai ler:"

PARAGRAFO_COMO_RECEBER = (
    "As edições da Gazeta do Povo Revista estão disponíveis para download em PDF pelos nossos "
    "assinantes todos os sábados pela manhã no site do jornal. Também é possível se inscrever para "
    "ser lembrado de baixar o arquivo. Você pode entrar em um de nossos grupos no "
    '<a href="https://especiais.gazetadopovo.com.br/noticias-por-mensagem" target="_blank" '
    'rel="noreferrer noopener">Whatsapp</a> ou em nosso canal no '
    '<a href="https://t.me/gazeta_do_povo" target="_blank" rel="noreferrer noopener">Telegram</a>. '
    "Se preferir receber por e-mail, você pode se inscrever na newsletter exclusiva para receber o "
    "link de download. Inscreva-se no box abaixo ou "
    '<a href="https://www.gazetadopovo.com.br/newsletter/?newsletter=gazeta-do-povo-revista&amp;" '
    'target="_blank" rel="noreferrer noopener">pelo link</a>.'
)

# Avisos para o que não dá para preencher de antemão
AVISO_FOTO = "(poste a foto aqui)"
AVISO_LEGENDA = "(poste a legenda aqui)"
AVISO_LINK_PDF = "(poste o link aqui)"
AVISO_SUBTITULO = "(poste o subtítulo aqui)"
AVISO_EDICAO = "(número da edição)"
AVISO_ABERTURA = "(escreva o texto de abertura aqui)"

# Aberturas reais usadas como exemplo para a IA imitar o tom
EXEMPLOS_ABERTURA = [
    (
        "O fim de semana decisivo para a política brasileira chegou e nesta edição da Gazeta do Povo "
        "Revista você confere como as mais recentes crises do STF devem afetar o resultado das eleições. "
        "Quem perde e quem sai ganhando neste cenário de desconfiança com o Judiciário?\n\n"
        "Além disso, o colunista Marcio Campos escreve sobre outro tema quente da semana: o uso "
        "eleitoreiro de Nossa Senhora Aparecida. Outro colunista, Rodrigo Constantino, mostra a "
        "estratégia de Flávio Bolsonaro para unir a direita neste pleito."
    ),
    (
        "O STF pode encarar um cenário bem menos amigável nos próximos anos. Um levantamento exclusivo "
        "da Gazeta do Povo mostra que 98 candidatos ao Senado, agora, em 2026, são favoráveis ao "
        "impeachment de ministros da Corte. O número é especialmente importante porque a eleição deste "
        "ano pode levar a uma renovação de dois terços da Casa legislativa, que é responsável "
        "justamente por dar início aos processos de derrubada de membros do STF.\n\n"
        "A possível guinada pró-impeachment no Supremo é o tema de capa da edição 202 da Gazeta do Povo "
        "Revista, que já está disponível para os assinantes. Baixe a sua edição e boa leitura!"
    ),
    (
        "Foi uma semana histórica para o Brasil, mas com um gosto amargo de impunidade. Na edição desta "
        "semana, a Gazeta do Povo Revista traz todo o desdobramento da sessão do STF que analisaria o "
        "pedido de investigação do ministro Alexandre de Moraes. Você confere um editorial que "
        "argumenta como alguns membros da Corte atuaram para blindar os erros do STF, transformando o "
        "encontro em um espetáculo deprimente e nada produtivo.\n\n"
        "Além disso, nossos colunistas debatem alguns dos episódios mais marcantes da sessão, como o "
        "pedido de desculpas de Carmén Lúcia e a polêmica frase de Gilmar Mendes sobre \"ética na máfia\"."
    ),
]


# ---------------------------------------------------------------------------
# Chave da OpenAI (arquivo .env)
# ---------------------------------------------------------------------------
def carregar_env():
    """
    Lê o arquivo .env (na pasta onde você roda o script ou na pasta do script) e põe as linhas
    NOME=valor no ambiente. Não troca variáveis que já estejam configuradas no computador.
    """
    pastas = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for pasta in pastas:
        caminho = os.path.join(pasta, ".env")
        if not os.path.isfile(caminho):
            continue
        with open(caminho, encoding="utf-8-sig") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                nome, valor = linha.split("=", 1)
                nome = nome.replace("export ", "").strip()
                valor = valor.strip().strip('"').strip("'")
                if nome and nome not in os.environ:
                    os.environ[nome] = valor
        return caminho
    return None


# ---------------------------------------------------------------------------
# Ler as matérias
# ---------------------------------------------------------------------------
def listar_htmls(caminhos):
    """Aceita pastas e/ou arquivos .html e devolve a lista de arquivos, na ordem natural."""
    arquivos = []
    for caminho in caminhos:
        if os.path.isdir(caminho):
            nomes = sorted(
                [f for f in os.listdir(caminho) if f.lower().endswith((".html", ".htm"))],
                key=chave_natural,
            )
            arquivos += [os.path.join(caminho, n) for n in nomes]
        elif os.path.isfile(caminho):
            arquivos.append(caminho)
        else:
            print("AVISO: não achei %s" % caminho)
    return arquivos


def ler_materias(caminhos):
    materias = []
    for arq in listar_htmls(caminhos):
        try:
            materias.append(extrair_materia(arq))
        except Exception as erro:  # noqa: BLE001
            print("AVISO: pulei %s (%s)" % (arq, erro))
    if not materias:
        print("ERRO: não achei nenhuma matéria nos HTMLs informados.")
        sys.exit(1)
    return materias


def texto_da_materia(materia, limite=700):
    """Parágrafos da matéria, até um limite de caracteres, para a IA entender do que se trata."""
    partes = []
    for bloco in materia["corpo"]:
        if bloco["tipo"] == "p":
            partes.append(texto_dos_runs(bloco["runs"]))
        elif bloco["tipo"] == "lista":
            partes += [texto_dos_runs(item) for item in bloco["itens"]]
        if sum(len(p) for p in partes) >= limite:
            break
    return " ".join(partes)[:limite]


def escolher_principal(materias, valor):
    """
    Descobre qual é a matéria principal (a manchete).
    `valor` pode ser o nome do arquivo (materia3.html ou materia3) ou a posição (3).
    Sem `valor`, usa a primeira reportagem. Devolve a posição (começando em 1).
    """
    if valor:
        valor = str(valor).strip()
        if valor.isdigit():
            n = int(valor)
            if 1 <= n <= len(materias):
                return n
        else:
            alvo = os.path.splitext(valor.lower())[0]
            for i, m in enumerate(materias, start=1):
                if os.path.splitext(m["arquivo"].lower())[0] == alvo:
                    return i
        print("ERRO: não achei a matéria principal '%s'. Os arquivos lidos são:" % valor)
        for i, m in enumerate(materias, start=1):
            print("  %d) %s" % (i, m["arquivo"]))
        sys.exit(1)
    for i, m in enumerate(materias, start=1):
        if m["tipo"] == "reportagem":
            return i
    return 1


# ---------------------------------------------------------------------------
# A lista "Nessa edição você vai ler"
# ---------------------------------------------------------------------------
def montar_itens_lista(materias, manchete):
    """
    Devolve a lista de itens [(rotulo_em_negrito, titulo), ...] na ordem dos exemplos:
      Manchete, Editorial, colunistas (nome em negrito) e depois as outras reportagens.
    `manchete` é o número da matéria (começando em 1) que será a manchete.
    """
    itens = []
    idx_manchete = manchete - 1 if manchete else None
    editorial_e_manchete = idx_manchete is not None and materias[idx_manchete]["tipo"] == "editorial"

    if idx_manchete is not None:
        m = materias[idx_manchete]
        rotulo = "Manchete/editorial:" if editorial_e_manchete else "Manchete:"
        itens.append((rotulo, m["titulo"]))

    for i, m in enumerate(materias):
        if i == idx_manchete:
            continue
        if m["tipo"] == "editorial":
            itens.append(("Editorial:", m["titulo"]))
    for i, m in enumerate(materias):
        if i == idx_manchete:
            continue
        if m["tipo"] == "opiniao":
            nome = m["autor"] or "Colunista"
            itens.append((nome + ":", m["titulo"]))
    for i, m in enumerate(materias):
        if i == idx_manchete:
            continue
        if m["tipo"] == "reportagem":
            itens.append((None, m["titulo"]))
    return itens


# ---------------------------------------------------------------------------
# Texto de abertura (OpenAI)
# ---------------------------------------------------------------------------
def montar_prompt(materias, principal):
    """Monta as instruções para a IA. `principal` = posição (1, 2, 3...) da matéria principal."""
    papeis = {"editorial": "EDITORIAL", "opiniao": "COLUNA DE OPINIÃO", "reportagem": "REPORTAGEM"}

    mp = materias[principal - 1]
    autor_p = " | autor: %s" % mp["autor"] if mp["autor"] and mp["tipo"] != "editorial" else ""
    principal_txt = "%s%s\nTítulo: %s\nTexto: %s" % (
        papeis[mp["tipo"]], autor_p, mp["titulo"], texto_da_materia(mp, 6000)
    )

    outras = []
    for i, m in enumerate(materias, start=1):
        if i == principal:
            continue
        autor = " | autor: %s" % m["autor"] if m["autor"] and m["tipo"] != "editorial" else ""
        outras.append("- %s%s\n  Título: %s\n  Começo do texto: %s" % (papeis[m["tipo"]], autor, m["titulo"], texto_da_materia(m, 350)))
    outras_txt = "\n\n".join(outras) if outras else "(não há outros conteúdos)"

    exemplos = "\n\n---\n\n".join(EXEMPLOS_ABERTURA)
    sistema = (
        "Você é editor da Gazeta do Povo Revista, revista semanal em PDF para assinantes. "
        "Escreve o pequeno texto de abertura da publicação da edição no site, em português do Brasil, "
        "em tom jornalístico, direto e convidativo."
    )
    usuario = (
        "Escreva o texto de abertura desta edição, com EXATAMENTE dois parágrafos curtos, "
        "separados por uma linha em branco. O texto deve ser baseado na MATÉRIA PRINCIPAL abaixo.\n"
        "- Parágrafo 1: apresenta o tema da matéria principal e o que está em jogo, usando os fatos "
        "e números mais fortes do texto, de forma instigante (pode terminar com uma pergunta). "
        "Se a matéria principal for editorial ou coluna de opinião, apresente a tese defendida.\n"
        "- Parágrafo 2: diz, em poucas frases, o que mais o leitor encontra na edição, citando "
        "o editorial e, pelo nome, os colunistas, com uma frase sobre o que cada um escreve. "
        "Não repita o assunto do parágrafo 1.\n"
        "- Não invente fatos: use só o que está nos textos abaixo.\n"
        "- Não use título, lista, markdown, aspas em volta do texto nem emojis.\n"
        "- Não escreva a frase 'A Gazeta do Povo Revista é exclusiva para assinantes' nem convite "
        "para baixar a edição: isso é acrescentado depois.\n\n"
        "EXEMPLOS DE ABERTURAS QUE JÁ PUBLICAMOS (imite o tom e o tamanho, não copie o conteúdo):\n\n"
        + exemplos
        + "\n\n=====\nMATÉRIA PRINCIPAL:\n\n"
        + principal_txt
        + "\n\n=====\nOUTROS CONTEÚDOS DA EDIÇÃO:\n\n"
        + outras_txt
    )
    return sistema, usuario


def limpar_resposta_ia(texto):
    """Fica só com os dois primeiros parágrafos, sem markdown nem aspas soltas."""
    texto = (texto or "").strip()
    texto = re.sub(r"^```.*?\n|\n```$", "", texto, flags=re.S).strip()
    paragrafos = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    paragrafos = [re.sub(r"^[#>*\-\s]+", "", p).replace("**", "") for p in paragrafos]
    # tira "etiquetas" soltas que a IA às vezes escreve antes do texto (ex.: "Texto de abertura:")
    paragrafos = [p for p in paragrafos if not (len(p) < 60 and p.endswith(":"))]
    if len(paragrafos) == 1:
        # a IA mandou tudo em um bloco só: divide ao meio, na frase mais próxima do meio
        frases = re.split(r"(?<=[.!?])\s+", paragrafos[0])
        if len(frases) >= 2:
            meio = len(frases) // 2
            paragrafos = [" ".join(frases[:meio]), " ".join(frases[meio:])]
    return paragrafos[:2]


def gerar_abertura(materias, principal, modelo_ia, cliente=None):
    """Pede a abertura à OpenAI. Devolve uma lista de parágrafos (ou None se não deu certo)."""
    sistema, usuario = montar_prompt(materias, principal)
    try:
        if cliente is None:
            if not os.environ.get("OPENAI_API_KEY"):
                print("AVISO: não achei a chave OPENAI_API_KEY (nem no computador, nem no arquivo .env); deixei um aviso no lugar do texto de abertura.")
                return None
            from openai import OpenAI  # importado só aqui, para o script rodar mesmo sem a biblioteca

            cliente = OpenAI()
        resposta = cliente.chat.completions.create(
            model=modelo_ia,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
        )
        paragrafos = limpar_resposta_ia(resposta.choices[0].message.content)
        if not paragrafos:
            print("AVISO: a IA devolveu uma resposta vazia.")
            return None
        return paragrafos
    except ImportError:
        print("AVISO: a biblioteca 'openai' não está instalada (pip install openai); deixei um aviso no lugar do texto de abertura.")
    except Exception as erro:  # noqa: BLE001
        print("AVISO: não consegui falar com a OpenAI (%s); deixei um aviso no lugar do texto de abertura." % erro)
    return None


# ---------------------------------------------------------------------------
# Blocos do WordPress
# ---------------------------------------------------------------------------
def esc(texto):
    return html.escape(texto, quote=False)


def esc_attr(texto):
    return html.escape(texto, quote=True)


def slug(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def bloco_paragrafo(conteudo_html):
    return "<!-- wp:paragraph -->\n<p>%s</p>\n<!-- /wp:paragraph -->" % conteudo_html


def bloco_lista(itens):
    """itens = [(rotulo_ou_None, titulo), ...]"""
    li = []
    for rotulo, titulo in itens:
        if rotulo:
            texto = "<strong>%s</strong> %s" % (esc(rotulo), esc(titulo))
        else:
            texto = esc(titulo)
        li.append("<!-- wp:list-item -->\n<li>%s</li>\n<!-- /wp:list-item -->" % texto)
    return "<!-- wp:list -->\n<ul class=\"wp-block-list\">%s</ul>\n<!-- /wp:list -->" % "\n\n".join(li)


def bloco_titulo(texto, com_id=True):
    id_attr = ' id="h-%s"' % slug(texto) if com_id else ""
    return "<!-- wp:heading -->\n<h2 class=\"wp-block-heading\"%s>%s</h2>\n<!-- /wp:heading -->" % (id_attr, esc(texto))


def bloco_imagem(url, legenda):
    return (
        '<!-- wp:image {"width":"620px","height":"auto","sizeSlug":"full","linkDestination":"none"} -->\n'
        '<figure class="wp-block-image size-full is-resized"><img src="%s" alt="" '
        'style="width:620px;height:auto"/><figcaption class="wp-element-caption">%s</figcaption></figure>\n'
        "<!-- /wp:image -->" % (esc_attr(url), esc(legenda))
    )


def montar_texto(abertura, itens, edicao, subtitulo, link_pdf, foto, legenda):
    blocos = []

    # 1) abertura escrita pela IA
    if abertura:
        for p in abertura:
            blocos.append(bloco_paragrafo(esc(p)))
    else:
        blocos.append(bloco_paragrafo(esc(AVISO_ABERTURA)))
    blocos.append(bloco_paragrafo(esc(FRASE_ASSINANTES)))

    # 2) link para baixar o PDF
    link = (
        '<a href="%s" target="_blank" rel="noreferrer noopener">%s</a>' % (esc_attr(link_pdf or AVISO_LINK_PDF), TEXTO_LINK_PDF)
    )
    blocos.append(bloco_paragrafo(link))

    # 3) lista "Nessa edição você vai ler"
    blocos.append(bloco_paragrafo("<strong>%s</strong>" % TITULO_LISTA))
    blocos.append(bloco_lista(itens))

    # 4) título da edição (subtítulo) + foto com legenda
    numero = str(edicao) if edicao else AVISO_EDICAO
    sub = subtitulo.upper() if subtitulo else AVISO_SUBTITULO
    blocos.append(bloco_titulo("EDIÇÃO %s: %s" % (numero, sub), com_id=bool(edicao and subtitulo)))
    blocos.append(bloco_imagem(foto or AVISO_FOTO, legenda or AVISO_LEGENDA))

    # 5) como receber (texto fixo)
    blocos.append(bloco_paragrafo(PARAGRAFO_COMO_RECEBER))

    return "\n\n".join(blocos) + "\n"


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def gerar_texto_da_edicao(materias, manchete, edicao=None, subtitulo=None, link_pdf=None, foto=None,
                          legenda=None, modelo_ia=None, usar_ia=True):
    """
    Monta o texto de publicação completo (o conteúdo do texto_para_publicar.txt).
    `manchete` é a posição da matéria principal (a primeira é 1).
    Usado pelo app; o terminal usa a função main logo abaixo.
    """
    itens = montar_itens_lista(materias, manchete)
    abertura = None
    if usar_ia:
        abertura = gerar_abertura(materias, manchete, modelo_ia or os.environ.get("OPENAI_MODEL", "gpt-4o"))
    return montar_texto(abertura, itens, edicao, subtitulo, link_pdf, foto, legenda)


def main():
    carregar_env()
    ap = argparse.ArgumentParser(description="Gera o texto de publicação da Gazeta do Povo Revista (blocos do WordPress).")
    ap.add_argument("--html", nargs="+", help="pasta(s) com os HTMLs das matérias, ou os próprios arquivos")
    ap.add_argument("--saida", default="texto_para_publicar.txt", help="arquivo de saída (padrão: texto_para_publicar.txt)")
    ap.add_argument("--edicao", help="número da edição, ex.: 205")
    ap.add_argument("--subtitulo", help="subtítulo da edição, ex.: 'O peso do STF nas eleições' (opcional)")
    ap.add_argument(
        "--principal",
        help="sua matéria principal (a manchete): nome do arquivo, ex.: materia3.html, ou a posição, ex.: 3. "
        "A abertura escrita pela IA é baseada nela. Padrão: a primeira reportagem",
    )
    ap.add_argument("--manchete", help="o mesmo que --principal (nome antigo)")
    ap.add_argument("--link-pdf", help="link do PDF, se você já tiver")
    ap.add_argument("--foto", help="endereço da foto, se você já tiver")
    ap.add_argument("--legenda", help="legenda da foto, se você já tiver")
    ap.add_argument("--modelo-ia", default=os.environ.get("OPENAI_MODEL", "gpt-4o"), help="modelo da OpenAI (ou defina OPENAI_MODEL)")
    ap.add_argument("--sem-ia", action="store_true", help="não chama a OpenAI; deixa um aviso no lugar da abertura")
    args = ap.parse_args()

    # Se você apertou o botão "Run" do VS Code (sem escrever nada depois do nome do script),
    # o script faz as perguntas aqui no terminal.
    if not args.html:
        print("Vou te fazer 3 perguntas rápidas. Aperte Enter para pular as opcionais.\n")
        pasta = ""
        while not pasta:
            pasta = input("Pasta com os HTMLs (ex.: htmls): ").strip().strip('"').strip("'")
        args.html = [pasta]
        args.edicao = args.edicao or input("Número da edição (ex.: 205): ").strip() or None
        args.principal = args.principal or input("Matéria principal (ex.: materia3.html ou só 3; Enter = primeira reportagem): ").strip() or None
        print()

    materias = ler_materias(args.html)
    manchete = escolher_principal(materias, args.principal or args.manchete)

    print("Matérias lidas:")
    for i, m in enumerate(materias, start=1):
        marca = "  <- matéria principal (manchete)" if i == manchete else ""
        print("  %d) [%s] %s%s" % (i, m["tipo"], m["titulo"], marca))

    itens = montar_itens_lista(materias, manchete)

    abertura = None
    if not args.sem_ia:
        print("\nPedindo o texto de abertura à OpenAI (%s)..." % args.modelo_ia)
        abertura = gerar_abertura(materias, manchete, args.modelo_ia)

    texto = montar_texto(abertura, itens, args.edicao, args.subtitulo, args.link_pdf, args.foto, args.legenda)
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(texto)

    print("\nPronto! Texto salvo em:", args.saida)
    pendentes = [a for a in (AVISO_FOTO, AVISO_LEGENDA, AVISO_LINK_PDF, AVISO_SUBTITULO, AVISO_EDICAO, AVISO_ABERTURA) if a in texto]
    if pendentes:
        print("Ainda falta preencher: " + ", ".join(pendentes))


if __name__ == "__main__":
    main()
