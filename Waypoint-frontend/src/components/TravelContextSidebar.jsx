import React from 'react';
import { useAgentState, QUERY_TYPES } from '../context/AgentStateContext';
import './TravelContextSidebar.css';

// Boş, null veya undefined değerleri eleyen güvenli kontrol
function hasValue(v) {
  if (v === undefined || v === null || v === '') return false;
  if (typeof v === 'object' && !Array.isArray(v)) {
    return Object.values(v).some((val) => val !== undefined && val !== null && val !== '');
  }
  return true;
}

// Bilinen 17 alanın kümesi
const KNOWN_KEYS = new Set([
  'origin',
  'destination',
  'preferred_origin_airport',
  'preferred_destination_airport',
  'departure_date',
  'return_date',
  'preferred_departure_period',
  'preferred_return_period',
  'check_in_date',
  'check_out_date',
  'preferred_hotel_area',
  'min_star_rating',
  'travelers',
  'total_budget',
  'currency',
  'travel_theme',
  'travel_pace'
]);

// snake_case anahtarları okunabilir başlığa çevirir (örn: car_rental -> Car Rental)
function formatKeyLabel(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// Bilinmeyen alan değerlerini (boolean, array, object) okunabilir metne dönüştürür
function formatDynamicValue(val) {
  if (typeof val === 'boolean') return val ? 'Evet' : 'Hayır';
  if (Array.isArray(val)) return val.join(', ');
  if (typeof val === 'object' && val !== null) return JSON.stringify(val);
  return String(val);
}

// Yolcu sayısını formatlar
function formatTravelers(travelers) {
  if (typeof travelers === 'number') return `${travelers} Yetişkin`;
  if (typeof travelers === 'object' && travelers !== null) {
    const parts = [];
    if (travelers.adults) parts.push(`${travelers.adults} Yetişkin`);
    if (travelers.children) parts.push(`${travelers.children} Çocuk`);
    if (travelers.rooms) parts.push(`${travelers.rooms} Oda`);
    return parts.length > 0 ? parts.join(', ') : `${travelers.adults || 1} Yetişkin`;
  }
  return String(travelers);
}

export default function TravelContextSidebar() {
  const { activeIntent, activeAgentState, lastExecutedTool } = useAgentState();
  const s = activeAgentState || {};

  // 1. Güzergah & Havalimanları
  const showRoute =
    hasValue(s.origin) ||
    hasValue(s.destination) ||
    hasValue(s.preferred_origin_airport) ||
    hasValue(s.preferred_destination_airport);

  // 2. Uçuş Tarihleri & Saat Tercihleri
  const showFlightDates =
    hasValue(s.departure_date) ||
    hasValue(s.return_date) ||
    hasValue(s.preferred_departure_period) ||
    hasValue(s.preferred_return_period);

  // 3. Konaklama & Otel Tercihleri
  const showHotel =
    hasValue(s.check_in_date) ||
    hasValue(s.check_out_date) ||
    hasValue(s.preferred_hotel_area) ||
    hasValue(s.min_star_rating);

  // 4. Yolcu & Bütçe
  const showTravelers = hasValue(s.travelers);
  const showBudget = hasValue(s.total_budget);

  // 5. Seyahat Tarzı & Temposu
  const showStyle =
    hasValue(s.travel_theme) ||
    hasValue(s.travel_pace);

  // 6. Bilinen 17 alan DIŞINDA backend'den gelen tüm ekstra dinamik alanlar
  const extraKeys = Object.keys(s).filter(
    (key) => !KNOWN_KEYS.has(key) && hasValue(s[key])
  );

  const hasAnyData =
    showRoute ||
    showFlightDates ||
    showHotel ||
    showTravelers ||
    showBudget ||
    showStyle ||
    extraKeys.length > 0;

  return (
    <aside className="context-sidebar">
      {/* Sidebar Başlığı */}
      <div className="sidebar-header">
        <div className="sidebar-title-row">
          <span className="live-indicator"></span>
          <h2 className="sidebar-title">Seyahat özeti</h2>
        </div>
        {hasAnyData && (
          <span className="intent-badge">
            {activeIntent === QUERY_TYPES.FLIGHT && '✈ Uçuş'}
            {activeIntent === QUERY_TYPES.HOTEL && '🏨 Otel'}
            {activeIntent === QUERY_TYPES.FLIGHT_HOTEL && '✈🏨 Paket'}
            {activeIntent === QUERY_TYPES.SIGHTSEEING && '🗺 Gezi'}
          </span>
        )}
      </div>

      {/* Boş Durum: minimal ikon + tek satır bilgi, veri gelince kaybolur */}
      {!hasAnyData && (
        <div className="empty-state-card">
          <span className="empty-state-icon">🧭</span>
          <p className="empty-state-caption">
            Planınız oluştukça detaylar, uçuş ve otel kartları burada listelenecek.
          </p>
        </div>
      )}

      <div className={"state-cards-container" + (hasAnyData ? "" : " is-empty")}>
        
        {/* 1. Güzergah & Havalimanları */}
        {showRoute && (
          <div className="state-card">
            <div className="state-card-header">
              <span>📍 Güzergah &amp; Havalimanları</span>
            </div>
            <div className="state-card-body">
              {hasValue(s.origin) && (
                <div className="param-row">
                  <span className="param-key">Nereden:</span>
                  <span className="param-val">{s.origin}</span>
                </div>
              )}
              {hasValue(s.preferred_origin_airport) && (
                <div className="param-row">
                  <span className="param-key">Kalkış Havalimanı:</span>
                  <span className="param-val highlight">{s.preferred_origin_airport}</span>
                </div>
              )}
              {hasValue(s.destination) && (
                <div className="param-row">
                  <span className="param-key">Nereye:</span>
                  <span className="param-val">{s.destination}</span>
                </div>
              )}
              {hasValue(s.preferred_destination_airport) && (
                <div className="param-row">
                  <span className="param-key">Varış Havalimanı:</span>
                  <span className="param-val highlight">{s.preferred_destination_airport}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 2. Uçuş & Tarih Planı */}
        {showFlightDates && (
          <div className="state-card">
            <div className="state-card-header">
              <span>✈️ Uçuş &amp; Tarih Planı</span>
            </div>
            <div className="state-card-body">
              {hasValue(s.departure_date) && (
                <div className="param-row">
                  <span className="param-key">Gidiş Tarihi:</span>
                  <span className="param-val">{s.departure_date}</span>
                </div>
              )}
              {hasValue(s.preferred_departure_period) && (
                <div className="param-row">
                  <span className="param-key">Gidiş Zamanı:</span>
                  <span className="param-val">{s.preferred_departure_period}</span>
                </div>
              )}
              {hasValue(s.return_date) && (
                <div className="param-row">
                  <span className="param-key">Dönüş Tarihi:</span>
                  <span className="param-val">{s.return_date}</span>
                </div>
              )}
              {hasValue(s.preferred_return_period) && (
                <div className="param-row">
                  <span className="param-key">Dönüş Zamanı:</span>
                  <span className="param-val">{s.preferred_return_period}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 3. Konaklama & Otel Detayları */}
        {showHotel && (
          <div className="state-card">
            <div className="state-card-header">
              <span>🏨 Konaklama Detayları</span>
            </div>
            <div className="state-card-body">
              {hasValue(s.check_in_date) && (
                <div className="param-row">
                  <span className="param-key">Giriş:</span>
                  <span className="param-val hotel-highlight">{s.check_in_date}</span>
                </div>
              )}
              {hasValue(s.check_out_date) && (
                <div className="param-row">
                  <span className="param-key">Çıkış:</span>
                  <span className="param-val hotel-highlight">{s.check_out_date}</span>
                </div>
              )}
              {hasValue(s.preferred_hotel_area) && (
                <div className="param-row">
                  <span className="param-key">Otel Bölgesi:</span>
                  <span className="param-val">{s.preferred_hotel_area}</span>
                </div>
              )}
              {hasValue(s.min_star_rating) && (
                <div className="param-row">
                  <span className="param-key">Min. Yıldız:</span>
                  <span className="param-val">⭐ {s.min_star_rating} Yıldız ve Üzeri</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 4. Yolcular & Bütçe */}
        {(showTravelers || showBudget) && (
          <div className="state-card">
            <div className="state-card-header">
              <span>👥 Yolcular &amp; Bütçe</span>
            </div>
            <div className="state-card-body">
              {showTravelers && (
                <div className="param-row">
                  <span className="param-key">Kişi Sayısı:</span>
                  <span className="param-val">{formatTravelers(s.travelers)}</span>
                </div>
              )}
              {showBudget && (
                <div className="param-row">
                  <span className="param-key">Toplam Bütçe:</span>
                  <span className="param-val highlight">
                    {s.total_budget} {s.currency || 'TL'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 5. Seyahat Tarzı */}
        {showStyle && (
          <div className="state-card">
            <div className="state-card-header">
              <span>🎯 Seyahat Tarzı</span>
            </div>
            <div className="state-card-body">
              {hasValue(s.travel_theme) && (
                <div className="param-row">
                  <span className="param-key">Tema:</span>
                  <span className="param-val">{s.travel_theme}</span>
                </div>
              )}
              {hasValue(s.travel_pace) && (
                <div className="param-row">
                  <span className="param-key">Tempo:</span>
                  <span className="param-val">{s.travel_pace}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 6. Dinamik Olarak Gelen Tüm Ekstra Alanlar */}
        {extraKeys.length > 0 && (
          <div className="state-card">
            <div className="state-card-header">
              <span>🧩 Ek Bilgiler &amp; Tercihler</span>
            </div>
            <div className="state-card-body">
              {extraKeys.map((key) => (
                <div key={key} className="param-row">
                  <span className="param-key">{formatKeyLabel(key)}:</span>
                  <span className="param-val">{formatDynamicValue(s[key])}</span>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Arka Planda Çağrılan Araç */}
      {lastExecutedTool && (
        <div className="tool-execution-box">
          <span className="tool-title">⚡ Arka Planda Çağrılan Araç:</span>
          <code>{lastExecutedTool}</code>
        </div>
      )}
    </aside>
  );
}