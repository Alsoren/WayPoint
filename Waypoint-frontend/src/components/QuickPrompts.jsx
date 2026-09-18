import React from 'react';
import './QuickPrompts.css';

// Asistanın gerçekte yaptığı üç farklı işi (uçuş, otel+gezi planı, hava
// durumuna duyarlı rota önerisi) temsil eden, tek bir şehre kilitlenmemiş
// örnek istekler.
const PROMPTS = [
  { icon: '✈', text: 'İstanbul - Roma arası uygun uçuşları bul' },
  { icon: '🏨', text: "Kapadokya'da 3 günlük butik otel ve gezi planı yap" },
  { icon: '🌤', text: 'Bu hafta sonu İzmir için hava durumuna uygun rota öner' },
];

export default function QuickPrompts({ onSelect }) {
  return (
    <div className="quick-prompts-bar">
      {PROMPTS.map((p) => (
        <button
          key={p.text}
          className="quick-chip"
          onClick={() => onSelect(p.text)}
        >
          <span className="quick-chip-icon">{p.icon}</span>
          {p.text}
        </button>
      ))}
    </div>
  );
}
