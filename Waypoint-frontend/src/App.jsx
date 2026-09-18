import React from 'react';
import { AgentStateProvider } from './context/AgentStateContext';
import Header from './components/Header';
import ChatView from './components/ChatView';
import TravelContextSidebar from './components/TravelContextSidebar';
import Footer from './components/Footer';
import './App.css';

export default function App() {
  return (
    <AgentStateProvider>
      <div className="agent-app-container">
        <Header />
        
        <main className="agent-main-layout">
          {/* Sol/Orta Alan: Chat Ajanı Konuşma Arayüzü */}
          <div className="chat-area">
            <ChatView />
          </div>

          {/* Sağ Alan: Kullanıcıdan Alınan ve Agent State'inde Tutulan Parametreler */}
          <div className="sidebar-area">
            <TravelContextSidebar />
          </div>
        </main>

        <Footer />
      </div>
    </AgentStateProvider>
  );
}
