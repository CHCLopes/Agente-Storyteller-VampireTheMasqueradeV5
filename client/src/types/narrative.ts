export type MessageType = 'system' | 'narrator' | 'player' | 'error' | 'success' | 'stream';

export interface NarrativeMessage {
  id: string;
  type: MessageType;
  content: string;
  timestamp: string;
}
