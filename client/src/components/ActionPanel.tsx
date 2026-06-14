import { useState } from 'react';
import { Send } from 'lucide-react';
import type { PlayerSheet, Relationship } from '../types/character';

interface ActionPanelProps {
  sheet: PlayerSheet;
  relationships: Relationship[];
  onSendAction: (action: string) => void;
  onConsultRelation: (title: string, desc: string) => void;
  disabled?: boolean;
}

const translateSkill = (key: string): string => {
  const map: Record<string, string> = {
    Athletics: "Atletismo", Brawl: "Briga", Craft: "Ofício", Drive: "Condução",
    Firearms: "Armas de Fogo", Larceny: "Ladrão", Melee: "Armas Brancas",
    Stealth: "Furtividade", Survival: "Sobrevivência", AnimalKen: "Trato com Animais",
    Etiquette: "Etiqueta", Insight: "Intuição", Intimidation: "Intimidação",
    Leadership: "Liderança", Performance: "Performance", Persuasion: "Persuasão",
    Streetwise: "Manha", Subterfuge: "Subterfúgio", Academics: "Acadêmicos",
    Awareness: "Percepção", Finance: "Finanças", Investigation: "Investigação",
    Medicine: "Medicina", Occult: "Ocultismo", Politics: "Política",
    Science: "Ciência", Technology: "Tecnologia"
  };
  return map[key] || key;
};

const translateDiscipline = (key: string): string => {
  const map: Record<string, string> = {
    animalism: "Animalismo", auspex: "Auspício", celerity: "Rapidez",
    dominate: "Dominar", fortitude: "Fortitude", obfuscate: "Ofuscação",
    potence: "Potência", presence: "Presença", protean: "Metamorfose",
    blood_sorcery: "Feitiçaria de Sangue", feral_weapons: "Armas Ferais",
    scorpion_touch: "Toque do Escorpião", awe: "Fascínio"
  };
  return map[key] || key.replace(/_/g, " ");
};



export const ActionPanel: React.FC<ActionPanelProps> = ({
  sheet,
  relationships,
  onSendAction,
  onConsultRelation,
  disabled
}) => {
  const [inputText, setInputText] = useState('');
  const [isFlashing, setIsFlashing] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || disabled) return;

    // Efeito de flash de envio
    setIsFlashing(true);
    setTimeout(() => setIsFlashing(false), 500);

    onSendAction(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>, type: 'skill' | 'discipline' | 'relation' | 'macro') => {
    const val = e.target.value;
    if (!val || disabled) return;

    if (type === 'relation') {
      const found = relationships.find(r => r.id === val);
      if (found) {
        onConsultRelation(found.titulo, found.desc);
        const npcName = found.titulo.split('—')[1]?.trim() || found.titulo;
        onSendAction(`Consultando relacionamento com ${npcName}`);
      }
    } else {
      onSendAction(val);
    }

    // Reset dropdown selection
    e.target.selectedIndex = 0;
  };

  return (
    <div 
      className={`w-full bg-v5-card/90 dark:bg-v5-card/90 light:bg-v5light-card/95 border-t border-zinc-800/80 dark:border-zinc-800/80 light:border-v5light-border/80 backdrop-blur z-20 p-4 space-y-3 transition-colors duration-300 ${
        isFlashing ? 'bg-v5-blood/10 dark:bg-v5-blood/10 light:bg-v5light-earth/10' : ''
      }`}
      id="action-panel-container"
    >
      <form onSubmit={handleSubmit} className="flex gap-2">
        <textarea
          id="user-input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? "Aguardando resposta do Narrador..." : "Descreva sua ação (ex: 'Investigar o galpão abandonado') ou rolagem..."}
          className="flex-1 min-h-[44px] max-h-[120px] bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded p-2 text-sm focus:outline-none focus:ring-1 focus:ring-v5-crimson dark:focus:ring-v5-crimson light:focus:ring-v5light-earth resize-none leading-relaxed text-primary"
          style={{ color: 'var(--text-primary)' }}
          rows={2}
          aria-label="Ação do Jogador"
        />
        <button
          type="submit"
          disabled={disabled || !inputText.trim()}
          id="btn-send-trigger"
          className="w-12 bg-v5-crimson hover:bg-red-800 dark:bg-v5-crimson dark:hover:bg-red-800 light:bg-v5light-earth light:hover:bg-amber-900 text-white rounded flex items-center justify-center cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title="Enviar Ação"
          aria-label="Enviar Ação"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Dropdowns reativos de ações rápidas */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {/* Macros */}
        <select
          id="macro-select"
          disabled={disabled}
          onChange={(e) => handleSelectChange(e, 'macro')}
          className="bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded p-1.5 focus:outline-none text-secondary"
          style={{ color: 'var(--text-secondary)' }}
          aria-label="Macros de ações rápidas"
        >
          <option value="" disabled selected hidden>Ações Rápidas...</option>
          <option value="Inicie uma nova crônica.">Iniciar Nova Crônica</option>
          <option value="Fazer teste de Força + Briga com Dificuldade 3">Atacar com Briga (Força + Briga, Dif 3)</option>
          <option value="Fazer teste de Destreza + Furtividade com Dificuldade 2">Esgueirar-se (Destreza + Fur, Dif 2)</option>
          <option value="Fazer teste de Raciocínio + Percepção com Dificuldade 3">Investigar Ambiente (Wits + Aware, Dif 3)</option>
          <option value="Usar poder de Rapidez para esquiva rápida">Ativar Rapidez (Esquiva)</option>
          <option value="Realizar teste de Humanidade para resistir a máculas">Resistir a Máculas (Humanidade)</option>
        </select>

        {/* Habilidades */}
        <select
          id="hud-skills-select"
          disabled={disabled}
          onChange={(e) => handleSelectChange(e, 'skill')}
          className="bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded p-1.5 focus:outline-none text-secondary"
          style={{ color: 'var(--text-secondary)' }}
          aria-label="Fazer teste de habilidade"
        >
          <option value="" disabled selected hidden>Habilidades...</option>
          {Object.entries(sheet.skills).map(([key, val]) => (
            <option key={key} value={`Fazer teste de ${translateSkill(key)}`}>
              {translateSkill(key)} (Nível {val})
            </option>
          ))}
        </select>

        {/* Disciplinas */}
        <select
          id="hud-disciplines-select"
          disabled={disabled}
          onChange={(e) => handleSelectChange(e, 'discipline')}
          className="bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded p-1.5 focus:outline-none text-secondary"
          style={{ color: 'var(--text-secondary)' }}
          aria-label="Ativar disciplina"
        >
          <option value="" disabled selected hidden>Disciplinas...</option>
          {Object.entries(sheet.disciplines).map(([key, val]) => (
            <option key={key} value={`Ativar disciplina ${translateDiscipline(key)}`}>
              {translateDiscipline(key)} (Nível {val})
            </option>
          ))}
        </select>

        {/* Relacionamentos */}
        <select
          id="hud-relations-select"
          disabled={disabled}
          onChange={(e) => handleSelectChange(e, 'relation')}
          className="bg-zinc-950/40 dark:bg-zinc-950/40 light:bg-v5light-card border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded p-1.5 focus:outline-none text-secondary"
          style={{ color: 'var(--text-secondary)' }}
          aria-label="Consultar relacionamento"
        >
          <option value="" disabled selected hidden>Relacionamentos...</option>
          {relationships.map((item) => (
            <option key={item.id} value={item.id}>
              {item.titulo}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};
export default ActionPanel;
