export type PersistedNarrativeMessageType = 'narrator' | 'mechanics' | 'guidance';

export type MessageType =
  | 'system'
  | 'player'
  | 'error'
  | 'success'
  | 'stream'
  | PersistedNarrativeMessageType;

export interface NarrativeMessage {
  id: string;
  type: MessageType;
  content: string;
  timestamp: string;
  narrativeMode?: string;
}
