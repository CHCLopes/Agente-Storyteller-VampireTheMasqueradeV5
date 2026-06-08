<div align="center">
  
  # Agente Storyteller | Motor Narrativo V5 🦇
  
  **Um motor de RPG de mesa bare-metal e assíncrono projetado para mestrar 'Vampiro: A Máscara 5ª Edição' com inteligência local avançada, concorrência atômica, frontend moderno em React e zero latência criativa.**

  **Stack Tecnológico do Backend**
  <br>
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
  [![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)

  **Stack Tecnológico do Frontend**
  <br>
  [![React](https://img.shields.io/badge/React-18.0-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-Strict-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
  [![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS_v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
  [![Vitest](https://img.shields.io/badge/Vitest-Test-729B1B?style=for-the-badge&logo=vitest&logoColor=white)](#)

</div>

<br />

---

## 📖 Visão Geral

O **Agente Storyteller** é um motor de orquestração local de Inteligência Artificial desenhado sob rigorosas práticas da **Mentoria Vibe Coding**. Concebido para atuar como o Mestre de Jogo de 'Vampiro: A Máscara', o sistema foi modernizado na **Fase 2** para incorporar um frontend modular em React 18+ com TypeScript Strict Mode e Tailwind CSS v4, acessibilidade WCAG AA com toggle de temas (Claro/Escuro), e inicialização zero-friction em cascata.

> [!NOTE]
> Este é o **repositório de desenvolvimento (Core)**. Para acessar a versão de distribuição empacotada e higienizada focada exclusivamente na experiência de jogo do jogador, acesse: [Agente Storyteller - Distribuição Pública (Foco do Jogador)](https://github.com/CHCLopes/AgenteStorytellerGame_Public).

---

## 🚀 Engenharia de Software & Refatoração React

O motor opera sob uma rígida separação de responsabilidades. Abaixo, os pilares técnicos que compõem o nosso padrão *Impeccable* após a refatoração da Fase 2:

| Pilar Técnico | Implementação (Fase 2) |
| :--- | :--- |
| 🌐 **Rede e Streaming** | Protocolo **WebSockets** em chamadas assíncronas no FastAPI servindo o build React estático de forma nativa na porta `8000` (rota raiz). |
| ⚛️ **Modernização da UI** | Migração completa de Vanilla JS para **React 18+** com **TypeScript strict: true**. Lógica reativa para rolagens de dados, upgrades de XP e controle de Frenesi. |
| 🎨 **Design System & Acessibilidade** | Estilização reestruturada sob **Tailwind CSS v4** sem CSS manual legado. Implementado suporte a **Dark Mode** (Charcoal + Crimson) e **Light Mode** gótico (Pergaminho + Terra) em conformidade com contraste **WCAG AA** e persistência no `localStorage`. |
| ⚡ **Auto-Inicialização** | Script Python (`scripts/initialize_game.py`) em cascata. Detecta a instalação do LM Studio no PATH ou diretórios padrões de usuário, valida a porta `1234`, escaneia e valida a presença de modelos recomendados, inicia o backend e abre o navegador automaticamente. |
| 🔒 **Atomicidade de Estado** | Sistema de arquivos assíncrono (`aiofiles`) operando sob `asyncio.Lock()` no backend para salvar mutações no JSON do *PlayerSheet* de forma segura. |
| 🧪 **Testes Automatizados** | Validação transversal: Cobertura de regras e latência no backend via **Pytest**, e testes de renderização de componentes de HUD via **Vitest** no frontend. |

---

## 🛠️ Guia de Inicialização Rápida (Zero-Friction)

Para jogadores e engenheiros iniciarem o Motor V5 de forma unificada:

1. **Instale** o [LM Studio](https://lmstudio.ai/) no seu computador.
2. **Baixe obrigatoriamente os três modelos de LLM** recomendados no LM Studio:
   *   🧠 **Árbitro de Regras (`qwen2.5-1.5b-instruct`):** Responsável por interpretar a matemática de VTM V5, dados de fome e mecânicas brutas.
   *   👁️ **Relacionamentos e Memória (`deepseek-r1-distill-qwen-7b`):** Gerencia as intrigas, contatos e o estado contínuo do Mundo das Trevas.
   *   🎭 **O Narrador (`llama-3.2-3b-instruct`):** Lapida a escrita gótica imersiva e a condução da história.
   *   *Nota: A orquestração paralela dos três modelos de forma independente e segregada é necessária para evitar alucinações conceituais e garantir a fidelidade às mecânicas durante a sessão.*
3. Dê duplo clique no atalho **`Iniciar o Jogo`** na raiz do projeto (ou execute `INICIAR_JOGO.bat` no terminal).
4. O inicializador inteligente cuidará de verificar as portas do LM Studio, validar a presença dos três modelos, subir o backend FastAPI e abrir o navegador em `http://localhost:8000` automaticamente.

---

## 📬 Contato

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/carlos-lopes-b445aa201)
[![E-mail](https://img.shields.io/badge/E--mail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:[carloshcldev@gmail.com])
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/CHCLopes)

---

<div align="center">
  Refatorado e mantido segundo o mais alto padrão com Prompt Engineering voltada para qualidade do código e experiência do usuário. 🦇✨
</div>
