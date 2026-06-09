# PRODUTO.md — Agente Storyteller V5

## Visão

O Agente Storyteller V5 é um motor de narrativa interativa local e offline para Vampiro: A Máscara 5ª Edição (VTM v5). Executa in-loco em LM Studio com 3 agentes especializados (Árbitro, Memória, Narrador), oferecendo uma experiência de RPG narrativo persistente via WebSocket e integração assíncrona, sem dependência de internet ou APIs externas.

## Escopo

### In
- Sistema de estado do personagem (Humanidade, Fome, saúde, etc)
- Controle de turnos e ações baseado em regras de VTM v5
- Persistência de sessão via JSON assíncrono (com aiofiles e asyncio.Lock)
- WebSocket real-time para interação Narrador ↔ Jogador
- UI Dark Mode (Crimson Red + Charcoal Black)
- Geração narrativa via LLM local (3 agentes: Árbitro, Memória, Narrador)
- Estados críticos (TORPOR, FRENZY_CHECK) com bloqueio estruturado
- Testes concorrentes de I/O e WebSocket

### Out
- API GraphQL (apenas REST via FastAPI e canais WebSocket)
- Suporte a múltiplos jogadores simultâneos (apenas 1 por sessão ativa)
- Armazenamento em nuvem (apenas local via aiofiles)

## Acceptance Criteria

### Feature: Estado Básico do Personagem
- [ ] AC 1: Carregar ficha com atributos VTM v5 (Humanidade, Fome, Saúde, etc)
- [ ] AC 2: Persistir estado entre sessões via JSON + asyncio.Lock()
- [ ] AC 3: Validar restrições (Fome >= 5 → FRENZY_CHECK automático)

### Feature: Narrativa Reativa (PENDENTE)
- [ ] AC 4: Gerar resposta narrativa pelo Narrador baseado em lore estruturado
- [ ] AC 5: Injetar prompt de sistema com contexto do personagem + mundo
- [ ] AC 6: Validar latência < 500ms (local LLM)

### Feature: Evolução e XP (PRÓXIMO MÓDULO)
- [ ] AC 7: Rastrear XP ganho por sessão
- [ ] AC 8: Aplicar aumento de atributos conforme regras VTM v5
- [ ] AC 9: Persistir progressão entre sessões

## Constraints

### Técnicas
- Stack: Python 3.11+, FastAPI, WebSocket, LM Studio local (porta 1234)
- LLMs: qwen2.5-1.5b (Árbitro), deepseek-r1-7b (Memória), llama-3.2-3b (Narrador)
- Banco: Arquivos JSON locais (sem ORM, sem RDS)
- Offline: Zero dependência de internet

### Negócio
- Simplicidade cirúrgica: Nenhum boilerplate corporativo
- Isolamento: client_legacy/ é legado. O frontend principal agora reside em client/ em React 19 com Tailwind CSS v4.
- Exclusividade: 1 sessão ativa por vez (não multiplayer massivo)

## Decision Log

| Data | Decisão | Justificativa | Impacto |
|---|---|---|---|
| 2026-06-04 | Engine Split: Motor Mecânico ≠ LLM | Separação de conceitos. Regras são determinísticas, narrativa é generativa | Permite trocar LLM sem refatorar regras |
| 2026-06-04 | WebSocket assíncrono | Latência real-time necessária para interação narrativa | Complexidade de asyncio, mas não há alternativa para offline |
| 2026-06-01 | LM Studio local (não Ollama remoto) | Controle total, sem latência de rede | Uso local apenas, sem escalabilidade de usuários |
| 2026-06-08 | React 19 + TS (Migrado) | Maior interatividade, componentização e reatividade nos logs em tempo real | Melhoria drástica na experiência do jogador e robustez técnica |
