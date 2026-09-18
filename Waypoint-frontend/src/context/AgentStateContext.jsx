import React, { createContext, useContext, useState, useRef } from 'react';

const AgentStateContext = createContext();

// VITE_API_URL tanımlı değilse varsayılan yerel backend portuna (8000) yönlenir
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const QUERY_TYPES = {
  FLIGHT: 'flight',
  HOTEL: 'hotel',
  FLIGHT_HOTEL: 'flight_hotel',
  SIGHTSEEING: 'sightseeing'
};

const resolveIntent = (backendIntent, currentIntent) => {
  if (backendIntent) {
    return backendIntent;
  }
  return currentIntent;
};

const agentNameForIntent = (intent) => {
  switch (intent) {
    case QUERY_TYPES.FLIGHT:
      return 'Flight Agent';
    case QUERY_TYPES.HOTEL:
      return 'Hotel Agent';
    case QUERY_TYPES.SIGHTSEEING:
      return 'Sightseeing Agent';
    case QUERY_TYPES.FLIGHT_HOTEL:
      return 'Supervisor Agent';
    default:
      return 'WayPoint Supervisor';
  }
};

// Backend'deki int travelers bilgisini UI'ın beklediği nesneyle uzlaştırır
const normalizeState = (backendState, previousTravelers) => {
  if (!backendState) return {};
  const normalized = { ...backendState };
  if (typeof backendState.travelers === 'number') {
    normalized.travelers = {
      adults: backendState.travelers,
      children: previousTravelers?.children || 0,
      rooms: previousTravelers?.rooms || 1
    };
  } else if (backendState.travelers === undefined && previousTravelers) {
    normalized.travelers = previousTravelers;
  }
  return normalized;
};

const nowLabel = () =>
  new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export const AgentStateProvider = ({ children }) => {
  // Backend gerçek bir niyet döndürene kadar hiçbir mod aktif değildir —
  // bu sayede sidebar'daki rozet, gerçek bir akış başlamadan görünmez.
  const [activeIntent, setActiveIntent] = useState(null);

  // Kullanıcı bilgi girmedikçe boş durur
  const [rawState, setRawState] = useState({});

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'agent',
      agentName: 'WayPoint Supervisor',
      text: "Merhaba! Ben WayPoint seyahat asistanınızım. Size uçuş, otel veya tatil paketi planlamanızda yardımcı olabilirim. Nereye seyahat etmek istersiniz?",
      timestamp: nowLabel()
    }
  ]);

  const [isThinking, setIsThinking] = useState(false);
  const [lastExecutedTool, setLastExecutedTool] = useState(null);

  const sessionIdRef = useRef(
    (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
  );

  // Tüm alanları filtrelemeden sidebar'a sunar
  const activeAgentState = rawState;

  const sendMessage = async (userText) => {
    if (!userText.trim()) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: userText,
      timestamp: nowLabel()
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsThinking(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          sessionId: sessionIdRef.current
        })
      });

      if (!response.ok) {
        throw new Error(`API ${response.status} döndü`);
      }

      const data = await response.json();

      const newIntent = resolveIntent(data.intent, activeIntent);
      setActiveIntent(newIntent);

      // Backend context'inden gelen tüm alanları birleştirir
      if (data.state && Object.keys(data.state).length > 0) {
        setRawState((prev) => ({
          ...prev,
          ...normalizeState(data.state, prev.travelers)
        }));
      }

      setLastExecutedTool(data.toolCalled || null);

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'agent',
          agentName: agentNameForIntent(newIntent),
          text: data.reply,
          toolCall: data.toolCalled,
          results: data.results,
          timestamp: nowLabel()
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'agent',
          agentName: 'WayPoint Supervisor',
          text: `Bağlantı hatası: backend'e ulaşılamadı (${API_BASE_URL}). api_server.py'nin çalıştığından emin ol. (${err.message})`,
          timestamp: nowLabel()
        }
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <AgentStateContext.Provider
      value={{
        activeIntent,
        setActiveIntent,
        rawState,
        activeAgentState,
        messages,
        sendMessage,
        isThinking,
        lastExecutedTool
      }}
    >
      {children}
    </AgentStateContext.Provider>
  );
};

export const useAgentState = () => {
  const context = useContext(AgentStateContext);
  if (!context) throw new Error('useAgentState must be used within AgentStateProvider');
  return context;
};