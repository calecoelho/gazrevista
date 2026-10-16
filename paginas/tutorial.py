"""
Página "Tutorial": como usar cada parte do sistema e o que sai de cada uma.
"""
import streamlit as st

st.title("📖 Tutorial")
st.write(
    "Aqui está o caminho completo, do HTML das matérias até a revista final em PDF, "
    "e o que você recebe em cada etapa."
)

# ---------------------------------------------------------------------------
# Visão geral
# ---------------------------------------------------------------------------
st.subheader("O caminho em 3 passos")
c1, c2, c3 = st.columns(3)
with c1.container(border=True):
    st.markdown("**1. Montar**")
    st.write("Você sobe os HTMLs das matérias. O sistema devolve a revista em Word e o texto para publicar no site.")
with c2.container(border=True):
    st.markdown("**2. Editar**")
    st.write("Você abre o Word no Google Docs, ajusta o que quiser e exporta em PDF.")
with c3.container(border=True):
    st.markdown("**3. Finalizar**")
    st.write("Você sobe o PDF editado e a capa. O sistema junta tudo, coloca o banner e comprime.")
st.caption("Além disso, a página “Roteiro para redes” sugere textos curtos para divulgar a edição.")

# ---------------------------------------------------------------------------
# Passo 1
# ---------------------------------------------------------------------------
st.divider()
st.header("Passo 1 · Montar a revista em Word")
st.write("Página **Montar a revista**, aba **1. Montar a revista (Word)**.")

st.subheader("O que você precisa subir")
st.markdown(
    """
**Os HTMLs das matérias (obrigatório).** São sempre 7 arquivos, e o número no nome é a ordem em que
as matérias aparecem na revista:

| Arquivo | Tipo de matéria |
|---|---|
| `materia1.html` | Editorial |
| `materia2.html` e `materia3.html` | Colunas de opinião |
| `materia4.html` a `materia7.html` | Reportagens |

Para gerar cada arquivo, salve a página da matéria no navegador como HTML (por exemplo, `Ctrl + S` e
a opção "Página da Web, somente HTML") e renomeie na ordem acima. Você pode selecionar os 7 de uma vez
e arrastar para a tela. Se alguma matéria estiver no tipo errado (por exemplo, uma reportagem no lugar de
uma coluna), o sistema avisa.

**As fotos (opcional).** Se você não enviar, o sistema tenta baixar as fotos pelo endereço que está no HTML.
Se quiser usar fotos suas, nomeie assim:

| Nome do arquivo | Onde a foto entra |
|---|---|
| `materia1.jpg` … `materia7.jpg` | Foto principal de cada matéria |
| `materia2_autor.jpg`, `materia3_autor.jpg` | Foto do colunista, nas colunas de opinião |
| `materia7_img1.jpg`, `materia7_img2.jpg` | Fotos no meio do texto, na ordem em que aparecem |

**O modelo da revista.** Normalmente já está guardado no sistema (a edição anterior). Se a tela pedir, envie
a revista anterior em `.docx`.
"""
)

st.subheader("O que preencher")
st.markdown(
    """
- **Número da edição:** por exemplo, `205`. Entra no título do texto para publicar.
- **Subtítulo (opcional):** o subtítulo da edição.
- **Matéria principal (manchete):** a que a IA usa para escrever o texto de abertura. Por padrão, é a primeira reportagem.
- **Opções avançadas (opcional):**
  - *Páginas do índice:* os números das páginas, separados por vírgula (por exemplo, `4,10,19,24,38,53,61`).
    Se deixar vazio, os números do índice ficam como estavam no modelo.
  - *Texto de abertura com a IA:* deixe marcado para a OpenAI escrever a abertura. Se estiver cinza, a chave da OpenAI não está configurada.
"""
)

st.subheader("O que sai")
st.markdown(
    """
Ao clicar em **Montar revista e texto**, aparecem dois botões de download:

| Arquivo | O que é |
|---|---|
| **Revista (.docx)** | A revista completa em Word: índice, as 7 matérias, fotos e legendas, no mesmo formato do modelo. Abre bem no Google Docs. |
| **Texto para publicar (.txt)** | O texto da publicação no site, já em blocos do WordPress: abertura escrita pela IA, link do PDF, lista “Nessa edição você vai ler” (montada com os títulos das matérias), título da edição e o parágrafo fixo de como receber a revista. |

No texto para publicar, o que o sistema não tem como saber fica marcado entre parênteses, para você trocar na hora:
`(poste a foto aqui)`, `(poste a legenda aqui)`, `(poste o link aqui)` e `(poste o subtítulo aqui)`.

Logo abaixo dos botões há uma caixa **“Ver o que foi lido e o que foi descartado”**. Ela mostra os títulos que o sistema
encontrou e o que foi deixado de fora, como “Leia mais” e “Veja também”.
"""
)
st.info(
    "O que continua à mão: a lista **“Para se aprofundar”**, no fim da revista, fica como no modelo. "
    "As listas com marcadores viram “•” simples. Confira também as páginas de abertura de cada matéria."
)

# ---------------------------------------------------------------------------
# Passo 2
# ---------------------------------------------------------------------------
st.divider()
st.header("Passo 2 · Editar no Google Docs")
st.markdown(
    """
1. Envie o `.docx` para o Google Drive e abra com o Google Docs.
2. Faça os ajustes que quiser: textos, fotos, legendas, a lista “Para se aprofundar” e os números do índice, se precisar.
3. Quando terminar, exporte em PDF: **Arquivo → Fazer download → Documento PDF (.pdf)**.
"""
)

# ---------------------------------------------------------------------------
# Passo 3
# ---------------------------------------------------------------------------
st.divider()
st.header("Passo 3 · Finalizar o PDF")
st.write("Página **Montar a revista**, aba **2. Finalizar o PDF**.")

st.subheader("O que você precisa subir")
st.markdown(
    """
- **PDF da revista editada:** o PDF que você exportou do Google Docs.
- **PDF da capa:** a página (ou páginas) da capa, em PDF. Ela vai para o começo da revista.
- **Banner:** já fica guardado no sistema e aparece na tela. Se quiser usar outro só desta vez, abra “Usar outro banner só desta vez”.
  O banner pode ser uma página de PDF (com link, que continua clicável) ou uma imagem.
"""
)

st.subheader("O que escolher")
st.markdown(
    """
- **Compressão:** *Leve* mantém quase toda a qualidade, *Médio* (recomendado) deixa o arquivo com um bom tamanho para
  leitura e envio, e *Forte* gera o menor arquivo, com perda visível de qualidade nas fotos.
- **Página do banner:** deixe em **0** para o sistema achar sozinho. Ele procura o índice e coloca o banner na página
  vazia logo depois. Se não achar, digite o número da página vazia contando pelo PDF da revista, sem a capa (normalmente é a 2).
"""
)

st.subheader("O que sai")
st.markdown(
    """
Ao clicar em **Finalizar PDF**, você recebe a **revista final (.pdf)** com:

- a capa na frente, seguida da revista;
- o banner na página vazia depois do índice (a tela mostra uma prévia dessa página);
- **todos os links funcionando:** os do índice, os de “voltar ao índice” e os links para sites, como a página de sugestões de outras matérias;
- o menu lateral do leitor de PDF (marcadores), quando o seu PDF tiver;
- o arquivo comprimido. A tela mostra o número de páginas e o tamanho antes e depois.

A tela também diz quantos links foram mantidos, por exemplo “23 internos e 18 externos”. Se algum link não puder ser levado,
aparece um aviso com o número.
"""
)

# ---------------------------------------------------------------------------
# Roteiro
# ---------------------------------------------------------------------------
st.divider()
st.header("Roteiro para redes")
st.write("Página **Roteiro para redes**, no menu da esquerda.")
st.markdown(
    """
1. **HTMLs:** se você já subiu os HTMLs na página “Montar a revista”, eles são usados automaticamente. Senão, envie os 7.
2. **Tema de capa:** escolha a matéria principal do roteiro.
3. **Outras matérias para destacar (opcional):** escolha até 4 matérias que também devem aparecer no texto.
4. **Quantas ideias:** de 1 a 5. Cada uma abre com um gancho diferente.
5. **Pedido especial (opcional):** por exemplo, “tom mais direto” ou “começar por uma pergunta”.
6. Clique em **Gerar ideias**.

**O que sai:** textos curtos (cerca de 80 a 130 palavras, em 2 ou 3 parágrafos), no estilo dos roteiros que a Gazeta
já publica: o tema de capa primeiro, as outras matérias depois, e uma frase final convidando o assinante a baixar a edição.
Cada texto tem um botão para copiar, e dá para baixar todos em um arquivo `.txt`.

Os textos usam só o que está nas matérias que você escolheu. Mesmo assim, **leia antes de publicar**: confira nomes, números e o tom.
"""
)

# ---------------------------------------------------------------------------
# Problemas comuns
# ---------------------------------------------------------------------------
st.divider()
st.header("Se algo não saiu como esperado")
with st.expander("Apareceu “Esperava 7 matérias e li outro número”"):
    st.write(
        "Faltou ou sobrou algum HTML na tela. Confira se os 7 arquivos foram enviados, sem repetidos "
        "e sem outros arquivos HTML no meio."
    )
with st.expander("“Não consegui ler um dos HTMLs”"):
    st.write(
        "O arquivo salvo pode estar incompleto ou ser de uma página que não é uma matéria. Abra a matéria no site, "
        "salve de novo como HTML e envie esse arquivo no lugar do anterior."
    )
with st.expander("A caixa da IA está cinza, ou o botão “Gerar ideias” não funciona"):
    st.write(
        "O app não encontrou a chave da OpenAI. Quem cuida do app precisa conferir se a chave está nos Secrets, "
        "com o nome exatamente `OPENAI_API_KEY`."
    )
with st.expander("“Não achei a página vazia depois do índice”"):
    st.write(
        "Na aba de finalizar, digite o número da página vazia no campo “Página do banner”. A contagem é feita no PDF "
        "da revista, sem a capa. Normalmente é a página 2."
    )
with st.expander("Apareceu um aviso de links que não puderam ser levados"):
    st.write(
        "Alguns links do PDF editado apontam para lugares que o sistema não consegue copiar (por exemplo, para outro arquivo). "
        "Abra o PDF final, clique em um link de cada tipo e confira. Se o problema estiver no PDF editado, "
        "corrija o link no Google Docs e exporte de novo."
    )
with st.expander("O banner não ficou como eu esperava"):
    st.write(
        "Um banner em PDF cobre a página inteira, e uma imagem fica na área livre entre o logo e o número da página. "
        "Quem cuida do app pode mudar isso no arquivo de configurações."
    )
with st.expander("O app demorou para abrir"):
    st.write(
        "Depois de um tempo sem uso, o app “dorme”. A primeira pessoa do dia espera alguns segundos até ele acordar. "
        "Depois, funciona normalmente."
    )
with st.expander("Esqueci a senha ou quero trocá-la"):
    st.write("A senha é definida por quem cuida do app, nas configurações do Streamlit. Peça a essa pessoa para consultar ou trocar.")
