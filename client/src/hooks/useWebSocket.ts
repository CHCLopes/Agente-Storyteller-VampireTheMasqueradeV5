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

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const wsUrl = `${protocol}//${host}/ws/session/${sessionId}`;

    console.log(`[WS] Conectando a ${wsUrl}...`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('[WS] Conectado.');
      setIsConnected(true);
      setConnectionError(false);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
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
      console.log('[WS] Desconectado. Tentando reconectar em 3s...');
      setIsConnected(false);
      
      // Limpa timeout anterior se houver
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, 3000);
    };

    wsRef.current = socket;
  }, [sessionId, onMessage]);

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
