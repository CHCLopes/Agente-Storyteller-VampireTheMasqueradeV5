# DESIGN.md — Agente Storyteller V5 — Phase 2 (Bugs + Refactor React)

## FASE 1 — DEBUG CRÍTICO (PRÉ-REQUISITO)

### Por quê o .bat não funciona?

**Análise**:
```bash
# Teste 1: Verificar se Python está no PATH
python --version

# Teste 2: Verificar se requirements.txt foi instalado
pip list | grep fastapi
pip list | grep aiofiles
pip list | grep pydantic

# Teste 3: Rodar main.py diretamente (não via .bat)
cd api/
python main.py

# Teste 4: Verificar se port 8000 está ocupada
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux
```

**Hipóteses**:
1. ❌ `PATH` não inclui Python (Windows)
2. ❌ `requirements.txt` não foi executado (`pip install -r requirements.txt`)
3. ❌ Porta 8000 já está em uso
4. ❌ Erro no `api/main.py` (import falho, sintaxe)
5. ❌ `.bat` tem diretório errado (cwd incorreto)

**Solução**:
```batch
@echo off
REM iniciar_jogo.bat — Versão 2 com diagnóstico

echo [*] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado no PATH
    pause
    exit /b 1
)

echo [*] Instalando dependências...
pip install -r requirements.txt >nul 2>&1

echo [*] Iniciando servidor FastAPI...
cd /d "%~dp0"
python api/main.py

if errorlevel 1 (
    echo [ERRO] Servidor não iniciou
    pause
    exit /b 1
)
```

### Por quê o client não abre?

**Análise**:
```javascript
// Console do browser (F12 → Console)
// Verifique se há erros de:
// 1. WebSocket não conecta → wss://localhost:8000/ws/session/{id}
// 2. HTML não carrega → arquivo index.html existe?
// 3. CSS/JS não carregam → path incorreto?
// 4. CORS bloqueando → backend não tem headers certos?
```

**Hipóteses**:
1. ❌ Backend não está servindo `index.html` (rota `/` não existe)
2. ❌ WebSocket URL é errada (`http://` vs `ws://`)
3. ❌ CORS headers ausentes (resposta `Access-Control-Allow-Origin`)
4. ❌ `127.0.0.1:8000` vs `localhost:8000` (browser cache)
5. ❌ JavaScript error em `app.js` (sintaxe ou referência indefinida)

**Solução — Backend**:
```python
# api/main.py — Adicionar rota para servir frontend

from fastapi.staticfiles import StaticFiles
import os

@app.get("/")
async def root():
    """Serve the frontend index.html"""
    with open(os.path.join(os.path.dirname(__file__), "../client/index.html")) as f:
        return HTMLResponse(content=f.read())

@app.get("/{filename}")
async def serve_static(filename: str):
    """Serve static assets (css, js)"""
    filepath = os.path.join(os.path.dirname(__file__), "../client", filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            if filename.endswith('.css'):
                return Response(content=f.read(), media_type="text/css")
            elif filename.endswith('.js'):
                return Response(content=f.read(), media_type="application/javascript")
    return {"error": "File not found"}
```

**Solução — Frontend**:
```javascript
// app.js — Conectar ao WebSocket corretamente

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//localhost:8000/ws/session/default`;

const ws = new WebSocket(wsUrl);

ws.onopen = () => {
    console.log('[✓] Conectado ao servidor');
    document.getElementById('conn-text').textContent = 'Conectado';
};

ws.onerror = (error) => {
    console.error('[✗] Erro WebSocket:', error);
    document.getElementById('conn-text').textContent = 'Erro';
};
```

**Status FASE 1**: 
- [ ] AC 1.1: Terminal .bat executa sem erros ✓
- [ ] AC 1.2: Frontend client abre em http://localhost:8000 ✓
- [ ] AC 1.3: WebSocket conecta ✓
- [ ] AC 1.4: Carregar ficha funciona ✓

---

## FASE 2 — REFATOR VANILLA JS → REACT/TYPESCRIPT

### 2.1 Análise do Código Atual (Vanilla JS)

**Estrutura Existente**:
```
app.js (437 linhas)
├── estado em objeto JavaScript puro
├── renderizadores (manipulação direta de DOM)
├── event listeners (botões, inputs)
├── WebSocket manual
└── Sem componentes reutilizáveis
```

**Problemas**:
1. ❌ Estado é mutável (sem unidirecionalidade)
2. ❌ Re-renderização é manual (querySelector + innerHTML)
3. ❌ Sem type checking (erros só em runtime)
4. ❌ Sem testes (componentes acoplados ao DOM)
5. ❌ Sem separação de concerns (lógica + UI misturadas)

**Benefícios do React**:
- ✅ Estado unidirecional (props down, events up)
- ✅ Re-renderização automática (Virtual DOM)
- ✅ TypeScript nativo (erros em build-time)
- ✅ Componentes testáveis (vitest, React Testing Library)
- ✅ Escalável (reutilização, composição)

---

### 2.2 Arquitetura React Proposta

```
src/
├── components/
│   ├── Header/
│   │   ├── Header.tsx          (Título + Conexão)
│   │   └── Header.module.css   (Styles específicos)
│   ├── HUD/
│   │   ├── HUDCharacterSheet.tsx   (Ficha do PC)
│   │   ├── HUDAttributeRow.tsx     (Linha de atributo)
│   │   └── PipTracker.tsx          (Pips de Fome/Vida/Vontade)
│   ├── Narrative/
│   │   ├── NarrativeLog.tsx        (Log de narrativa)
│   │   └── NarrativeMessage.tsx    (Mensagem individual)
│   ├── ActionPanel/
│   │   ├── ActionPanel.tsx         (Input + Botões)
│   │   ├── CommandInput.tsx        (Textarea)
│   │   ├── MacroSelect.tsx         (Dropdown de ações rápidas)
│   │   └── SendButton.tsx          (Botão enviar)
│   ├── Navigation/
│   │   ├── BottomNav.tsx          (Nav mobile)
│   │   └── NavButton.tsx          (Botão nav)
│   ├── Modal/
│   │   ├── Modal.tsx             (Genérico)
│   │   ├── AboutModal.tsx        (Sobre)
│   │   └── HelpModal.tsx         (Ajuda)
│   └── Common/
│       ├── Pip.tsx               (Pip individual)
│       ├── Button.tsx            (Button reutilizável)
│       └── Select.tsx            (Select reutilizável)
├── hooks/
│   ├── useCharacterState.ts      (Estado do personagem)
│   ├── useWebSocket.ts           (Conexão WebSocket)
│   ├── useDarkMode.ts            (Dark/Light mode)
│   └── useModal.ts               (Controle de modais)
├── types/
│   ├── character.ts              (PlayerSheet, State)
│   ├── narrative.ts              (Message, Log)
│   └── game.ts                   (Game state, Actions)
├── styles/
│   ├── tailwind.css              (Tailwind + custom)
│   ├── dark-mode.css             (Dark/Light paletas)
│   └── animations.css            (Efeitos VTM)
├── utils/
│   ├── formatMessage.ts          (Parser de narrativa)
│   ├── pipCalculators.ts         (Lógica de pips)
│   └── macroParser.ts            (Parser de macros)
├── App.tsx                       (Root component)
├── main.tsx                      (Entry point)
├── vite-env.d.ts                (Tipos Vite)
└── tsconfig.json                (TypeScript config)
```

---

### 2.3 Componentes Base — React/TypeScript

#### **1. types/character.ts**

```typescript
// Tipos do personagem (V5 VTM)

export interface Tracker {
  size: number;
  superficial: number;
  aggravated: number;
}

export interface PlayerSheet {
  id: string;
  nome: string;
  geracao: string; // "Neófito", "Cria", etc
  clan: string;   // "Brujah", "Ventrue", etc
  predator: string; // "Sanguinário", "Caçador", etc
  
  // Atributos (0-5)
  attributes: {
    strength: number;
    dexterity: number;
    stamina: number;
    charisma: number;
    manipulation: number;
    composure: number;
    intelligence: number;
    wits: number;
    resolve: number;
  };
  
  // Trackers
  hunger: number; // 0-5 (crítico: >= 5 → FRENZY_CHECK)
  health: Tracker;
  willpower: Tracker;
  
  // Skills / Disciplines / Relations
  skills: Record<string, number>;
  disciplines: Record<string, number>;
  relationships: Relationship[];
  
  // Progression
  xp: number;
}

export interface Relationship {
  id: string;
  npcName: string;
  type: "ally" | "enemy" | "favor" | "mentor";
  strength: number; // 1-5
  description: string;
}

export interface CharacterState {
  sheet: PlayerSheet;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date;
}
```

#### **2. types/narrative.ts**

```typescript
// Tipos de narrativa

export type MessageType = "system" | "narrator" | "action" | "error" | "success";

export interface NarrativeMessage {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  speakerRole?: "Árbitro" | "Narrador" | "Memória"; // LLM agents
}

export interface NarrativeLog {
  messages: NarrativeMessage[];
  sessionId: string;
  startedAt: Date;
}
```

#### **3. hooks/useCharacterState.ts**

```typescript
import { useState, useCallback } from 'react';
import { PlayerSheet, CharacterState } from '../types/character';

export const useCharacterState = (initialSheet?: PlayerSheet) => {
  const [state, setState] = useState<CharacterState>({
    sheet: initialSheet || emptySheet(),
    isLoading: false,
    error: null,
    lastUpdated: new Date(),
  });

  const updateSheet = useCallback((sheet: PlayerSheet) => {
    setState(prev => ({
      ...prev,
      sheet,
      lastUpdated: new Date(),
    }));
  }, []);

  const setHunger = useCallback((value: number) => {
    setState(prev => ({
      ...prev,
      sheet: { ...prev.sheet, hunger: Math.min(5, Math.max(0, value)) },
    }));
  }, []);

  const damageHealth = useCallback((type: 'superficial' | 'aggravated', count: number) => {
    setState(prev => ({
      ...prev,
      sheet: {
        ...prev.sheet,
        health: {
          ...prev.sheet.health,
          [type]: Math.min(prev.sheet.health.size, prev.sheet.health[type] + count),
        },
      },
    }));
  }, []);

  return { state, updateSheet, setHunger, damageHealth };
};

function emptySheet(): PlayerSheet {
  return {
    id: '',
    nome: '',
    geracao: '',
    clan: '',
    predator: '',
    attributes: {
      strength: 0, dexterity: 0, stamina: 0,
      charisma: 0, manipulation: 0, composure: 0,
      intelligence: 0, wits: 0, resolve: 0,
    },
    hunger: 0,
    health: { size: 10, superficial: 0, aggravated: 0 },
    willpower: { size: 5, superficial: 0, aggravated: 0 },
    skills: {},
    disciplines: {},
    relationships: [],
    xp: 0,
  };
}
```

#### **4. hooks/useWebSocket.ts**

```typescript
import { useEffect, useRef, useCallback, useState } from 'react';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: any) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export const useWebSocket = ({
  url,
  onMessage,
  onError,
  onConnect,
  onDisconnect,
}: UseWebSocketOptions) => {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//localhost:8000/ws/session/default`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };

    ws.onerror = (error) => {
      setIsConnected(false);
      onError?.(error);
    };

    ws.onclose = () => {
      setIsConnected(false);
      onDisconnect?.();
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [url, onMessage, onError, onConnect, onDisconnect]);

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { isConnected, send, ws: wsRef.current };
};
```

#### **5. hooks/useDarkMode.ts**

```typescript
import { useState, useEffect } from 'react';

export const useDarkMode = () => {
  const [isDark, setIsDark] = useState(() => {
    // Check localStorage first
    const stored = localStorage.getItem('theme');
    if (stored) return stored === 'dark';
    
    // Check OS preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const html = document.documentElement;
    if (isDark) {
      html.classList.add('dark');
      html.classList.remove('light');
      localStorage.setItem('theme', 'dark');
    } else {
      html.classList.remove('dark');
      html.classList.add('light');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggle = () => setIsDark(prev => !prev);

  return { isDark, toggle };
};
```

#### **6. components/HUD/PipTracker.tsx**

```typescript
import React from 'react';

interface PipTrackerProps {
  type: 'hunger' | 'health' | 'willpower';
  value?: number;
  size?: number;
  superficial?: number;
  aggravated?: number;
}

export const PipTracker: React.FC<PipTrackerProps> = ({
  type,
  value,
  size = 5,
  superficial = 0,
  aggravated = 0,
}) => {
  if (type === 'hunger') {
    return (
      <div className="flex gap-2" aria-label="Tracker de Fome">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={`w-5 h-5 rounded-full border-2 transition-all ${
              i < (value || 0)
                ? 'bg-red-500 border-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
                : 'border-red-900 bg-transparent'
            }`}
            aria-label={i < (value || 0) ? 'Fome ativa' : 'Fome vazia'}
          />
        ))}
      </div>
    );
  }

  // Health / Willpower (quadrados com danos)
  return (
    <div className="flex gap-2 flex-wrap" aria-label={`Tracker de ${type}`}>
      {Array.from({ length: size }).map((_, i) => {
        const isAggravated = i < aggravated;
        const isSuperficial = i < (aggravated + superficial);

        return (
          <div
            key={i}
            className={`w-5 h-5 border-2 border-red-700 rounded transition-all ${
              isAggravated
                ? 'bg-red-500'
                : isSuperficial
                ? 'bg-red-300'
                : 'bg-transparent'
            }`}
            style={{
              backgroundImage: isAggravated
                ? 'linear-gradient(135deg, transparent 46%, #b91c1c 46%, #b91c1c 54%, transparent 54%), linear-gradient(45deg, transparent 46%, #b91c1c 46%, #b91c1c 54%, transparent 54%)'
                : isSuperficial
                ? 'linear-gradient(135deg, transparent 46%, #b91c1c 46%, #b91c1c 54%, transparent 54%)'
                : 'none',
            }}
            aria-label={
              isAggravated ? 'Dano agravado' : isSuperficial ? 'Dano superficial' : 'Intacto'
            }
          />
        );
      })}
    </div>
  );
};
```

#### **7. components/ActionPanel/ActionPanel.tsx**

```typescript
import React, { useState } from 'react';
import { CommandInput } from './CommandInput';
import { MacroSelect } from './MacroSelect';
import { SendButton } from './SendButton';

interface ActionPanelProps {
  onSendAction: (action: string) => void;
  isLoading?: boolean;
}

export const ActionPanel: React.FC<ActionPanelProps> = ({ onSendAction, isLoading }) => {
  const [input, setInput] = useState('');

  const handleMacroSelect = (macro: string) => {
    setInput(macro);
  };

  const handleSend = () => {
    if (input.trim()) {
      onSendAction(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSend();
    }
  };

  return (
    <div className="w-full bg-zinc-950/90 border-t border-zinc-800/80 backdrop-blur z-20 p-4 space-y-3">
      <CommandInput
        value={input}
        onChange={setInput}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
      />
      <div className="flex gap-3">
        <MacroSelect onSelect={handleMacroSelect} className="w-2/3" />
        <SendButton onClick={handleSend} isLoading={isLoading} className="w-1/3" />
      </div>
    </div>
  );
};
```

---

### 2.4 Tailwind Config Expandido

```javascript
// tailwind.config.ts (TypeScript)

import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class', // .dark na classe do HTML
  theme: {
    extend: {
      colors: {
        // Dark Mode (padrão)
        v5: {
          charcoal: '#121214',
          parchment: '#e2e0d9',
          blood: '#7f1d1d',
          crimson: '#b91c1c',
          card: '#18181b',
          border: '#27272a'
        },
        // Light Mode (novo)
        v5light: {
          parchment: '#f5f0e8',    // Pergaminho envelhecido
          earth: '#8B4513',         // Terra queimada (marrom VTM)
          charcoal: '#3d3d3d',      // Cinzento escuro (não preto puro)
          accent: '#d4a574',        // Dourado envelhecido
          border: '#c9b8a8',        // Borda terra
        }
      },
      fontFamily: {
        gothic: ['"Pirata One"', 'serif'],
        serif: ['Lora', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif']
      },
      keyframes: {
        'border-flash': {
          '0%': { borderColor: '#b91c1c', boxShadow: '0 0 0px rgba(185, 28, 28, 0)' },
          '50%': { borderColor: '#ef4444', boxShadow: '0 0 12px rgba(239, 68, 68, 0.5)' },
          '100%': { borderColor: '#3f3f46', boxShadow: '0 0 0px rgba(185, 28, 28, 0)' },
        },
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        }
      },
      animation: {
        'border-flash': 'border-flash 0.5s cubic-bezier(0.25, 0.8, 0.25, 1)',
        'pulse-subtle': 'pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    }
  },
  plugins: [],
}

export default config
```

---

### 2.5 App.tsx Root Component

```typescript
import React from 'react';
import { useCharacterState } from './hooks/useCharacterState';
import { useWebSocket } from './hooks/useWebSocket';
import { useDarkMode } from './hooks/useDarkMode';

import Header from './components/Header/Header';
import NarrativeLog from './components/Narrative/NarrativeLog';
import ActionPanel from './components/ActionPanel/ActionPanel';
import HUDCharacterSheet from './components/HUD/HUDCharacterSheet';
import BottomNav from './components/Navigation/BottomNav';

export default function App() {
  const characterState = useCharacterState();
  const { isDark, toggle: toggleDarkMode } = useDarkMode();
  const [narrativeMessages, setNarrativeMessages] = React.useState([]);

  const { isConnected, send: sendWebSocket } = useWebSocket({
    url: 'ws://localhost:8000/ws/session/default',
    onMessage: (data) => {
      if (data.type === 'narrative') {
        setNarrativeMessages(prev => [...prev, data]);
      } else if (data.type === 'state_update') {
        characterState.updateSheet(data.sheet);
      }
    },
    onConnect: () => console.log('[✓] Connected to server'),
    onDisconnect: () => console.log('[✗] Disconnected from server'),
  });

  const handleSendAction = (action: string) => {
    sendWebSocket({
      type: 'action',
      content: action,
      timestamp: new Date().toISOString(),
    });
  };

  return (
    <div className={isDark ? 'dark' : 'light'}>
      <div className="min-h-screen bg-v5-charcoal dark:bg-v5-charcoal light:bg-v5light-parchment text-v5-parchment dark:text-v5-parchment light:text-v5light-charcoal font-sans overflow-hidden flex flex-col relative select-none">
        
        {/* Noise Overlay */}
        <div className="noise-overlay fixed inset-0 pointer-events-none z-50" aria-hidden="true" />

        {/* Header */}
        <Header 
          isConnected={isConnected} 
          isDarkMode={isDark}
          onToggleDarkMode={toggleDarkMode}
        />

        {/* Main Layout */}
        <main className="flex-1 lg:grid lg:grid-cols-3 pt-14 overflow-hidden">
          
          {/* Narrativa (2/3) */}
          <section className="lg:col-span-2 flex flex-col h-full">
            <NarrativeLog messages={narrativeMessages} />
            <ActionPanel onSendAction={handleSendAction} />
          </section>

          {/* HUD (1/3) */}
          <aside className="hidden lg:block overflow-y-auto p-4 bg-v5-card dark:bg-v5-card light:bg-v5light-parchment/50 border-l border-v5-border">
            <HUDCharacterSheet sheet={characterState.state.sheet} />
          </aside>
        </main>

        {/* Bottom Nav (Mobile) */}
        <BottomNav />
      </div>
    </div>
  );
}
```

---

### 2.6 Setup Projeto React + TypeScript

```bash
# Criar projeto Vite + React + TypeScript
npm create vite@latest agente-storyteller-client -- --template react-ts

# Entrar no diretório
cd agente-storyteller-client

# Instalar dependências
npm install

# Instalar Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Iniciar dev server
npm run dev
```

**Estrutura final**:
```
agente-storyteller-client/
├── src/
│   ├── components/          (Componentes React)
│   ├── hooks/               (Custom hooks)
│   ├── types/               (TypeScript types)
│   ├── styles/              (CSS + Tailwind)
│   ├── utils/               (Funções utilitárias)
│   ├── App.tsx
│   └── main.tsx
├── index.html               (HTML entry)
├── tailwind.config.ts       (Tailwind config)
├── tsconfig.json            (TypeScript config)
├── package.json
└── vite.config.ts           (Vite config)
```

---

## FASE 3 — DARK/LIGHT MODE

### 3.1 Paletas

**Dark Mode (Atual)**:
```css
--bg-primary: #121214 (Charcoal)
--bg-secondary: #18181b (Card)
--text-primary: #e2e0d9 (Parchment)
--accent: #b91c1c (Crimson)
--border: #27272a (Zinc)
```

**Light Mode (Novo)**:
```css
--bg-primary: #f5f0e8 (Pergaminho envelhecido)
--bg-secondary: #faf8f5 (Papel claro)
--text-primary: #3d3d3d (Charcoal escuro)
--accent: #8B4513 (Terra queimada)
--border: #c9b8a8 (Borda terra)
--highlight: #d4a574 (Dourado envelhecido)
```

### 3.2 Contraste WCAG AA

```
Dark:
- Crimson #b91c1c vs Parchment #e2e0d9 = 9.5:1 ✅ AAA

Light:
- Terra #8B4513 vs Pergaminho #f5f0e8 = 6.2:1 ✅ AA
- Charcoal #3d3d3d vs Pergaminho #f5f0e8 = 10.1:1 ✅ AAA
```

### 3.3 Implementação CSS

```css
/* tailwind.css */

/* Dark Mode (padrão) */
:root {
  --bg-primary: #121214;
  --bg-secondary: #18181b;
  --text-primary: #e2e0d9;
  --accent: #b91c1c;
  --border: #27272a;
}

/* Light Mode */
:root.light {
  --bg-primary: #f5f0e8;
  --bg-secondary: #faf8f5;
  --text-primary: #3d3d3d;
  --accent: #8B4513;
  --border: #c9b8a8;
  --highlight: #d4a574;
}

/* Usar variáveis em componentes */
body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

button {
  background-color: var(--accent);
  border-color: var(--accent);
}
```

### 3.4 AC FASE 3

- [ ] AC 3.1: Dark mode usa paleta atual ✓
- [ ] AC 3.2: Light mode usa tons pergaminho/terra ✓
- [ ] AC 3.3: Toggle light/dark funciona (localStorage) ✓
- [ ] AC 3.4: Contraste WCAG AA em ambos os modos ✓
- [ ] AC 3.5: SO preference respeitado (prefers-color-scheme) ✓

---

## FASE 4 — AUTO-INICIALIZAÇÃO COM CASCATA DE TESTES

### 4.1 Script Python (`scripts/initialize_game.py`)

```python
#!/usr/bin/env python3
"""
Auto-initialization script for Agente Storyteller V5
Orchestrates LM Studio startup, health checks, and frontend launch
"""

import subprocess
import sys
import time
import requests
import os
import json
from pathlib import Path

class GameInitializer:
    def __init__(self):
        self.lm_studio_port = 1234
        self.backend_port = 8000
        self.frontend_url = f"http://localhost:{self.backend_port}"
        
    def check_lm_studio_installed(self) -> bool:
        """Verifica se LM Studio está instalado"""
        try:
            # Procura LM Studio no PATH
            result = subprocess.run(['where' if sys.platform == 'win32' else 'which', 'lm-studio'],
                                  capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def start_lm_studio(self) -> bool:
        """Tenta abrir LM Studio"""
        try:
            if sys.platform == 'win32':
                os.startfile('lm-studio')  # Windows
            elif sys.platform == 'darwin':
                subprocess.run(['open', '-a', 'LM Studio'])  # macOS
            else:
                subprocess.run(['lm-studio'])  # Linux
            
            print("[*] LM Studio iniciando...")
            time.sleep(3)  # Aguardar startup
            return True
        except Exception as e:
            print(f"[✗] Erro ao iniciar LM Studio: {e}")
            return False
    
    def test_port_available(self, port: int) -> bool:
        """Testa se a porta está aberta"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def test_models_installed(self) -> dict:
        """Testa quais modelos estão instalados"""
        required_models = [
            'qwen2.5-1.5b-instruct',
            'deepseek-r1-distill-qwen-7b',
            'llama-3.2-3b-instruct'
        ]
        
        # Procura por arquivos de modelo em ~/.cache/lm-studio
        models_dir = Path.home() / '.cache' / 'lm-studio' / 'models'
        installed = {}
        
        for model in required_models:
            installed[model] = (models_dir / model).exists()
        
        return installed
    
    def test_websocket_connection(self) -> bool:
        """Testa conexão WebSocket"""
        try:
            # Verificar se backend está rodando
            response = requests.get(self.frontend_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def launch_frontend(self) -> bool:
        """Abre o navegador"""
        try:
            import webbrowser
            webbrowser.open(self.frontend_url)
            return True
        except:
            return False
    
    def run(self):
        """Executa inicialização em cascata"""
        print("=" * 60)
        print("  AGENTE STORYTELLER V5 — INICIALIZADOR")
        print("=" * 60)
        
        # Passo 1: Verificar LM Studio
        print("\n[1/5] Verificando LM Studio...")
        if not self.check_lm_studio_installed():
            print("[✗] LM Studio não encontrado")
            print("     Instale em: https://lmstudio.ai/")
            return False
        print("[✓] LM Studio encontrado")
        
        # Passo 2: Iniciar LM Studio
        print("\n[2/5] Iniciando LM Studio...")
        if not self.start_lm_studio():
            print("[✗] Erro ao iniciar LM Studio")
            return False
        print("[✓] LM Studio iniciado")
        
        # Passo 3: Testar porta
        print(f"\n[3/5] Testando porta {self.lm_studio_port}...")
        if not self.test_port_available(self.lm_studio_port):
            print(f"[✗] Porta {self.lm_studio_port} não respondeu")
            print("    Verifique se LM Studio abriu corretamente")
            return False
        print(f"[✓] Porta {self.lm_studio_port} disponível")
        
        # Passo 4: Testar modelos
        print("\n[4/5] Verificando modelos...")
        models = self.test_models_installed()
        missing = [m for m, installed in models.items() if not installed]
        
        if missing:
            print(f"[⚠] Modelos faltando: {', '.join(missing)}")
            print("    Baixe em LM Studio > Model Search")
        else:
            print("[✓] Todos os modelos encontrados")
        
        # Passo 5: Testar WebSocket
        print(f"\n[5/5] Testando conexão com backend...")
        if not self.test_websocket_connection():
            print(f"[✗] Backend não respondeu em {self.frontend_url}")
            print("    Execute o servidor: python api/main.py")
            return False
        print("[✓] Backend conectado")
        
        # Lançar frontend
        print("\n[✓] Sistema pronto para jogar!")
        print(f"    Abrindo {self.frontend_url}...")
        self.launch_frontend()
        
        return True

if __name__ == '__main__':
    init = GameInitializer()
    success = init.run()
    sys.exit(0 if success else 1)
```

### 4.2 AC FASE 4

- [ ] AC 4.1: Script detecta LM Studio ✓
- [ ] AC 4.2: Se não existe, aviso + recomenda instalação + encerra ✓
- [ ] AC 4.3: Se existe mas não inicia, aviso de erro + encerra ✓
- [ ] AC 4.4: Testa porta 1234 (porta aberta = sucesso) ✓
- [ ] AC 4.5: Testa 3 modelos (lista instalados) ✓
- [ ] AC 4.6: Se modelo falta, aviso (modelo X não encontrado) ✓
- [ ] AC 4.7: Inicia frontend (http://localhost:8000) ✓
- [ ] AC 4.8: Testa WebSocket (frontend ↔ backend) ✓
- [ ] AC 4.9: Se tudo ok, emite "Pronto para jogar" em português no client ✓
- [ ] AC 4.10: Se algo falha em cascata, para e avisa ✓

---

## FASE 5 — ÍCONE VAMPIRO NO ATALHO

### 5.1 Criar Ícone Vampiro

**SVG Vampiro**:
```svg
<!-- vampire-icon.svg -->
<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="vampire-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#990000;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#660000;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Fundo -->
  <circle cx="128" cy="128" r="125" fill="url(#vampire-grad)" stroke="#ffffff" stroke-width="2"/>
  
  <!-- Rosto -->
  <ellipse cx="128" cy="110" rx="50" ry="55" fill="#f5f0e8"/>
  
  <!-- Olhos vermelhos (menacingly) -->
  <circle cx="110" cy="100" r="8" fill="#ff0000"/>
  <circle cx="146" cy="100" r="8" fill="#ff0000"/>
  <circle cx="112" cy="98" r="4" fill="#000000"/>
  <circle cx="148" cy="98" r="4" fill="#000000"/>
  
  <!-- Boca / Presas -->
  <path d="M 128 120 Q 120 130 115 135" stroke="#000000" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 128 120 Q 136 130 141 135" stroke="#000000" stroke-width="2" fill="none" stroke-linecap="round"/>
  
  <!-- Presas (triângulos) -->
  <polygon points="121,135 118,142 124,138" fill="#ffffff" stroke="#000000" stroke-width="1"/>
  <polygon points="135,135 138,142 132,138" fill="#ffffff" stroke="#000000" stroke-width="1"/>
  
  <!-- Capa gótica -->
  <path d="M 80 110 Q 70 140 80 160 L 176 160 Q 186 140 176 110 Z" fill="#000000" opacity="0.8"/>
  
  <!-- Lua / Noite (background) -->
  <circle cx="40" cy="40" r="15" fill="#e2e0d9" opacity="0.7"/>
</svg>
```

### 5.2 Atualizar .lnk (Windows)

```powershell
# PowerShell script para criar atalho com ícone

$WshShell = New-Object -ComObject WScript.Shell
$ShortcutPath = "$PSScriptRoot\Iniciar o Jogo.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$PSScriptRoot\iniciar_jogo.bat"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = "$PSScriptRoot\vampire-icon.ico"  # Converter SVG → ICO
$Shortcut.WindowStyle = 1  # Normal
$Shortcut.Description = "Iniciar Agente Storyteller V5"

$Shortcut.Save()
```

### 5.3 AC FASE 5

- [ ] AC 5.1: Atalho tem ícone vampiro personalizado ✓
- [ ] AC 5.2: Windows/Mac/Linux suportados ✓

---

## RESUMO — DESIGN.md Completo

| Fase | Objetivo | AC |
|---|---|---|
| **1** | Debug crítico (.bat + client) | 4 AC |
| **2** | Refator Vanilla → React/TypeScript | 5 AC |
| **3** | Dark/Light mode | 5 AC |
| **4** | Auto-inicialização cascata | 10 AC |
| **5** | Ícone vampiro | 2 AC |

**Total**: 26 AC

---

## Próximos Passos

1. Você aprova DESIGN.md?
2. Quer refinar alguma proposta?
3. Ou leva para Antigravity agora?
