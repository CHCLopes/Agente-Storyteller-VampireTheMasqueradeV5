import { useEffect, useRef, useState, useCallback } from 'react';

interface UseWebSocketProps {
  sessionId: string;
  onMessage: (data: unknown) => void;
}

export interface TurnInputEnvelope {
  operation_id: string;
  input: string;
}

interface PendingAction {
  envelope: TurnInputEnvelope;
  sent: boolean;
}

const MAX_RECONNECT_ATTEMPTS = 10;
const STABLE_CONNECTION_MS = 10_000;

const createOperationId = (): string => {
  const randomId = globalThis.crypto?.randomUUID?.();
  return randomId
    ? `op-${randomId}`
    : `op-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const isCanonicalSnapshot = (data: unknown): boolean => {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) return false;
  const event = data as Record<string, unknown>;
  return event.action === 'state_update' || event.event === 'state_update';
};

const terminalOperationId = (data: unknown): string | null => {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) return null;
  const event = data as Record<string, unknown>;
  if (typeof event.operation_id !== 'string') return null;
  if (event.action === 'stream_end' && event.status !== 'pending') {
    return event.operation_id;
  }
  if (event.action === 'narration_paused' && typeof event.source_operation_id === 'string') {
    return event.source_operation_id;
  }
  if (event.terminal === true) return event.operation_id;
  return null;
};

export const useWebSocket = ({ sessionId, onMessage }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const connectRef = useRef<() => void>(() => undefined);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const stableConnectionTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);
  const pendingActionRef = useRef<PendingAction | null>(null);

  // Mantém a referência do callback atualizada sem causar re-render/reconexão
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '5173' ? 'localhost:8000' : (window.location.host || 'localhost:8000');
    const wsUrl = `${protocol}//${host}/ws/session/${sessionId}`;

    console.log(`[WS] Conectando a ${wsUrl}...`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('[WS] Conectado.');
      setIsConnected(true);
      setConnectionError(false);

      if (stableConnectionTimeoutRef.current !== null) {
        clearTimeout(stableConnectionTimeoutRef.current);
      }
      stableConnectionTimeoutRef.current = window.setTimeout(() => {
        if (wsRef.current === socket && socket.readyState === WebSocket.OPEN) {
          reconnectAttemptsRef.current = 0;
        }
        stableConnectionTimeoutRef.current = null;
      }, STABLE_CONNECTION_MS);

      const pending = pendingActionRef.current;
      if (pending?.sent) {
        try {
          socket.send(JSON.stringify(pending.envelope));
        } catch (err) {
          console.error('[WS] Falha ao reenviar ação pendente:', err);
          setConnectionError(true);
          setIsConnected(false);
        }
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (wsRef.current === socket && isCanonicalSnapshot(data)) {
          reconnectAttemptsRef.current = 0;
          if (stableConnectionTimeoutRef.current !== null) {
            clearTimeout(stableConnectionTimeoutRef.current);
            stableConnectionTimeoutRef.current = null;
          }
        }
        const completedOperationId = terminalOperationId(data);
        if (
          completedOperationId !== null
          && pendingActionRef.current?.envelope.operation_id === completedOperationId
        ) {
          pendingActionRef.current = null;
        }
        onMessageRef.current(data);
      } catch (err) {
        console.error('[WS] Erro ao parsear mensagem:', err, event.data);
      }
    };

    socket.onerror = (err) => {
      console.error('[WS] Erro na conexão:', err);
      setConnectionError(true);
      setIsConnected(false);
    };

    socket.onclose = () => {
      setIsConnected(false);

      if (stableConnectionTimeoutRef.current !== null) {
        clearTimeout(stableConnectionTimeoutRef.current);
        stableConnectionTimeoutRef.current = null;
      }
      
      // Limpa timeout anterior se houver
      if (reconnectTimeoutRef.current !== null) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      // Backoff exponencial: 1s, 2s, 4s, 8s, 16s, max 30s — limite de 10 tentativas
      const attempt = reconnectAttemptsRef.current;
      if (attempt >= MAX_RECONNECT_ATTEMPTS) {
        console.warn(`[WS] Limite de reconexões atingido (${MAX_RECONNECT_ATTEMPTS}). Parado.`);
        setConnectionError(true);
        return;
      }

      const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
      console.log(`[WS] Desconectado. Tentativa ${attempt + 1}/${MAX_RECONNECT_ATTEMPTS} em ${delay / 1000}s...`);
      reconnectAttemptsRef.current = attempt + 1;
      
      reconnectTimeoutRef.current = window.setTimeout(() => {
        reconnectTimeoutRef.current = null;
        connectRef.current();
      }, delay);
    };

    wsRef.current = socket;
  }, [sessionId]);

  useEffect(() => {
    connectRef.current = connect;
    reconnectAttemptsRef.current = 0;
    pendingActionRef.current = null;
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // Evita reconexão automática ao desmontar
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current !== null) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (stableConnectionTimeoutRef.current !== null) {
        clearTimeout(stableConnectionTimeoutRef.current);
        stableConnectionTimeoutRef.current = null;
      }
    };
  }, [connect]);

  const send = useCallback((message: unknown) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        const payload = typeof message === 'string' ? message : JSON.stringify(message);
        if (payload === undefined) return false;
        wsRef.current.send(payload);
        return true;
      } catch (err) {
        console.error('[WS] Falha ao enviar mensagem:', err);
        setConnectionError(true);
        setIsConnected(false);
        return false;
      }
    }
    console.warn('[WS] Tentativa de envio sem conexão ativa.');
    return false;
  }, []);

  const sendAction = useCallback((input: string) => {
    const normalized = input.trim();
    if (!normalized) return false;

    let pending = pendingActionRef.current;
    if (pending?.envelope.input !== normalized) {
      pending = {
        envelope: {
          operation_id: createOperationId(),
          input: normalized,
        },
        sent: false,
      };
      pendingActionRef.current = pending;
    }

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Tentativa de envio sem conexão ativa.');
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify(pending.envelope));
      pendingActionRef.current = { ...pending, sent: true };
      return true;
    } catch (err) {
      console.error('[WS] Falha ao enviar ação:', err);
      setConnectionError(true);
      setIsConnected(false);
      return false;
    }
  }, []);

  return { isConnected, connectionError, send, sendAction };
};
