# Gazeta Revista

App interno (Streamlit) para a equipe montar a Gazeta do Povo Revista.

O app tem um menu lateral com três páginas:

- **Montar a revista** (as duas abas descritas abaixo);
- **Roteiro para redes:** sugere textos curtos para divulgar a edição, a partir das matérias que você escolher;
- **Tutorial:** explica como fazer os uploads e o que o sistema devolve em cada etapa.

**Aba 1 – Montar a revista:** sobe os HTMLs das matérias e baixa a revista em Word (`.docx`) e o texto para publicar no site (`texto_para_publicar.txt`).

**Aba 2 – Finalizar o PDF:** sobe o PDF da revista já editada e o PDF da capa. O sistema junta os dois, coloca o banner na página vazia que vem logo depois do índice e comprime o arquivo (nível médio, por padrão).

Fluxo de quem usa:

1. Aba 1 → baixa o `.docx`.
2. Abre no Google Docs, edita como quiser e exporta em PDF.
3. Aba 2 → sobe esse PDF e a capa → baixa a revista final.

## O que tem em cada arquivo

| Arquivo | Para que serve |
|---|---|
| `app.py` | A porta de entrada do app: pede a senha e monta o menu lateral. |
| `comum.py` | A tela de senha e a leitura dos segredos, usadas por todas as páginas. |
| `paginas/revista.py` | A página "Montar a revista" (abas de Word e de PDF). |
| `paginas/roteiro.py` | A página "Roteiro para redes". |
| `paginas/tutorial.py` | A página "Tutorial". |
| `roteiro_redes.py` | O pedido à IA e a limpeza dos textos do roteiro. |
| `exemplos/exemplos_roteiro.txt` | Os textos de exemplo que a IA imita no roteiro (veja abaixo como mudar). |
| `montar_revista.py` | Lê os HTMLs e monta a revista em Word a partir do modelo. |
| `gerar_texto_publicacao.py` | Gera o texto para publicar (com a abertura escrita pela IA). |
| `finalizar_pdf.py` | Junta capa + revista, coloca o banner e comprime. |
| `config.py` | Ajustes simples: onde fica o banner, como ele entra na página, nível de compressão padrão. |
| `assets/banner.pdf` | **O banner**: uma página de PDF com link, ou uma imagem (você coloca aqui). |
| `modelo/modelo.docx` | **A revista da edição anterior**, usada como modelo (você coloca aqui). |
| `requirements.txt` | Lista do que o Streamlit precisa instalar. |
| `docs/` | Explicações detalhadas dos scripts de Word e de texto. |

## Antes de subir: coloque os dois arquivos seus

1. O banner em `assets/banner.pdf` (uma página de PDF, com o link) ou `assets/banner.png`.
2. A revista da edição anterior em `modelo/modelo.docx`.

Se você não colocar, o app pede esses arquivos na própria tela, mas fica mais prático deixá-los guardados.

> **Use um repositório PRIVADO no GitHub.** O modelo da revista e o banner ficam dentro dele.

## Testar no seu computador

No terminal do VS Code, dentro da pasta do projeto:

    pip install -r requirements.txt

Crie um arquivo `.env` (copie o `.env.example` e preencha):

    APP_PASSWORD=escolha-uma-senha-boa
    OPENAI_API_KEY=sua-chave-da-openai

Depois:

    streamlit run app.py

O navegador abre sozinho. Entre com a senha que você escolheu.

## Subir para o GitHub

1. No GitHub, crie um repositório novo e marque **Private**.
2. No terminal, dentro da pasta do projeto:

       git init
       git add .
       git commit -m "primeira versão"
       git branch -M main
       git remote add origin https://github.com/SEU-USUARIO/NOME-DO-REPOSITORIO.git
       git push -u origin main

3. Confira no GitHub que **não** apareceram os arquivos `.env` nem `.streamlit/secrets.toml`. O `.gitignore` já impede isso, mas vale olhar.

## Colocar no ar (Streamlit Community Cloud)

1. Entre em <https://share.streamlit.io> com a sua conta do GitHub e clique em **Create app**.
2. Escolha o repositório, a branch `main` e o arquivo `app.py`.
3. Em **Advanced settings → Secrets**, cole (com os seus valores):

       APP_PASSWORD = "escolha-uma-senha-boa"
       OPENAI_API_KEY = "sua-chave-da-openai"

4. Clique em **Deploy**. Quando terminar, compartilhe o link e a senha com a equipe.

A conta gratuita só permite **um app privado**. Como este app tem senha, ele pode ficar público (só o link abre a tela de entrada, e sem a senha nada funciona). Mesmo assim, use uma senha forte e defina um limite de gasto no painel da OpenAI.

## Trocar a senha ou a chave

No Streamlit Cloud: **Settings → Secrets**, edite e salve. O app reinicia sozinho.

## Atualizar o banner

Troque o arquivo `assets/banner.png` no GitHub (ou faça `git push` de novo). O app se atualiza em seguida.

## Onde o banner entra

O sistema procura o primeiro "Índice" nas primeiras páginas da revista e coloca o banner na página vazia logo depois dele (na revista atual, é a página 2). Se a revista mudar e ele não achar, digite o número da página no campo **Página do banner**.

O banner pode ser **uma página de PDF** (`assets/banner.pdf`) ou uma imagem (`assets/banner.png`). Se for PDF com link, o link continua clicável na revista final.

Em `config.py`, `BANNER_MODO` escolhe como ele entra na página:

- `"automatico"` (padrão): banner em PDF cobre a página inteira; banner em imagem cabe na área livre, sem cobrir o logo do topo nem o número da página.
- `"area_livre"`: sempre cabe na área livre.
- `"pagina_inteira"`: sempre cobre a página toda.

## Roteiro para redes

Na página **Roteiro para redes**, a pessoa escolhe a matéria de capa e, se quiser, até 4 outras para destacar. O sistema pede à OpenAI de 1 a 5 ideias de texto curto (cerca de 80 a 130 palavras, em 2 ou 3 parágrafos), cada uma com um gancho diferente, no estilo dos exemplos. Os textos usam só o que está nas matérias escolhidas, mas sempre vale ler antes de publicar.

Se os HTMLs já foram enviados na página "Montar a revista", a página de roteiro os usa automaticamente.

**Para mudar o estilo:** edite o arquivo `exemplos/exemplos_roteiro.txt`. Cada texto começa com uma linha `EXEMPLO 1:`, `EXEMPLO 2:` e assim por diante. Pode acrescentar, trocar ou apagar exemplos: a IA imita o tom e o tamanho deles. Depois é só enviar o arquivo ao GitHub.

## Links e marcadores

Todos os links do PDF editado continuam funcionando no PDF final, já apontando para as páginas certas (a capa empurra tudo uma página para frente):

- os links do **sumário**;
- os links de **"voltar ao índice"** (ou ao topo);
- os links para sites, como os da página de **sugestões de outras matérias**;
- os **marcadores** do menu lateral do leitor de PDF, se o seu PDF tiver.

Depois de finalizar, o app mostra quantos links foram mantidos (por exemplo, "23 internos e 18 externos"). Se algum não puder ser levado, ele avisa com o número. O link do banner entra além desses.

## Compressão

Três níveis, escolhidos na tela:

| Nível | O que faz |
|---|---|
| Leve | Mantém as imagens quase como estão. |
| **Médio** | Reduz as imagens para uma resolução boa para tela e leitura. É o padrão. |
| Forte | O menor arquivo possível, com perda visível de qualidade nas fotos. |

Os valores de cada nível estão no começo de `finalizar_pdf.py`, se você quiser ajustar.

## Limites e cuidados

- O plano gratuito do Streamlit tem cerca de 1 GB de memória. Revistas muito pesadas (centenas de MB) podem estourar.
- O app "dorme" depois de algumas horas sem uso; a primeira pessoa do dia espera alguns segundos.
- Não coloque a chave da OpenAI nem a senha dentro do código. Elas ficam só nos Secrets (ou no `.env`, que não vai para o GitHub).
- A biblioteca de PDF (PyMuPDF) é licenciada sob AGPL. Para uso interno da equipe, isso não costuma ser problema; se um dia o app for oferecido a pessoas de fora da empresa, vale conferir a licença com o jurídico.
- Se quiser calcular os números do índice automaticamente na aba 1, o servidor precisa do LibreOffice. No Streamlit gratuito, ele não vem instalado; digite as páginas à mão no campo "Páginas do índice".

## Rodar os scripts sem o app

Os scripts continuam funcionando sozinhos pelo terminal:

    python montar_revista.py --html htmls --modelo modelo/modelo.docx --saida revista_205.docx
    python gerar_texto_publicacao.py
    python finalizar_pdf.py --corpo revista_editada.pdf --capa capa.pdf --saida revista_final.pdf

Detalhes em `docs/LEIAME.md` e `docs/LEIAME_PUBLICACAO.md`.
