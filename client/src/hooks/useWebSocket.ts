import { useEffect, useRef, useState, useCallback } from 'react';

interface UseWebSocketProps {
  sessionId: string;
  onMessage: (data: any) => void;
}

export const useWebSocket = ({ sessionId, onMessage }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);

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
      reconnectAttemptsRef.current = 0;
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
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
      
      // Limpa timeout anterior se houver
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      // Backoff exponencial: 1s, 2s, 4s, 8s, 16s, max 30s — limite de 10 tentativas
      const attempt = reconnectAttemptsRef.current;
      if (attempt >= 10) {
        console.warn('[WS] Limite de reconexões atingido (10). Parado.');
        setConnectionError(true);
        return;
      }

      const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
      console.log(`[WS] Desconectado. Tentativa ${attempt + 1}/10 em ${delay / 1000}s...`);
      reconnectAttemptsRef.current = attempt + 1;
      
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, delay);
    };

    wsRef.current = socket;
  }, [sessionId]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // Evita reconexão automática ao desmontar
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const send = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
      return true;
    }
    console.warn('[WS] Tentativa de envio sem conexão ativa.');
    return false;
  }, []);

  return { isConnected, connectionError, send };
};
