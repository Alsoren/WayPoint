import React from 'react';
import './Header.css';

export default function Header() {
  return (
    <header className="header-container">
      <div className="top-bar">
        <div className="brand-section">
          <div className="logo">
            <span className="logo-text">WayPoint</span>
            <span className="logo-plane">✈</span>
          </div>
          <span className="logo-subtitle">Seyahat asistanı</span>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          <span>Sistem hazır</span>
        </div>
      </div>
    </header>
  );
}
