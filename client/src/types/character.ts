export interface TrackerDetail {
  superficial: number;
  aggravated: number;
  size: number;
}

export interface Trackers {
  health: TrackerDetail;
  willpower: TrackerDetail;
  humanity: number;
  stains: number;
}

export interface CharacterAttributes {
  self_control: number;
  resolve: number;
}

export interface CharacterInfo {
  id: string;
  trackers: Trackers;
  attributes: CharacterAttributes;
  fome: number;
  status: string; // "ACTIVE" | "FRENZY_CHECK" | "TORPOR"
}

export interface PlayerSheet {
  nome: string;
  clan: string;
  geracao: string;
  attributes: Record<string, number>;
  skills: Record<string, number>;
  disciplines: Record<string, number>;
  available_xp?: number;
  status?: {
    current_hunger: number;
    health_tracker: { size: number; superficial: number; aggravated: number };
    willpower_tracker: { size: number; superficial: number; aggravated: number };
    humanity: number;
    stains: number;
  };
}

export interface Relationship {
  id: string;
  titulo: string;
  desc: string;
  disposition?: string;
  trust_level?: number;
  favor_balance?: number;
}
