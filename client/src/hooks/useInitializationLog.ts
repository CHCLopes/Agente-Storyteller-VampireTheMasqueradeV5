import { useState, useEffect, useCallback, useRef } from "react";

export interface LogEntry {
  status: "pending" | "success" | "error" | "warning";
  message: string;
  phase: number;
  timestamp: number;
  id: string;
}

export function useInitializationLog(onComplete?: (success: boolean) => void) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    setError(null);
    setIsInitializing(true);

    const wsHost = window.location.port === "5173" ? "localhost:8000" : window.location.host;
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${wsHost}/ws/initialization`;

    console.log(`[Init] Conectando ao WebSocket de inicialização: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[Init] WebSocket conectado.");
      // Adiciona o log de conexão inicial
      setLogs((prev) => {
        const connLog: LogEntry = {
          status: "success",
          message: "Conectado ao servidor de inicialização",
          phase: 0,
          timestamp: Date.now(),
          id: `conn-${Date.now()}`
        };
        // Evita duplicidade se já houver
        if (prev.some(l => l.message === connLog.message)) return prev;
        return [...prev, connLog];
      });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("[Init] Log recebido:", data);

        const newLog: LogEntry = {
          status: data.status,
          message: data.message,
          phase: data.phase,
          timestamp: data.timestamp,
          id: data.id || `${data.timestamp}-${Math.random()}`
        };

        setLogs((prev) => {
          // Se o log já existir (por mensagem/id idêntico), substitui ou ignora
          const existsIdx = prev.findIndex((l) => l.id === newLog.id || (l.message === newLog.message && l.phase === newLog.phase));
          if (existsIdx > -1) {
            const next = [...prev];
            next[existsIdx] = newLog;
            return next;
          }
          return [...prev, newLog];
        });

        if (data.status === "error") {
          setIsInitializing(false);
          setError(data.message || "Erro durante a inicialização");
          if (onComplete) onComplete(false);
        } else if (data.phase === 5 && data.status === "success") {
          setIsInitializing(false);
          // Pequeno delay para o usuário ver o sucesso antes de completar
          setTimeout(() => {
            if (onComplete) onComplete(true);
          }, 800);
        }
      } catch (e) {
        console.error("[Init] Falha ao parsear mensagem:", e);
      }
    };

    ws.onerror = (err) => {
      console.error("[Init] Erro no WebSocket:", err);
    };

    ws.onclose = (event) => {
      console.log("[Init] WebSocket fechado:", event);
      if (isInitializing && !event.wasClean) {
        setTimeout(() => {
          if (wsRef.current === ws) {
            setError("Conexão perdida com o servidor de inicialização.");
            setIsInitializing(false);
          }
        }, 1000);
      }
    };
  }, [onComplete, isInitializing]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const retry = useCallback(async () => {
    setLogs([]);
    setError(null);
    setIsInitializing(true);

    const apiHost = window.location.port === "5173" ? "localhost:8000" : window.location.host;
    const apiProto = window.location.protocol;
    const retryUrl = `${apiProto}//${apiHost}/api/initialization/retry`;

    try {
      console.log(`[Init] Enviando requisição de retry: ${retryUrl}`);
      const res = await fetch(retryUrl, { method: "POST" });
      if (!res.ok) {
        throw new Error(`Servidor retornou status ${res.status}`);
      }
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
      }
    } catch (err: any) {
      console.error("[Init] Erro ao disparar retry:", err);
      setError(`Falha ao reiniciar inicialização: ${err.message || err}`);
      setIsInitializing(false);
    }
  }, [connect]);

  return { logs, isInitializing, error, retry };
}
