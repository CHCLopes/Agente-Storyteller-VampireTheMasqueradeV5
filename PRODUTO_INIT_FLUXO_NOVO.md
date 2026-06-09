# PRODUTO.md — Agente Storyteller V5 — Phase 2.5 (Novo Fluxo de Inicialização)

## Visão

Phase 2 foi completada (26/26 AC). Porém, testes end-to-end revelaram UX problem crítico:

**Problema**: Script rodava silenciosamente. Jogador via janela piscar e sumir sem feedback.

**Solução**: Novo fluxo com feedback visual em cascata — jogador vê exatamente o que está acontecendo.

---

## Escopo

### In

**NOVO FLUXO DE INICIALIZAÇÃO** (6 AC):

#### Init.1: Script Abre Navegador Automaticamente
```
AC 1.1: Duplo-clique em INICIAR_JOGO.bat → navegador abre em http://localhost:8000
Verificação: 
  - Browser window aparece com URL correto
  - Client React carrega
  - InitializationPanel exibido
```

#### Init.2: Menu Interativo de Seleção de Navegador (Opção B)
```
AC 1.2: Script pergunta qual navegador usar
Verificação:
  - Terminal exibe menu com 4 opções:
    (1) Chrome
    (2) Firefox
    (3) Edge
    (0) Auto-detectar
  - Usuário digita número
  - Navegador escolhido abre

Comportamento padrão: Se usuário pressiona Enter sem digitar → Auto-detecta
```

#### Init.3: Client Exibe InitializationPanel Durante Execução
```
AC 1.3: React component InitializationPanel renderiza imediatamente
Verificação:
  - Tela mostra "Inicializando Sistema" (título)
  - Lista de logs vazia inicialmente
  - Cliente aguarda conexão com script
  - Não há spinner infinito (ou spinner minimal)
```

#### Init.4: Script Envia Logs via WebSocket UM A UM
```
AC 1.4: Script Python envia cada log via POST /api/initialization/logs
Payload esperado:
  {
    "status": "pending" | "success" | "error" | "warning",
    "message": "[0/5] Abrindo navegador...",
    "phase": 0,
    "timestamp": 1717856400000
  }
Verificação:
  - Backend recebe POST e distribui via WebSocket /ws/initialization
  - Cada log tem id único (timestamp + random)
  - Logs são imutáveis (não editados depois)
```

#### Init.5: Client Exibe Logs em Cascata com Visual
```
AC 1.5: Cada log aparece com:
  - Transição fade-in suave (0.3s)
  - Ícone de status: [✓] (sucesso), [✗] (erro), [⚠] (warning), [...] (pending)
  - Cor por status:
    * success: text-green-500
    * error: text-red-500
    * warning: text-yellow-500
    * pending: text-zinc-400
  - Scroll automático para último log
  - Monospace font (font-mono)
  - Overflow com scrollbar (altura máxima)
Verificação:
  - Cada log fade-in quando chega
  - Scroll bottom automático
  - Cores corretas
  - Ícones visíveis
```

#### Init.6: Fim com Sucesso → HUD Desbloqueado; Fim com Erro → Mensagem Clara
```
AC 1.6: Dois finais:

SUCESSO:
  - Último log: "[✓] [5/5] Sistema Pronto! Boa Caçada 🦇"
  - InitializationPanel some (fade-out 0.5s)
  - HUD aparece (fade-in 0.5s)
  - Chat ativado, narrativa esperando
  
ERRO:
  - Log com status "error"
  - Exemplo: "[✗] LM Studio não encontrado. Instale em https://lmstudio.ai/"
  - InitializationPanel permanece
  - Botão "Tentar Novamente" aparece (re-executa script)
  - Logs salvos em localStorage para debugging

Verificação (Sucesso):
  - InitializationPanel desaparece
  - HUD renderiza (Ficha do PC visível)
  - Chat ativado
  
Verificação (Erro):
  - Mensagem de erro clara exibida
  - Botão "Tentar Novamente" funcional
  - Logs no console do browser (F12)
```

---

## Acceptance Criteria (Resumo)

| AC | Descrição | Status |
|---|---|---|
| Init.1 | Script abre navegador automaticamente | [ ] |
| Init.2 | Menu interativo: Chrome/Firefox/Edge/Auto | [ ] |
| Init.3 | InitializationPanel renderiza no client | [ ] |
| Init.4 | Script envia logs via POST → WebSocket | [ ] |
| Init.5 | Logs em cascata com transições e cores | [ ] |
| Init.6 | Fim com sucesso (HUD) ou erro (retry) | [ ] |

**Total**: 6 AC

---

## Constraints

### Técnicas
- **Backend**: Adicionar rota POST `/api/initialization/logs` e WebSocket `/ws/initialization`
- **Frontend**: Novo componente `InitializationPanel.tsx` + hook `useInitializationLog.ts`
- **Script**: Usar `httpx` para enviar logs via POST (async)
- **Browser**: Menu no terminal (input text simples)
- **Timeout**: Script espera máximo 30s por resposta do backend

### UX
- **Feedback**: Cada ação tem feedback visual (log)
- **Transparência**: Jogador vê EXATAMENTE o que está acontecendo
- **Recuperação**: Se erro, botão "Tentar Novamente" permite retry sem rebootar
- **Velocidade**: Logs devem aparecer < 500ms após envio

### Negócio
- **Prioridade**: Crítica (melhora UX drasticamente)
- **Impacto**: Zero breaking changes (apenas novo fluxo paralelo)
- **Rollback**: Se problema, volta para fluxo anterior (mas não deve ser necessário)

---

## Decision Log

| Decisão | Justificativa | Impacto |
|---|---|---|
| Opção B (Menu) vs Opção A (Auto) | Transparência + controle do jogador | UX +40%, mas 1 step extra |
| POST → WebSocket (não direto) | Backend distribui para múltiplos clientes (futura escalabilidade) | +20% latência, mas arquitetura melhor |
| Fade-in transitions | Visual feedback = sensação de "algo está acontecendo" | -10ms latência imperceptível |
| Retry button | Evita reinicialização completa do jogo se erro | +1 componente, UX +50% |

---

## Próximas Fases (Preview)

**Phase 3** (não nesta sessão):
- [ ] Expandir InitializationPanel para mostrar status de modelos visualmente
- [ ] Adicionar "Advanced Settings" para override de portas, caminhos, etc
- [ ] Salvar logs permanentemente (~última inicialização)

---

**Status**: Pronto para implementação. Aguardando Antigravity.
