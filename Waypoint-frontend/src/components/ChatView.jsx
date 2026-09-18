import React, { useState, useRef, useEffect } from 'react';
import { useAgentState } from '../context/AgentStateContext';
import QuickPrompts from './QuickPrompts';
import './ChatView.css';

// Backend'den gelen metin markdown-benzeri (satır başı "* ", **kalın**,
// [metin](url) linkler) içeriyor. Burada tam bir markdown kütüphanesi
// eklemeden, ajan yanıtlarında gerçekten kullanılan bu birkaç kalıbı
// okunabilir React elemanlarına çeviriyoruz.

function renderInline(text, keyPrefix) {
  // [metin](url) ve **kalın** kalıplarını tek geçişte ayrıştır.
  const pattern = /\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*/g;
  const nodes = [];
  let lastIndex = 0;
  let match;
  let i = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    if (match[1] !== undefined) {
      nodes.push(
        <a
          key={`${keyPrefix}-l-${i++}`}
          href={match[2]}
          target="_blank"
          rel="noopener noreferrer"
        >
          {match[1]}
        </a>
      );
    } else {
      nodes.push(<strong key={`${keyPrefix}-b-${i++}`}>{match[3]}</strong>);
    }
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

function FormattedMessage({ text }) {
  if (!text) return null;

  // Ajan yanıtları çoğu zaman "* " ile başlayan tek satırlık maddeler
  // halinde geliyor (bazen gerçek \n ile, bazen tek paragrafa yapışık
  // "* ... * ..." şeklinde) — ikisini de madde listesine çeviriyoruz.
  const normalized = text.replace(/\s\*\s(?=\*\*)/g, '\n* ');
  const lines = normalized.split('\n').filter((l) => l.trim().length > 0);

  const isList = lines.length > 1 && lines.every((l) => l.trim().startsWith('* '));

  if (isList) {
    return (
      <ul className="bubble-list">
        {lines.map((line, idx) => (
          <li key={idx}>{renderInline(line.trim().slice(2), `li-${idx}`)}</li>
        ))}
      </ul>
    );
  }

  return (
    <>
      {lines.map((line, idx) => (
        <p key={idx} className="bubble-line">
          {renderInline(line, `p-${idx}`)}
        </p>
      ))}
    </>
  );
}

const GROUP_META = {
  flight: { label: '✈ Uçuş Seçenekleri', className: 'group-flight' },
  hotel: { label: '🏨 Otel Seçenekleri', className: 'group-hotel' },
  place: { label: '📍 Gezilecek Yerler', className: 'group-place' },
};
const GROUP_ORDER = ['flight', 'hotel', 'place'];

function ResultCard({ item }) {
  const isPlace = item.type === 'place';
  return (
    <div className={`result-card result-card-${item.type || 'default'}`}>
      <div className="result-top">
        {item.badge && <span className="result-badge">{item.badge}</span>}
        {item.rating != null && (
          <span className="result-rating">⭐ {item.rating}</span>
        )}
      </div>
      <div className="result-name">{item.name}</div>

      {/* Havalimanı + saat bilgisi (sadece uçuş kartlarında dolu gelir) */}
      {(item.originAirport || item.destinationAirport) && (
        <div className="result-route">
          <span className="route-airport">{item.originAirport}</span>
          <span className="route-arrow">→</span>
          <span className="route-airport">{item.destinationAirport}</span>
        </div>
      )}
      {(item.departureTime || item.arrivalTime) && (
        <div className="result-times">
          <span>{item.departureTime}</span>
          <span className="route-arrow">→</span>
          <span>{item.arrivalTime}</span>
          {item.durationMinutes != null && (
            <span className="result-duration">· {item.durationMinutes} dk</span>
          )}
        </div>
      )}

      {/* Yer kartlarında fiyat yerine açık olduğu saatler gösterilir */}
      {isPlace ? (
        item.hours && (
          <div className="result-hours-row">
            <span className="hours-label">Açık:</span>
            <span className="result-hours">{item.hours}</span>
          </div>
        )
      ) : (
        item.price && (
          <div className="result-price-row">
            <span className="price-label">Fiyat:</span>
            <span className="result-price">{item.price}</span>
          </div>
        )
      )}
    </div>
  );
}

function ResultGroups({ results }) {
  const grouped = {};
  for (const item of results) {
    const key = item.type && GROUP_META[item.type] ? item.type : 'place';
    (grouped[key] = grouped[key] || []).push(item);
  }
  const activeGroups = GROUP_ORDER.filter((k) => grouped[k]?.length);
  const multiGroup = activeGroups.length > 1;

  return (
    <div className="result-groups">
      {activeGroups.map((key) => (
        <div key={key} className={`result-group ${GROUP_META[key].className}`}>
          {multiGroup && <div className="result-group-label">{GROUP_META[key].label}</div>}
          <div className="results-grid">
            {grouped[key].map((item, idx) => (
              <ResultCard key={idx} item={item} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ChatView() {
  const { messages, sendMessage, isThinking } = useAgentState();
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    sendMessage(inputText);
    setInputText('');
  };

  const handleQuickPrompt = (prompt) => {
    sendMessage(prompt);
  };

  return (
    <div className="chat-container">
      <QuickPrompts onSelect={handleQuickPrompt} />

      {/* Mesaj Akışı */}
      <div className="messages-stream">
        {messages.map((msg) => (
          <div key={msg.id} className={"message-row " + msg.sender}>
            <div className="avatar">
              {msg.sender === 'agent' ? '🤖' : '👤'}
            </div>
            <div className="message-content">
              <div className="message-header">
                <span className="sender-name">
                  {msg.sender === 'agent' ? (msg.agentName || 'WayPoint Agent') : 'Siz'}
                </span>
                <span className="message-time">{msg.timestamp}</span>
              </div>

              <div className="bubble-text">
                {msg.sender === 'agent' ? (
                  <FormattedMessage text={msg.text} />
                ) : (
                  msg.text
                )}
              </div>

              {/* Tool Çağrı Rozeti */}
              {msg.toolCall && (
                <div className="tool-call-badge">
                  <span className="badge-icon">⚙️</span>
                  <span>Çalıştırılan Araç: <code>{msg.toolCall}</code></span>
                </div>
              )}

              {/* Ajan Sonuç Kartları — tipe göre gruplanır (uçuş/otel/yer paket
                  isteklerinde birbirine karışmasın diye) */}
              {msg.results && msg.results.length > 0 && (
                <ResultGroups results={msg.results} />
              )}
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="message-row agent">
            <div className="avatar">🤖</div>
            <div className="message-content">
              <div className="thinking-bubble">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="thinking-label">Asistan yanıtınızı hazırlıyor</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Mesaj Gönderme Kutusu */}
      <form onSubmit={handleSubmit} className="chat-input-bar">
        <input
          type="text"
          className="chat-input"
          placeholder="Seyahat planınızı yazın (Örn: 'Ankara'dan İzmir'e uçak bileti arayalım')..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />
        <button type="submit" className="chat-send-button">
          Gönder ✈
        </button>
      </form>
    </div>
  );
}
