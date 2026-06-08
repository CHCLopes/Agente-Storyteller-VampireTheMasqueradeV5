import { useState, useCallback } from 'react';
import type { PlayerSheet } from '../types/character';

const defaultPlayerSheet: PlayerSheet = {
  nome: "Karl Brujah",
  clan: "Brujah",
  geracao: "11ª Geração",
  attributes: {
    Strength: 3, Dexterity: 3, Stamina: 3,
    Charisma: 2, Manipulation: 2, Composure: 3,
    Intelligence: 2, Wits: 3, Resolve: 3
  },
  skills: {
    Athletics: 2, Brawl: 3, Firearms: 1, Melee: 2,
    Stealth: 1, Insight: 2, Intimidation: 2, Persuasion: 1,
    Streetwise: 2, Awareness: 2, Occult: 1
  },
  disciplines: {
    potence: 2,
    celerity: 1,
    presence: 1
  },
  available_xp: 0,
  status: {
    current_hunger: 1,
    health_tracker: { size: 7, superficial: 0, aggravated: 0 },
    willpower_tracker: { size: 5, superficial: 0, aggravated: 0 },
    humanity: 7,
    stains: 0
  }
};

export const useCharacterState = () => {
  const [sheet, setSheet] = useState<PlayerSheet>(defaultPlayerSheet);

  const updateSheetFromEvent = useCallback((eventData: any) => {
    if (!eventData) return;
    
    // Suporte ao evento de sincronização que o backend envia
    let rawSheet = eventData.player_sheet;
    
    // Se estiver aninhado
    if (rawSheet && rawSheet.player_sheet) {
      rawSheet = rawSheet.player_sheet;
    }

    if (!rawSheet) return;

    setSheet(prev => {
      const newSheet = { ...prev };
      
      if (rawSheet.nome) newSheet.nome = rawSheet.nome;
      if (rawSheet.clan) newSheet.clan = rawSheet.clan;
      if (rawSheet.geracao) newSheet.geracao = rawSheet.geracao;
      if (rawSheet.attributes) newSheet.attributes = { ...rawSheet.attributes };
      if (rawSheet.skills) newSheet.skills = { ...rawSheet.skills };
      if (rawSheet.disciplines) newSheet.disciplines = { ...rawSheet.disciplines };
      if (typeof rawSheet.available_xp === 'number') newSheet.available_xp = rawSheet.available_xp;

      if (rawSheet.status) {
        newSheet.status = {
          current_hunger: typeof rawSheet.status.current_hunger === 'number' 
            ? rawSheet.status.current_hunger 
            : prev.status?.current_hunger ?? 1,
          health_tracker: rawSheet.status.health_tracker 
            ? { ...rawSheet.status.health_tracker } 
            : prev.status?.health_tracker ?? { size: 7, superficial: 0, aggravated: 0 },
          willpower_tracker: rawSheet.status.willpower_tracker 
            ? { ...rawSheet.status.willpower_tracker } 
            : prev.status?.willpower_tracker ?? { size: 5, superficial: 0, aggravated: 0 },
          humanity: typeof rawSheet.status.humanity === 'number' 
            ? rawSheet.status.humanity 
            : prev.status?.humanity ?? 7,
          stains: typeof rawSheet.status.stains === 'number' 
            ? rawSheet.status.stains 
            : prev.status?.stains ?? 0,
        };
      }

      return newSheet;
    });
  }, []);

  return {
    sheet,
    updateSheetFromEvent
  };
};
