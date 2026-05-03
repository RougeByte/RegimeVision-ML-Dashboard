import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts';
import axios from 'axios';
import { Search, TrendingUp, AlertTriangle, Minus, RefreshCcw, LayoutDashboard } from 'lucide-react';

function App() {
  const chartContainerRef = useRef();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // PERSISTENCE: Initialize state from localStorage or default to ^NSEI
  const [ticker, setTicker] = useState(() => {
    return localStorage.getItem('selectedTicker') || '^NSEI';
  });

  const [searchInput, setSearchInput] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const tickerList = [
    { symbol: "^NSEI", name: "Nifty 50 Index" },
    { symbol: "RELIANCE.NS", name: "Reliance Industries" },
    { symbol: "HDFCBANK.NS", name: "HDFC Bank" },
    { symbol: "INFY.NS", name: "Infosys Ltd" },
    { symbol: "BTC-USD", name: "Bitcoin" },
    { symbol: "ETH-USD", name: "Ethereum" },
    { symbol: "^GSPC", name: "S&P 500 Index" },
    { symbol: "NVDA", name: "NVIDIA Corp" },
    { symbol: "AAPL", name: "Apple Inc" },
    { symbol: "TSLA", name: "Tesla Inc" },
    { symbol: "USDINR=X", name: "USD to INR" }
  ];

  const filteredTickers = tickerList.filter(t => 
    t.symbol.toLowerCase().includes(searchInput.toLowerCase()) || 
    t.name.toLowerCase().includes(searchInput.toLowerCase())
  );

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`http://localhost:8000/api/regimes/${ticker}`);
      setData(res.data);
      // PERSISTENCE: Save to localStorage on successful fetch
      localStorage.setItem('selectedTicker', ticker);
    } catch (err) {
      console.error("Backend Error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Re-fetch when ticker changes
  useEffect(() => { 
    fetchData(); 
  }, [ticker]);

  // Chart Logic
  useEffect(() => {
    if (loading || !data.length || !chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#020617' }, textColor: '#94a3b8' },
      width: chartContainerRef.current.clientWidth,
      height: 450,
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
    });

    const mainSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981', downColor: '#ef4444', borderVisible: false,
      wickUpColor: '#10b981', wickDownColor: '#ef4444',
    });

    mainSeries.setData(data);

    try {
      const markers = data.map(item => {
        if (item.regime === 1) return { time: item.time, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'BEAR' };
        if (item.regime === 2) return { time: item.time, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'BULL' };
        return null;
      }).filter(Boolean);
      if (mainSeries.setMarkers) mainSeries.setMarkers(markers);
    } catch (e) {}

    chart.timeScale().fitContent();
    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [loading, data]);

  const lastPoint = data[data.length - 1];
  const getStatus = () => {
    if (!lastPoint) return { label: 'Unknown', color: '#94a3b8', icon: <Minus /> };
    if (lastPoint.regime === 2) return { label: 'BULLISH', color: '#10b981', icon: <TrendingUp /> };
    if (lastPoint.regime === 1) return { label: 'BEARISH', color: '#ef4444', icon: <AlertTriangle /> };
    return { label: 'SIDEWAYS', color: '#94a3b8', icon: <Minus /> };
  };
  const status = getStatus();

  return (
    <div style={{ padding: '20px 5%', backgroundColor: '#020617', minHeight: '100vh', color: 'white', fontFamily: 'Inter, sans-serif', boxSizing: 'border-box' }}>
      
      {/* Navbar Area */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
             <div style={{ backgroundColor: '#0f172a', padding: '8px', borderRadius: '8px', border: '1px solid #1e293b' }}>
               <LayoutDashboard color="#38bdf8" size={24} />
             </div>
             <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 'bold' }}>Regime<span style={{ color: '#38bdf8' }}>Vision</span></h1>
        </div>

        {/* Search Input Container */}
        <div style={{ position: 'relative', flex: '1 1 300px', maxWidth: '400px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: '#64748b', zIndex: 10 }} />
            <input 
              type="text" 
              placeholder="Search Ticker..." 
              value={searchInput}
              onFocus={() => setIsDropdownOpen(true)}
              onBlur={() => setIsDropdownOpen(false)}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchInput) {
                  setTicker(searchInput.toUpperCase());
                  setSearchInput('');
                  setIsDropdownOpen(false);
                }
              }}
              style={{ 
                padding: '12px 12px 12px 40px', borderRadius: '10px', border: '1px solid #1e293b', 
                backgroundColor: '#0f172a', color: 'white', width: '100%', 
                outline: 'none', fontSize: '14px', boxSizing: 'border-box' 
              }}
            />
          </div>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div style={{ position: 'absolute', top: '55px', left: 0, right: 0, backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', zIndex: 100, maxHeight: '300px', overflowY: 'auto', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)' }}>
              {filteredTickers.map((t) => (
                <div key={t.symbol} onMouseDown={(e) => { e.preventDefault(); setTicker(t.symbol); setSearchInput(''); setIsDropdownOpen(false); }}
                  style={{ padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid #1e293b' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#1e293b'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}>
                  <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{t.symbol}</div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>{t.name}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Analysis Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '20px' }}>
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '16px', padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '11px', fontWeight: 'bold' }}>Status: {ticker}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginTop: '10px' }}>
              <div style={{ color: status.color, backgroundColor: `${status.color}15`, padding: '8px', borderRadius: '8px' }}>{status.icon}</div>
              <h2 style={{ margin: 0, fontSize: '32px', color: status.color, fontWeight: '800' }}>{status.label}</h2>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '24px', fontWeight: '800' }}>{lastPoint ? lastPoint.close.toLocaleString() : '0.00'}</div>
            <div style={{ fontSize: '12px', color: '#475569' }}>{lastPoint?.time}</div>
          </div>
        </div>
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '16px', padding: '24px', display: 'flex', alignItems: 'center', fontSize: '13px', color: '#94a3b8' }}>
          <p>Machine Learning Insight: Our <strong>GMM clustering</strong> indicates that volatility is currently trending in a <strong>{status.label.toLowerCase()}</strong> direction for {ticker}.</p>
        </div>
      </div>

      {/* Chart Section */}
      <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '20px', padding: '15px' }}>
        {loading ? (
          <div style={{ height: '450px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '15px' }}>
            <RefreshCcw className="animate-spin" color="#38bdf8" size={32} />
            <p style={{ color: '#64748b', fontSize: '14px' }}>Fetching from Go Ingestor...</p>
          </div>
        ) : (
          <div ref={chartContainerRef} style={{ borderRadius: '10px', overflow: 'hidden' }} />
        )}
      </div>
      
      <footer style={{ marginTop: '20px', textAlign: 'center', color: '#1e293b', fontSize: '11px' }}>
        LocalStorage Persistence Active • {ticker} Saved
      </footer>
    </div>
  );
}

export default App;