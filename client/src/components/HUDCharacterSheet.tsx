import type { PlayerSheet } from '../types/character';
import { PipTracker } from './PipTracker';
import { Shield, Heart, Zap, Award } from 'lucide-react';

interface HUDCharacterSheetProps {
  sheet: PlayerSheet;
}

const translateAttribute = (key: string): string => {
  const map: Record<string, string> = {
    Strength: "Força", Dexterity: "Destreza", Stamina: "Vigor",
    Charisma: "Carisma", Manipulation: "Manipulação", Composure: "Autocontrole",
    Intelligence: "Inteligência", Wits: "Raciocínio", Resolve: "Determinação"
  };
  return map[key] || key;
};

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

export const HUDCharacterSheet: React.FC<HUDCharacterSheetProps> = ({ sheet }) => {
  const status = sheet.status || {
    current_hunger: 1,
    health_tracker: { size: 7, superficial: 0, aggravated: 0 },
    willpower_tracker: { size: 5, superficial: 0, aggravated: 0 },
    humanity: 7,
    stains: 0
  };

  return (
    <div className="space-y-6 select-text text-left">
      {/* Nome e Clã */}
      <div className="border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border pb-4">
        <h2 id="hud-character-name" className="font-serif text-2xl font-bold tracking-wide text-primary" style={{ color: 'var(--text-primary)' }}>
          {sheet.nome}
        </h2>
        <div className="flex justify-between items-center mt-1">
          <span id="hud-clan-name" className="text-xs font-semibold tracking-wider text-v5-crimson dark:text-v5-crimson light:text-v5light-earth uppercase">
            Clã {sheet.clan}
          </span>
          <span className="text-xs text-secondary" style={{ color: 'var(--text-secondary)' }}>
            {sheet.geracao}
          </span>
        </div>
      </div>

      {/* VTM Trackers (Vida, Vontade, Fome, Humanidade) */}
      <div className="space-y-4 bg-zinc-950/20 dark:bg-zinc-950/20 light:bg-v5light-card p-4 border border-zinc-800 dark:border-zinc-800 light:border-v5light-border rounded">
        {/* Saúde */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs font-bold tracking-widest uppercase text-secondary" style={{ color: 'var(--text-secondary)' }}>
            <span className="flex items-center gap-1.5"><Heart className="w-3.5 h-3.5" /> Saúde</span>
            <span className="text-[10px] opacity-75">{status.health_tracker.size - status.health_tracker.superficial - status.health_tracker.aggravated}/{status.health_tracker.size}</span>
          </div>
          <PipTracker type="health" tracker={status.health_tracker} />
        </div>

        {/* Força de Vontade */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs font-bold tracking-widest uppercase text-secondary" style={{ color: 'var(--text-secondary)' }}>
            <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> Força de Vontade</span>
            <span className="text-[10px] opacity-75">{status.willpower_tracker.size - status.willpower_tracker.superficial - status.willpower_tracker.aggravated}/{status.willpower_tracker.size}</span>
          </div>
          <PipTracker type="willpower" tracker={status.willpower_tracker} />
        </div>

        {/* Fome */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs font-bold tracking-widest uppercase text-secondary" style={{ color: 'var(--text-secondary)' }}>
            <span className="flex items-center gap-1.5 text-v5-crimson dark:text-v5-crimson light:text-v5light-hunger">
              🩸 Fome
            </span>
            <span className="text-[10px] opacity-75 text-v5-crimson dark:text-v5-crimson light:text-v5light-hunger font-bold">{status.current_hunger} / 5</span>
          </div>
          <PipTracker type="hunger" value={status.current_hunger} />
        </div>

        {/* Humanidade e XP */}
        <div className="grid grid-cols-2 gap-4 border-t border-zinc-800 dark:border-zinc-800 light:border-v5light-border pt-3 mt-2">
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-secondary block" style={{ color: 'var(--text-secondary)' }}>
              Humanidade
            </span>
            <div className="flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-bold">{status.humanity}</span>
              {status.stains > 0 && (
                <span className="text-[10px] text-red-500 font-bold" title={`${status.stains} máculas`}>
                  (+{status.stains}M)
                </span>
              )}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-secondary block" style={{ color: 'var(--text-secondary)' }}>
              Experiência
            </span>
            <div className="flex items-center gap-1.5">
              <Award className="w-4 h-4 text-amber-500" />
              <span id="hud-xp-avb" className="text-sm font-bold">{sheet.available_xp ?? 0} XP</span>
            </div>
          </div>
        </div>
      </div>

      {/* Atributos */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-widest text-secondary mb-3 border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border pb-1" style={{ color: 'var(--text-secondary)' }}>
          Atributos
        </h3>
        <div id="hud-attributes" className="grid grid-cols-3 gap-2">
          {Object.entries(sheet.attributes).map(([key, val]) => (
            <div 
              key={key} 
              className="flex flex-col bg-zinc-950/45 dark:bg-zinc-950/45 light:bg-v5light-card p-2 border border-zinc-900 dark:border-zinc-900 light:border-v5light-border rounded text-center"
            >
              <span className="text-[10px] text-secondary truncate" style={{ color: 'var(--text-secondary)' }}>
                {translateAttribute(key)}
              </span>
              <span className="text-sm font-bold tracking-wide mt-0.5">
                {val}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Habilidades e Disciplinas */}
      <div className="grid grid-cols-2 gap-4">
        {/* Disciplinas */}
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-secondary mb-2 border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border pb-1" style={{ color: 'var(--text-secondary)' }}>
            Disciplinas
          </h3>
          <div className="space-y-1 max-h-[150px] overflow-y-auto pr-1">
            {Object.entries(sheet.disciplines).map(([key, val]) => (
              <div key={key} className="flex justify-between text-xs py-1 border-b border-zinc-900/50 dark:border-zinc-900/50 light:border-v5light-border/30">
                <span className="opacity-80">{translateDiscipline(key)}</span>
                <span className="font-bold">{val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Habilidades */}
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-secondary mb-2 border-b border-zinc-800 dark:border-zinc-800 light:border-v5light-border pb-1" style={{ color: 'var(--text-secondary)' }}>
            Habilidades
          </h3>
          <div className="space-y-1 max-h-[150px] overflow-y-auto pr-1">
            {Object.entries(sheet.skills).map(([key, val]) => (
              <div key={key} className="flex justify-between text-xs py-1 border-b border-zinc-900/50 dark:border-zinc-900/50 light:border-v5light-border/30">
                <span className="opacity-80">{translateSkill(key)}</span>
                <span className="font-bold">{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
export default HUDCharacterSheet;
