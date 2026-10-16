# Texto de publicação da revista (gerar_texto_publicacao.py)

Este script gera o arquivo `texto_para_publicar.txt` no mesmo formato dos seus três exemplos
(blocos do WordPress), pronto para colar no editor do site.

## O que sai no arquivo

1. Texto de abertura, escrito pela IA da OpenAI com base nas matérias da pasta.
2. "A Gazeta do Povo Revista é exclusiva para assinantes. Baixe a sua:"
3. O link "BAIXE A NOVA EDIÇÃO DA GAZETA REVISTA EM PDF".
4. "Nessa edição você vai ler:" e a lista, montada sozinha a partir dos títulos dos HTMLs.
5. O título "EDIÇÃO NNN: ...".
6. A foto com a legenda.
7. O parágrafo fixo sobre como receber a revista (igual nos três exemplos).

O que não dá para saber antes fica com um aviso entre parênteses, para você trocar na hora:

    (poste a foto aqui)       (poste a legenda aqui)     (poste o link aqui)
    (poste o subtítulo aqui)  (número da edição)

## Sua matéria principal

Você diz qual é a matéria principal na hora de rodar, com `--principal`:

    python gerar_texto_publicacao.py --html htmls --edicao 205 --principal materia3.html

Pode escrever o nome do arquivo (com ou sem `.html`) ou só a posição na pasta (`--principal 3`).
Se você não informar, o script usa a primeira reportagem e mostra na tela qual escolheu.
Se o nome não existir, ele lista os arquivos que leu para você escolher.

O que a principal muda:

- **O texto de abertura:** a IA lê a matéria principal inteira. O primeiro parágrafo apresenta o tema
  e o que está em jogo nela. O segundo conta, em poucas frases, o que mais há na edição
  (editorial e colunistas), sem repetir o assunto do primeiro.
- **A lista:** a principal vira o primeiro item, "Manchete:". Se ela for o editorial, o rótulo é
  "Manchete/editorial:".

## Como o resto da lista é montada

Depois da manchete, a ordem segue a dos seus exemplos:

- **Editorial:** o editorial.
- **Nome do colunista:** as colunas de opinião, com o nome em negrito.
- As outras reportagens, só com o título.

Os títulos são os mesmos dos HTMLs. Se quiser um título mais curto, edite o .txt depois.

## Primeira vez

No terminal do VS Code:

    pip install openai

Depois, configure a chave da OpenAI. Ela não fica escrita no script, por segurança.
O nome que o script procura é exatamente `OPENAI_API_KEY`.

**Jeito mais simples: arquivo `.env`.** Crie um arquivo chamado `.env` (com o ponto, sem mais nada
no nome) na mesma pasta do script, com esta linha dentro:

    OPENAI_API_KEY=sua-chave-aqui

Sem aspas e sem espaços. Se quiser trocar o modelo, pode acrescentar `OPENAI_MODEL=gpt-4o`.
O script lê esse arquivo sozinho, não precisa instalar nada além do `openai`.
Se a chave já estiver configurada no computador, ela tem prioridade sobre o `.env`.

Cuidados: não mande o `.env` para ninguém, não suba para o GitHub nem para pastas compartilhadas.
Se usar git, escreva `.env` dentro de um arquivo `.gitignore`.

**Outro jeito: pelo terminal**, a cada vez que abrir o terminal:

- Windows (PowerShell): `$env:OPENAI_API_KEY="sua-chave-aqui"`
- Mac ou Linux: `export OPENAI_API_KEY="sua-chave-aqui"`

Se você já guarda essa chave em outro projeto, use a mesma.

## Rodar pelo botão "Run" do VS Code

Se você abrir o `gerar_texto_publicacao.py` e apertar o botão de play (Run Python File), o script
pergunta no terminal a pasta dos HTMLs, o número da edição e a matéria principal.
Não precisa digitar o comando comprido. Os outros dados (foto, legenda, link) ficam com os avisos de sempre.

## Rodar pelo terminal

    python gerar_texto_publicacao.py --html htmls --edicao 205 --principal materia3.html

Se tiver mais de uma pasta de HTMLs, pode listar todas:

    python gerar_texto_publicacao.py --html htmls_a htmls_b --edicao 205

Opções que você pode acrescentar, se já souber a informação:

    --subtitulo "O peso do STF nas eleições"
    --link-pdf "https://media.gazetadopovo.com.br/.../Gazeta_Revista_ed_205.pdf"
    --foto "https://media.gazetadopovo.com.br/.../foto.jpg"
    --legenda "Gazeta do Povo Revista debate o peso do STF nas eleições"
    --principal materia4.html
    --modelo-ia gpt-4o        (ou o modelo que você usa nos outros projetos)
    --sem-ia                  (não chama a OpenAI e deixa um aviso no lugar da abertura)

Se a OpenAI não responder (sem chave, sem internet ou erro), o script não trava:
ele deixa "(escreva o texto de abertura aqui)" e avisa na tela.

## Detalhes

- Os dois scripts (`montar_revista.py` e `gerar_texto_publicacao.py`) precisam ficar na mesma pasta.
- Nos exemplos havia um atributo "placeholder" com um texto em inglês em alguns blocos.
  Ele não faz parte do conteúdo, então não foi incluído.
- O bloco da foto sai sem o número interno da imagem do WordPress. Quando você trocar
  "(poste a foto aqui)" pelo endereço da foto, funciona normalmente.
- O título "EDIÇÃO NNN: ..." só ganha o código interno (id) quando você informa `--edicao` e
  `--subtitulo`. Se você preencher o subtítulo à mão no site, o WordPress cria o código sozinho.

## Como o script funciona, por partes

- `carregar_env`: tenta descobrir a sua chave da OpenAI.
  Para isso, abre o arquivo `.env` e coloca cada linha `NOME=valor` no ambiente do programa.
- `ler_materias`: tenta descobrir título, autor e tipo de cada matéria.
  Para isso, usa a mesma leitura de HTML do `montar_revista.py`.
- `escolher_principal`: tenta descobrir qual é a sua matéria principal.
  Para isso, compara o que você escreveu em `--principal` com o nome dos arquivos lidos.
- `montar_itens_lista`: tenta descobrir a ordem da lista "Nessa edição você vai ler".
  Para isso, põe a principal como manchete e junta editorial, colunistas e reportagens depois dela.
- `montar_prompt`: tenta explicar à IA o que escrever.
  Para isso, manda seus três exemplos de abertura, o texto inteiro da principal e só o começo das outras matérias.
- `limpar_resposta_ia`: tenta garantir que a abertura tenha só dois parágrafos limpos.
  Para isso, tira títulos soltos, markdown e parágrafos a mais.
- `montar_texto`: tenta reproduzir a estrutura dos exemplos.
  Para isso, encaixa cada parte em um bloco do WordPress, na mesma ordem.
