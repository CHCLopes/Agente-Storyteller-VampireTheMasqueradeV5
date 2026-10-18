# 🦇 A Primeira Noite: primeiros passos

O Agente Storyteller é local-first: regras, estado da campanha, eventos e memória
ficam sob controle da aplicação local. Isso não obriga que a inferência do LLM
ocorra no mesmo computador. Você escolhe explicitamente um único alvo compatível
com a API OpenAI; o sistema não seleciona provedor ou modelo e não faz fallback.

Para detalhes de arquitetura e desenvolvimento, consulte o [README](README.md).

## 1. Prepare o projeto

Requisitos:

- Python 3.11 ou superior;
- Node.js `^20.19.0` ou `>=22.12.0`;
- um alvo LLM OpenAI-compatible capaz de geração estruturada e streaming.

Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r api/requirements.txt

Set-Location client
npm ci
npm run build
Set-Location ..
```

## 2. Configure o alvo LLM

Copie o template para um arquivo local ignorado pelo Git:

```powershell
Copy-Item .env.example .env
```

Preencha `LLM_TARGET_ID`, `LLM_PROVIDER_LABEL`, `LLM_MODEL`, `LLM_BASE_URL`,
`LLM_STRUCTURED_GENERATION` e `LLM_STREAMING`. `LLM_API_KEY` é opcional apenas
no adaptador genérico e obrigatório para OpenRouter, Gemini e NVIDIA NIM.
`LLM_REASONING_EFFORT` também é opcional e deve ser omitido quando o alvo não
declarar suporte; para modelos locais compatíveis, `none` reduz latência em
operações mecânicas e estruturadas.

O servidor ou serviço escolhido precisa estar disponível antes de iniciar o jogo.
O Agente Storyteller não o instala nem o inicia. Se o alvo for remoto, prompts e o
contexto selecionado para narrar o turno serão enviados a esse serviço; avalie a
política de privacidade correspondente. Se for local, mantenha a URL restrita à
interface de loopback sempre que possível.

Para Gemini direto, use o modelo estável fixo `gemini-3.7-flash`, nunca um alias
`latest`. A modalidade gratuita pode usar prompts e respostas para melhorar
produtos; por isso ela deve ficar restrita aos testes sintéticos documentados em
`evals/narrator/README.md`, sem dados de campanha. O runtime principal exige
também `LLM_CAMPAIGN_DATA_ALLOWED=true`; mantenha-o falso até confirmar que a
política do projeto associado à chave permite o envio da campanha.

Para NVIDIA NIM, fixe `LLM_ADAPTER_KIND=nvidia`, o provedor `NVIDIA NIM`, a URL
`https://integrate.api.nvidia.com/v1` e o modelo
`nvidia/nemotron-3-ultra-550b-a55b`. O runtime recebe a chave apenas por
`LLM_API_KEY`; a variável `NVIDIA_API_KEY` é exclusiva do avaliador sintético.
O trial gratuito não deve receber cenas, memórias ou segredos da campanha.
Mantenha `LLM_CAMPAIGN_DATA_ALLOWED=false` e só habilite o runtime depois de
confirmar uma política apropriada para dados reais.

## 3. Inicie e valide

```powershell
python scripts\initialize_game.py
```

O inicializador abre um único processo do backend na porta 8000 e executa um teste
sintético sem dados da campanha. O sistema só é declarado pronto quando a
configuração, as capabilities e a resposta do alvo são válidas.

No Windows, `INICIAR_JOGO.bat` também prepara o ambiente, compila o frontend e
chama esse inicializador. Revise o `.env` antes de usá-lo.

## 4. Comece a jogar

Abra `http://localhost:8000` e descreva a ação do personagem. Ações narrativas
podem ser escritas em linguagem natural; ações mecânicas reconhecidas são
resolvidas pelos módulos determinísticos antes da narrativa.

Os comandos “Inicie uma nova crônica” e “Continue minha jornada” são texto de
jogador, não operações administrativas de criar, apagar ou trocar campanha. A
campanha ativa é identificada pela sessão carregada na interface.

## Dados e privacidade

- O estado canônico é armazenado por padrão em
  `data/saves/storyteller.sqlite3`.
- JSON legados são importados de forma não destrutiva e permanecem como fonte.
- O arquivo `.env` pode conter credenciais e nunca deve ser versionado ou enviado.
- Use um único worker do backend no MVP; a coordenação de sessão é local ao processo.
