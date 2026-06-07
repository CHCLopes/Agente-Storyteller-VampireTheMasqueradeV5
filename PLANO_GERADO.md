# PLANO DE IMPLEMENTAÇÃO E EXECUÇÃO

## 1. SPEC_REFERENCES
- PRODUTO.md (commit: 3d1e3fc, version: 1.0)
- DESIGN.md (commit: 3d1e3fc, version: 1.0)
- DESIGN_SYSTEM.md (commit: 3d1e3fc, version: 1.0)

## 2. ACCEPTANCE_CRITERIA
- [x] AC 1: Carregar ficha com atributos VTM v5 (Humanidade, Fome, Saúde, etc)
- [x] AC 2: Persistir estado entre sessões via JSON + asyncio.Lock()
- [x] AC 3: Validar restrições (Fome >= 5 → FRENZY_CHECK automático)
- [x] AC 4: Gerar resposta narrativa pelo Narrador baseado em lore estruturado
- [x] AC 5: Injetar prompt de sistema com contexto do personagem + mundo
- [x] AC 6: Validar latência < 500ms (local LLM)
- [x] AC 7: Rastrear XP ganho por sessão
- [x] AC 8: Aplicar aumento de atributos conforme regras VTM v5
- [x] AC 9: Persistir progressão entre sessões

## 3. DESIGN_COMPLIANCE
- [x] Validar padrão técnico: Serviços: `*_service.py` (state_service, rules_service)
- [x] Validar padrão técnico: Schemas Pydantic: `*Model` (PlayerSheetModel, StateUpdateEvent)
- [x] Validar padrão técnico: Métodos assíncronos: `async def` sempre com `await` explícito
- [x] Validar padrão técnico: Locks: `async with <lock>:` para seção crítica
- [x] Validar padrão técnico: **Unit**: Schemas Pydantic (validação de dados)

## 4. DESIGN_SYSTEM_COMPLIANCE
- [x] Validar padrão de UI/Componente: Paleta Principal
- [x] Validar padrão de UI/Componente: Modo Dark/Light
- [x] Validar padrão de UI/Componente: Tipografia
- [x] Validar padrão de UI/Componente: Button
- [x] Validar padrão de UI/Componente: Input

## 5. CONFORMANCE_CHECKLIST
- [x] Setup do ambiente e validação das especificações (PRODUTO, DESIGN, DESIGN_SYSTEM).
- [x] Confirmação de que não existem conflitos de tecnologia entre as especificações.
- [x] Validação do escopo com as restrições arquiteturais definidas.

## 6. PLANO_ATÔMICO
- [x] Passo 1: Implementar as estruturas básicas de backend conforme o DESIGN.md.
- [x] Passo 2: Construir e estilizar a interface de acordo com o DESIGN_SYSTEM.md.
- [x] Passo 3: Integrar a lógica e rodar testes de critérios de aceitação (AC).

## 7. VALIDAÇÃO_AUTOMÁTICA
- [x] Rodar testes unitários e de integração para validar cada critério de aceitação de negócio.
- [x] Executar auditoria de design visual para verificar a correta aplicação dos componentes de UI.

## 8. SUCCESS_SIGNATURE
Status: 9 de 9 critérios completados.
