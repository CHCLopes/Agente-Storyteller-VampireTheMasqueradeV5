<div align="center">
  
  # Agente Storyteller | Motor Narrativo V5 🦇
  
  **Um motor de RPG de mesa bare-metal e assíncrono projetado para mestrar 'Vampiro: A Máscara 5ª Edição' com inteligência local avançada e zero latência criativa.**

  **Stack Tecnológico**
  <br>
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
  [![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)

  **Metodologia & Infraestrutura**
  <br>
  [![AI Agentic Coding](https://img.shields.io/badge/AI_Agentic_Coding-000000?style=for-the-badge&logo=openai&logoColor=white)](#)
  [![Bare-Metal Deployment](https://img.shields.io/badge/Bare--Metal_Deployment-FF8C00?style=for-the-badge&logo=server&logoColor=white)](#)
  [![Local LLM Binding](https://img.shields.io/badge/Local_LLM_Binding-7B68EE?style=for-the-badge&logo=probot&logoColor=white)](#)
  [![AppSec/PIP-Audit](https://img.shields.io/badge/AppSec/PIP--Audit-2E8B57?style=for-the-badge&logo=shield&logoColor=white)](#)
</div>

<br />

---

## 📖 Visão Geral

O projeto **Agente Storyteller** não é um mero chatbot; trata-se de um motor de orquestração local de Inteligência Artificial. Concebido para atuar como o Mestre de Jogo de 'Vampiro: A Máscara', o sistema baseia-se em uma arquitetura de API assíncrona orientada a Máquina de Estados (State Machine) e persistência de dados local, engatilhando chamadas otimizadas para LLMs rodando na própria máquina via LM Studio (ex: Llama 3.2 3B).

Com foco estrito na diretriz de Vibe Coding (Surgical Changes, Segurança Ativa e Infraestrutura Invisível), o motor oferece isolamento em *sandbox* (venv), testes unitários velozes e roteamento de Processamento de Linguagem Natural com tolerância a falhas.

---

## 🚀 Arquitetura e Engenharia de Software

O projeto opera sob uma rígida separação de responsabilidades (Backend vs Engine de IA). Abaixo, os pilares técnicos fundamentais:

| Pilar Técnico | Implementação (Agente Storyteller V5) |
| :--- | :--- |
| 🏗️ **Infraestrutura Bare-Metal** | Inicializador `.bat` dinâmico que provisiona o ambiente virtual (`.venv`), valida rotas físicas via cURL (Porta 1234) e bloqueia a execução em caso de anomalias no LM Studio. |
| 🎮 **Máquina de Estados (State Pattern)** | Controle estrito de UX no Python. Menus de Início, Expurgo de Saves, Tutorial Interativo de Lore e Interceptação de Saída Segura sem delegar controle sistêmico ao LLM. |
| 🧠 **Injeção de Persona Sombria** | Empacotamento Assíncrono (`httpx`) com *System Prompt* imutável (O Filtro da Besta), garantindo narração poética, gótica e anti-assistencialista para as campanhas. |
| 🗄️ **Persistência I/O Bound** | CRUD embutido em JSON, estruturado via *Pydantic Schemas*, isolando a integridade dos atributos de campanha do jogador em relação à saída criativa da IA. |
| ⚡ **Performance & AppSec** | Testes primários com `Pytest` (< 50ms para Health, < 100ms para Roteamento) conjugado a `pip-audit` contra injeções de vulnerabilidade de dependências. |
| 🛠️ **Ambiente de IDE (DX)** | Caminhos absolutos ancorados nativamente em `pyrightconfig.json` e `.vscode/settings.json`, mitigando quebras no *Linter/Pyright* no ambiente do Windows. |

---

## 🛠️ Guia de Inicialização Rápida

Para jogadores e engenheiros iniciarem o Motor V5:

1. **Baixe e Instale** o [LM Studio](https://lmstudio.ai/).
2. Carregue um modelo leve (como o *Llama 3.2 3B*) e inicie o **Local Server** na porta `1234`.
3. Abra a pasta do projeto e execute o **`INICIAR_JOGO.bat`**.
4. O Motor irá ler as dependências, verificar o status do LM Studio e orquestrar a API FastAPI no `localhost:8000`. O terminal higienizado guiará o jogador pela UX em CLI ou UI engatada.

---

## 📬 Contato

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/carlos-lopes-b445aa201)
[![E-mail](https://img.shields.io/badge/E--mail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:[carloshcldev@gmail.com])
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/CHCLopes)

---

<div align="center">
  Desenvolvido sob rigorosas diretrizes de engenharia de software para trazer as noites sombrias à sua máquina local. 🧛🩸
</div>
