import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, AreaSeries } from 'lightweight-charts';
import axios from 'axios';
import { Search, TrendingUp, AlertTriangle, Minus, RefreshCcw, LayoutDashboard } from 'lucide-react';

function App() {
  const chartContainerRef = useRef();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // PERSISTENCE: Initialize state from localStorage or default to AAPL
  const [ticker, setTicker] = useState(() => {
    return localStorage.getItem('selectedTicker') || 'AAPL';
  });

  const [searchInput, setSearchInput] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Updated List: Using .NSE for Alpha Vantage compatibility where applicable
  const tickerList = [
    { symbol: "AAPL", name: "Apple Inc" },
    { symbol: "TSLA", name: "Tesla Inc" },
    { symbol: "NVDA", name: "NVIDIA Corp" },
    { symbol: "RELIANCE.NSE", name: "Reliance Industries" },
    { symbol: "INFY.NSE", name: "Infosys Ltd" },
    { symbol: "BTC", name: "Bitcoin" },
    { symbol: "ETH", name: "Ethereum" }
  ];

  const filteredTickers = tickerList.filter(t => 
    t.symbol.toLowerCase().includes(searchInput.toLowerCase()) || 
    t.name.toLowerCase().includes(searchInput.toLowerCase())
  );

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`https://regimevision-backend1.onrender.com/api/regimes/${ticker}`);
      
      if (res.data.error) {
        console.error("Backend Error:", res.data.error);
        setData([]);
      } else {
        // MAP DATA: Convert Backend keys (Date, Close) to Chart keys (time, value)
        const formattedData = res.data.map(item => ({
          time: item.Date,      // From main.py 'Date'
          value: item.Close,    // From main.py 'Close'
          regime: item.Regime   // From main.py 'Regime'
        }));
        setData(formattedData);
        localStorage.setItem('selectedTicker', ticker);
      }
    } catch (err) {
      console.error("Network Error:", err);
    } finally {
      setLoading(false);
    }
  };

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

    // Switched to AreaSeries to handle the single-price data points
    const mainSeries = chart.addSeries(AreaSeries, {
      lineColor: '#38bdf8',
      topColor: 'rgba(56, 189, 248, 0.3)',
      bottomColor: 'rgba(56, 189, 248, 0.0)',
      lineWidth: 2,
    });

    mainSeries.setData(data);

    // Apply GMM Markers using the stabilized 'Regime' key
    try {
      const markers = data.map(item => {
        if (item.regime === 1) return { time: item.time, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'BEAR' };
        if (item.regime === 2) return { time: item.time, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'BULL' };
        return null;
      }).filter(Boolean);
      mainSeries.setMarkers(markers);
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
             <div style={{ backgroundColor: '#0f172a', padding: '8px', borderRadius: '8px', border: '1px solid #1e293b' }}>
               <LayoutDashboard color="#38bdf8" size={24} />
             </div>
             <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 'bold' }}>Regime<span style={{ color: '#38bdf8' }}>Vision</span></h1>
        </div>

        {/* Search Input */}
        <div style={{ position: 'relative', flex: '1 1 300px', maxWidth: '400px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: '#64748b', zIndex: 10 }} />
            <input 
              type="text" 
              placeholder="Search (e.g. AAPL, RELIANCE.NSE)..." 
              value={searchInput}
              onFocus={() => setIsDropdownOpen(true)}
              // Added delay to let the click on the dropdown item fire first
              onBlur={() => setTimeout(() => setIsDropdownOpen(false), 200)}
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
                backgroundColor: '#0f172a', color: 'white', width: '100%', outline: 'none'
              }}
            />
          </div>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div style={{ position: 'absolute', top: '55px', left: 0, right: 0, backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', zIndex: 100, maxHeight: '250px', overflowY: 'auto' }}>
              {filteredTickers.map((t) => (
                <div key={t.symbol} 
                  // Use onMouseDown to trigger before the input loses focus
                  onMouseDown={(e) => {
                    setTicker(t.symbol);
                    setSearchInput('');
                    setIsDropdownOpen(false);
                  }}
                  style={{ padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid #1e293b' }}>
                  <div style={{ fontWeight: 'bold' }}>{t.symbol}</div>
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
            <span style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '11px', fontWeight: 'bold' }}>Ticker: {ticker}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginTop: '10px' }}>
              <div style={{ color: status.color, backgroundColor: `${status.color}15`, padding: '8px', borderRadius: '8px' }}>{status.icon}</div>
              <h2 style={{ margin: 0, fontSize: '32px', color: status.color, fontWeight: '800' }}>{status.label}</h2>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '24px', fontWeight: '800' }}>{lastPoint ? lastPoint.value.toLocaleString() : '0.00'}</div>
            <div style={{ fontSize: '12px', color: '#475569' }}>{lastPoint?.time}</div>
          </div>
        </div>
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '16px', padding: '24px', display: 'flex', alignItems: 'center', fontSize: '13px', color: '#94a3b8' }}>
          <p>GMM Analysis: High-volatility clusters detected. The <strong>Gaussian Mixture Model</strong> suggests a primary <strong>{status.label.toLowerCase()}</strong> regime based on recent price action.</p>
        </div>
      </div>

      {/* Chart Section */}
      <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '20px', padding: '15px' }}>
        {loading ? (
          <div style={{ height: '450px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '15px' }}>
            <RefreshCcw className="animate-spin" color="#38bdf8" size={32} />
            <p style={{ color: '#64748b' }}>Running Go Ingestor...</p>
          </div>
        ) : data.length === 0 ? (
          <div style={{ height: '450px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
            No data. Please check ticker format or API limits.
          </div>
        ) : (
          <div ref={chartContainerRef} style={{ borderRadius: '10px', overflow: 'hidden' }} />
        )}
      </div>
    </div>
  );
}

export default App;