<div align="center">
  
  # Agente Storyteller | Motor Narrativo V5 🦇
  
  **Um motor de RPG de mesa bare-metal e assíncrono projetado para mestrar 'Vampiro: A Máscara 5ª Edição' com inteligência local avançada, concorrência atômica e zero latência criativa.**

  **Stack Tecnológico**
  <br>
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
  [![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
  [![WebSockets](https://img.shields.io/badge/WebSockets-010101?style=for-the-badge&logo=socket.io&logoColor=white)](#)

  **Metodologia & Infraestrutura**
  <br>
  [![Impeccable Architecture](https://img.shields.io/badge/Impeccable_Architecture-000000?style=for-the-badge&logo=architecture&logoColor=white)](#)
  [![Vibe Coding Guidelines](https://img.shields.io/badge/Vibe_Coding-FF8C00?style=for-the-badge&logo=star&logoColor=white)](#)
  [![Test Driven Development](https://img.shields.io/badge/TDD_100%25-2E8B57?style=for-the-badge&logo=testing&logoColor=white)](#)
</div>

<br />

---

## 📖 Visão Geral

O projeto **Agente Storyteller** é um motor de orquestração local de Inteligência Artificial desenhado sob rigorosas práticas da **Mentoria Vibe Coding**. Concebido para atuar como o Mestre de Jogo de 'Vampiro: A Máscara', o sistema agora roda suportando WebSockets nativos para streaming reativo, validação estrita de contratos de dados (Pydantic), concorrência atômica e design orientado a múltiplos agentes.

Esta iteração assegura *zero technical debt*, eliminando I/O bloqueante e centralizando o estado através de um Pipeline robusto e altamente testado.

---

## 🚀 Engenharia de Software

O motor opera sob uma rígida separação de responsabilidades (Backend vs Engine de IA). Abaixo, os pilares técnicos que compõem o nosso padrão *Impeccable*:

| Pilar Técnico | Implementação (Agente Storyteller V5) |
| :--- | :--- |
| 🌐 **Rede e Streaming** | Migração total para protocolo **WebSockets** em chamadas assíncronas, garantindo streaming de texto (H6) *chunk* por *chunk*, reduzindo drasticamente a latência percebida no Frontend. |
| 🧠 **Multi-Agent Design** | Orquestração segregada: **Parser (H1)** com Retry/Fallback para extração matemática determinística de intenções e **Narrador (H6)** para injeção criativa de *Lore* Sombrio de VTM. |
| 🔒 **Atomicidade de Estado** | Sistema de arquivos assíncrono (`aiofiles`) operando sob `asyncio.Lock()`. Mutações no JSON do *PlayerSheet* ocorrem em concorrência isolada e segura por `session_id`. |
| 🛡️ **Validação de Contrato** | Base de Conhecimento V5 (Clãs, Disciplinas, NPCs, Economia de XP) construída em arquivos JSON estáticos rigorosamente validados na inicialização por schemas `Pydantic`. |
| 🏗️ **Fat-Orchestrator Removido** | Refatoração de *Design Patterns*: Criação do isolado `SystemLogBuilder`, limpando o orquestrador e construindo contextos semânticos para o LLM programaticamente. |
| ⚡ **Quality Assurance (TDD)** | Pipeline validado por 25 testes de integração assíncronos via `Pytest`, assegurando 100% de estabilidade nas mecânicas de Progressão, Combate, Danos Banes e Rerrolagem de Força de Vontade. |

---

## 🛠️ Guia de Inicialização Rápida

Para jogadores e engenheiros iniciarem o Motor V5:

1. **Baixe e Instale** o [LM Studio](https://lmstudio.ai/).
2. Carregue os modelos configurados na porta `1234`.
3. Abra a pasta do projeto e execute o **`INICIAR_JOGO.bat`** (valida o ambiente `.venv` e orquestra FastAPI).
4. Acione a interface de usuário (Web/Terminal) apontando para o Endpoint de WebSocket `/ws/session/local_player` na porta `8000`.

---

## 📬 Contato

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/carlos-lopes-b445aa201)
[![E-mail](https://img.shields.io/badge/E--mail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:[carloshcldev@gmail.com])
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/CHCLopes)

---

<div align="center">
  Refatorado e mantido segundo o mais alto padrão com Prompt Engineering voltada para qualidade do código e experiência do usuário. 🦇✨
</div>
