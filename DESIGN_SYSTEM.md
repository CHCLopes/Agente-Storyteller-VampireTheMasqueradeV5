# DESIGN_SYSTEM.md — Agente Storyteller V5

## Cor & Tipografia

### Paleta Principal
- **Crimson Red**: #990000 (acentos, borders, hover states)
- **Charcoal Black**: #121212 (background principal)
- **Neutral Gray**: #2a2a2a (secondary background)
- **Text White**: #f5f5f5 (texto principal)

### Modo Dark/Light
- Dark Mode (default): Charcoal + Crimson
- Light Mode: Branco + Marrom escuro (implementado via persistencia de useDarkMode)

### Tipografia
- **Font Family**: Outfit (títulos), Inter (corpo)
- **Sizes**: 
  - H1 (títulos): 32px, peso 700
  - H2 (subtítulos): 20px, peso 600
  - Body (texto): 14px, peso 400
  - Small (labels): 12px, peso 500

## Componentes UI Base

### Button
Variantes:
- **Primary**: Fundo Crimson, texto branco, sem borda
- **Secondary**: Borda Crimson, fundo transparent, texto Crimson
- **Danger**: Fundo vermelho escuro, texto branco (para ações críticas)

Estados:
- **Normal**: Cor base
- **Hover**: Brilho +20% (glow effect)
- **Disabled**: Opacidade 50%
- **Active**: Border 2px Crimson

Exemplo (HTML):
```html
<button class="btn btn-primary">Rolar Dados</button>
<button class="btn btn-secondary">Cancelar</button>
```

### Input
Estados:
- **Default**: Borda 1px Neutral Gray, fundo Charcoal
- **Focus**: Borda 2px Crimson, glow effect
- **Error**: Borda 2px vermelho claro, background rosa suave

Exemplo (HTML):
```html
<input type="text" class="input" placeholder="Nome da ação">
<input type="number" class="input input-focus">
```

### Card
Layout: Container retangular com padding 16px
- **Background**: Neutral Gray (#2a2a2a)
- **Border**: 1px Crimson (sutil)
- **Border-radius**: 4px
- **Shadow**: Nenhuma (flat design)

Exemplo (HTML):
```html
<div class="card">
  <h3>Estado do Personagem</h3>
  <p>Humanidade: 8</p>
  <p>Fome: 2</p>
</div>
```

### Modal
- **Overlay**: Charcoal Black, opacidade 70%
- **Modal Body**:
  - Background: Neutral Gray
  - Border: 2px Crimson
  - Width: 60% viewport (máx 600px)
  - Padding: 24px

Exemplo (HTML):
```html
<div class="modal">
  <div class="modal-header">
    <h2>Generar Narrativa</h2>
    <button class="btn-close">&times;</button>
  </div>
  <div class="modal-body">
    [...conteúdo]
  </div>
</div>
```

## Grid & Layout

### Breakpoints
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

### Macro Layout (App-Shell)
```
┌─────────────────────────────────────────┐
│     Header (Título + Status Bar)        │
├──────────────────┬──────────────────────┤
│   Sidebar 1/3    │   Main Content 2/3   │
│ (Ficha do PC)    │ (Chat + Narrativa)   │
│                  │                      │
│                  │                      │
│                  │                      │
├──────────────────┴──────────────────────┤
│     Footer (Input + Botões de Ação)     │
└─────────────────────────────────────────┘
```

### Spacing Scale
- **xs**: 4px
- **sm**: 8px
- **md**: 16px
- **lg**: 24px
- **xl**: 32px

## Tokens Tailwind (Se aplicável)
```javascript
// Tailwind CSS v4 Theme Config (implementado em client/src/index.css)
module.exports = {
  theme: {
    colors: {
      'crimson': '#990000',
      'charcoal': '#121212',
      'neutral-gray': '#2a2a2a',
      'text-white': '#f5f5f5',
    },
    fontSize: {
      'h1': '32px',
      'h2': '20px',
      'body': '14px',
      'small': '12px',
    },
    spacing: {
      'xs': '4px',
      'sm': '8px',
      'md': '16px',
      'lg': '24px',
      'xl': '32px',
    },
  },
};
```

## Icon System
Library: Lucide Icons (ou similar)
- **Icons**: 24x24px (padrão)
- **Cores**: Text White ou Crimson (conforme contexto)
- **Uso**: Botões de ação, status indicators

Exemplos:
- Rolar dados: dice icon
- Enviar ação: send icon
- Fechar: x icon
- Menu: menu icon

## Accessibility & Semantics

### WCAG AA Compliance
- ✅ Contraste de cores: 4.5:1 (texto vs fundo)
- ✅ Keyboard navigation: Tab através de buttons/inputs
- ✅ Focus visible: Border 2px Crimson em elementos focados
- ✅ Semantic HTML: `<button>`, `<input>`, `<form>`, `<h1>`-`<h3>`

### ARIA Labels
```html
<button aria-label="Rolar dados do personagem">
  <span class="icon-dice"></span>
</button>

<input 
  type="text" 
  aria-label="Campo para descrever ação"
  placeholder="Descreva sua ação..."
>
```

### Color Accessibility
Não use cor como único indicador de estado. Adicione textos ou ícones para reforçar.

Exemplo:
```html
<!-- ❌ Ruim -->
<div class="status crimson">Crítico</div>

<!-- ✅ Bom -->
<div class="status status-critical">
  <span class="icon-alert"></span> Crítico
</div>
```
