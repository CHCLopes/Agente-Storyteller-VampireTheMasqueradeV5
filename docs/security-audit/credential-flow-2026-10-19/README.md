# Auditoria da aplicação receptora da credencial - 19/10/2026

Escopo: lançador PowerShell, console/editor, supervisor, fila local e adaptador
OpenAI. Não é nova auditoria integral do produto. Skill de auditoria global e
skill PDF utilizadas; relatório anterior de 16/10 preservado.

## Resultado

- Três falhas locais informativas corrigidas: entrada sem feedback/validação,
  diagnóstico genérico de transporte/JSON e fase inexistente na credencial vazia.
- Zero vulnerabilidades remotas demonstradas neste escopo, sem promessa de
  segurança integral. Não foi lida nem testada a chave real.
- Colagem repetida ou caractere de controle são hipóteses locais reproduzíveis;
  não são causa confirmada do probe L26, cujo recibo continua inconclusivo.
- A aplicação não revela nem salva a chave. Chave duplicada não é dividida,
  truncada ou corrigida automaticamente. Formato local não comprova autenticação.

## UX implementada

O editor Windows mostra até 32 asteriscos e um contador total de caracteres,
sem revelar início/fim da chave. Backspace corrige, Esc/Ctrl+U limpa, Ctrl+C
cancela e Ctrl+Shift+V permite colagem pelo terminal. Nenhuma API de clipboard é
usada pelo script. Controles, espaços, Unicode e repetição integral de token
sk- duas a quatro vezes são recusados; o operador pode inserir novamente antes
de qualquer envio. Comprimentos/valores não entram em status ou relatórios.

O adaptador valida novamente antes de criar o cliente HTTP. Diagnósticos usam
apenas categorias fixas por tipo de erro; mensagens brutas e corpos/headers
não são registrados. Nova tentativa paga não foi autorizada nem executada aqui.

## Verificação

126 testes relacionados aprovados/um aviso preexistente python_multipart, XML
eval-results/credential-input-audit-extended-2026-10-19.xml. Cobertura: editor,
supervisora, custo, HTTP status, erro de transporte/JSON, gate fechado/drift,
manifestações históricas isoladas em fixtures e integração de campanha.
Não é suíte integral verde. Console Windows PTY testado com valor sintético:
asteriscos/contador e confirmação SYNTHETIC_CONSOLE_CHECK_OK.

Scan explícito: 10 arquivos e dois blobs históricos relacionados, zero indicadores
pelos padrões usados; .env, clipboard, memória/ambiente de processo, saves e
bundles fora do escopo não foram lidos. Ausência de indicador não prova ausência
universal de segredo.

PDF: sete páginas, texto/contagens verificados com pypdf, páginas rasterizadas e
visão geral/detalhe da tabela inspecionados; sem corte/sobreposição observados.
Issues são rascunhos informativos de rastreabilidade, não publicadas.

## Ativação humana necessária

A supervisora PID 3076/sessão 4beb08ec-4442-46ae-bb9d-c9c70377b216 ainda executa
o código antigo carregado. Ela foi preservada ociosa; gates L25/L26 fechados.
Não migrar credencial lendo ambiente/memória nem encerrar a janela sem coordenação.
As mudanças no adaptador invalidam hashes antigos por desenho; não alterar
manifestos históricos para contornar isso.

Quando o usuário puder interagir:

1. Encerrar a supervisora antiga, confirmando ausência de avaliador ativo.
2. Abrir o lançador corrigido com deadline absoluto até a meia-noite de Fortaleza.
3. Usuário cola UMA vez no campo com asteriscos, confere contador e confirma.
   Se detectar repetição, o editor recusa e permite reentrada. Não enviar chave ao chat.
4. Verificar somente estado idle/credential_local_validation=passed; isto ainda
   não é autenticação no provedor. Teste real posterior depende da quantidade
   autorizada; teto padrão USD 0,15 já está aprovado.

## Artefatos e reprodução

- relatorio-auditoria-seguranca.pdf: relatório final.
- dados-relatorio.json: evidências mascaradas, achados, proteções e limites.
- cobertura-scan.json: inventário explícito/scan redigido.
- issues.md: rascunhos completos, não publicados.
- manifesto-auditoria.json: hashes atuais e do PDF.
- gerar_relatorio.py: gerador reproduzível sem rede/credenciais.
- previews/: rasterizações verificadas (artefatos regeneráveis).

Executar gerar_relatorio.py com o Python documental já disponível em
C:/Users/skate/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe.
Nenhuma dependência foi instalada, nenhuma chave real usada e nenhum commit/push
foi realizado nesta auditoria.
