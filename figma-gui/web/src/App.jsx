import React, { useEffect, useState } from 'react';
import {
  Activity, ArrowUpRight, Battery, Check, ChevronRight, Database,
  Gauge, History, LockKeyhole, LogOut, Radio, Settings2, ShieldCheck,
  Thermometer, Wrench, Zap, Play, Pause, RefreshCw, Download, AlertTriangle, Palette, Cpu,
  Trash2, User, UserCheck
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area, CartesianGrid,
  XAxis, YAxis, Tooltip, ReferenceLine, Legend
} from 'recharts';

const PALETTES = {
  mint: {
    name: 'CYBER_MINT',
    display: 'Cyber-Mint',
    primary: '#00F5A0',
    highlight: '#5CFFC7',
    secondary: '#00E5FF',
    dim: 'rgba(0, 245, 160, 0.15)',
    contrast: '14.2:1 (OLED AAA)',
    compliance: 'PASS • ISO/SAE Invariant',
    vibe: 'Voltesse signature cybernetic electric neon',
  },
  stealth: {
    name: 'STEALTH_MONOCHROME',
    display: 'Stealth Monochrome',
    primary: '#E2E8F0',
    highlight: '#FFFFFF',
    secondary: '#94A3B8',
    dim: 'rgba(226, 232, 240, 0.15)',
    contrast: '15.8:1 (OLED AAA)',
    compliance: 'PASS • ISO/SAE Invariant',
    vibe: 'Pure hypercar titanium silver & white',
  },
  amber: {
    name: 'SOLAR_AMBER',
    display: 'Solar Amber',
    primary: '#FFB800',
    highlight: '#FFD166',
    secondary: '#FF9F1C',
    dim: 'rgba(255, 184, 0, 0.15)',
    contrast: '11.6:1 (OLED AAA)',
    compliance: 'PASS • ISO/SAE Invariant',
    vibe: 'Endurance motorsport amber tachometer',
  },
  redline: {
    name: 'TRACK_REDLINE',
    display: 'Track Redline',
    primary: '#FF3366',
    highlight: '#FF6B8B',
    secondary: '#FF9900',
    dim: 'rgba(255, 51, 102, 0.15)',
    contrast: '7.9:1 (OLED AA)',
    compliance: 'PASS • ISO/SAE Invariant',
    vibe: 'Aggressive track attack crimson',
  },
  synthwave: {
    name: 'NEON_SYNTHWAVE',
    display: 'Neon Synthwave',
    primary: '#D946EF',
    highlight: '#F472B6',
    secondary: '#06B6D4',
    dim: 'rgba(217, 70, 239, 0.15)',
    contrast: '9.4:1 (OLED AAA)',
    compliance: 'PASS • ISO/SAE Invariant',
    vibe: 'Cyberpunk night drive magenta & cyan',
  },
};

async function request(path, options = {}, csrf) {
  let response;
  try {
    response = await fetch('/api' + path, {
      ...options,
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'VoltesseGUI',
        ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
        ...options.headers
      }
    });
  } catch {
    throw new Error('Cannot reach the backend. Check that the API is running.');
  }
  let result;
  try {
    result = await response.json();
  } catch {
    throw new Error('The API did not return JSON. Check backend and Vite proxy configuration.');
  }
  if (!response.ok) {
    const err = new Error(typeof result.detail === 'string' ? result.detail : 'Please check your input.');
    err.status = response.status;
    throw err;
  }
  return result;
}

function useResource(key, load, interval = 0) {
  const [state, setState] = useState({});
  useEffect(() => {
    let active = true, timer;
    async function refresh() {
      try {
        const data = await load();
        if (active) setState({ key, data });
      } catch (error) {
        if (active) setState({ key, error });
      }
      if (active && interval) timer = setTimeout(refresh, interval);
    }
    refresh();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [key, interval]);
  return state.key === key ? state : {};
}

function Brand() {
  return (
    <div className="brand">
      <div className="brand-symbol"><Zap size={22} fill="currentColor" /></div>
      <div>VOLTESSE<span>DASH / TECHNICIAN</span></div>
    </div>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('Tab render error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="notice danger" style={{ marginTop: 20 }}>
          <AlertTriangle size={18} />
          <div>
            <strong>Encountered an error displaying this view.</strong>
            <p style={{ marginTop: 4, fontSize: 12, color: '#FFA3B4' }}>{this.state.error?.message || 'Unknown view error'}</p>
            <button className="text-button" style={{ marginTop: 8 }} onClick={() => this.setState({ hasError: false })}>
              Try reload view
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function ErrorBox({ error }) {
  return (
    <div role="alert" className="notice danger">
      <AlertTriangle size={17} />{error.message || error}
    </div>
  );
}

function Loading() {
  return <div className="empty"><RefreshCw size={20} className="spin" /> Loading data…</div>;
}

function fmt(value, digits = 1) {
  return value == null ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function date(value) {
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' });
}

function duration(seconds) {
  return `${Math.floor(Number(seconds) / 60)}:${String(Math.floor(Number(seconds) % 60)).padStart(2, '0')}`;
}

const CustomTooltip = ({ active, payload, label, unit = '' }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'rgba(8, 12, 14, 0.95)',
        border: '1px solid rgba(0, 245, 212, 0.4)',
        padding: '8px 12px',
        borderRadius: 6,
        fontSize: 11,
        fontFamily: 'Consolas, monospace',
        color: '#E2E8F0',
        boxShadow: '0 4px 14px rgba(0,0,0,0.6)'
      }}>
        <div style={{ color: '#94A3B8', marginBottom: 4 }}>T = {label}s</div>
        {payload.map((entry, index) => (
          <div key={`item-${index}`} style={{ color: entry.color || entry.stroke, display: 'flex', gap: 8, justifyContent: 'space-between' }}>
            <span>{entry.name}:</span>
            <strong>{fmt(entry.value, 1)} {unit}</strong>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

function Plot({ title, subtitle, data, color = 'var(--v-primary)', limit, height = 215, unit = '' }) {
  return (
    <section className="panel plot">
      <div className="panel-heading">
        <div><h3>{title}</h3><p>{subtitle}</p></div>
        <Activity size={17} />
      </div>
      {!data?.length ? (
        <div className="empty">No readings available for this chart.</div>
      ) : (
        <div style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 12, right: 20, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="rgba(255, 255, 255, 0.08)" />
              <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={v => fmt(v, 1)} tickLine={false} axisLine={false} />
              <YAxis domain={limit != null ? [0, max => Math.max(max + 5, limit + 5)] : ['auto', 'auto']} tick={{ fontSize: 10, fill: '#94A3B8' }} tickLine={false} axisLine={false} width={45} />
              <Tooltip content={<CustomTooltip unit={unit} />} />
              {limit != null && (
                <ReferenceLine y={limit} stroke="#FF4D6D" strokeDasharray="5 4" label={{ value: `Limit (${limit})`, position: 'insideTopRight', fontSize: 10, fill: '#FF4D6D' }} />
              )}
              <Line name={title} type="monotone" dataKey="y" stroke={color} strokeWidth={2.2} dot={data.length < 25 ? { r: 2 } : false} isAnimationActive={false} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

function Login({ onLogin, initialError }) {
  const [username, setUsername] = useState(''), [password, setPassword] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState(initialError);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      setPassword('');
      onLogin(user);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-layout">
      <section className="login-story">
        <Brand />
        <div className="story-main">
          <span className="eyebrow">VOLTESSE FORMULA ELECTRIC</span>
          <h1>Every reading.<br />A clearer picture.</h1>
          <p>Your workspace for vehicle telemetry, performance analysis, and trackside diagnostics.</p>
          <div className="story-grid">
            <div><Activity />LIVE TELEMETRY</div>
            <div><History />SESSION ANALYSIS</div>
            <div><ShieldCheck />PROTECTED ACCESS</div>
          </div>
        </div>
        <p className="story-footer">ENGINEERED FOR THE TEAM. BUILT FOR THE NEXT LAP.</p>
      </section>
      <main className="login-main">
        <div className="login-card">
          <div className="login-icon"><LockKeyhole size={24} /></div>
          <span className="eyebrow">TECHNICIAN / ADMIN</span>
          <h2>Welcome to the garage.</h2>
          <p>Sign in with your team account to access Voltesse Dash.</p>
          <form onSubmit={submit}>
            <label htmlFor="username">Username or email</label>
            <input id="username" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required maxLength={254} placeholder="Your team username" />
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required maxLength={1024} placeholder="Enter your password" />
            {error && <ErrorBox error={error} />}
            <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<ArrowUpRight size={18} /></button>
          </form>
          <div className="login-foot"><ShieldCheck size={16} /> Authorized team members only</div>
          <p className="provision-note">Need an account? Ask your project administrator to provision one.</p>
        </div>
      </main>
    </div>
  );
}

const PAGES = [
  ['Live', 'Live telemetry', Activity],
  ['Diagnostics', 'Diagnostics', Wrench],
  ['Sessions', 'Sessions', History],
  ['Settings', 'Settings', Settings2],
  ['Backups', 'Backups', Database]
];

function Live({ api, prefs }) {
  const [t, setT] = useState(30), [playing, setPlaying] = useState(false);
  const [wsData, setWsData] = useState(null);
  const [wsActive, setWsActive] = useState(false);
  const [cmdBusy, setCmdBusy] = useState(false);
  const [cmdStatus, setCmdStatus] = useState(null);
  const [driverInputLive, setDriverInputLive] = useState('');
  const { data: pollData, error: pollError } = useResource('live:' + t, () => api('/live?t=' + t), wsActive ? 0 : 1000);

  async function sendCmd(cmd) {
    setCmdBusy(true);
    try {
      const res = await api('/vehicle/command', {
        method: 'POST',
        body: JSON.stringify(cmd)
      });
      setCmdStatus(res.command);
      setTimeout(() => setCmdStatus(null), 3500);
    } catch (err) {
      console.error('Vehicle command failed:', err);
    } finally {
      setCmdBusy(false);
    }
  }

  useEffect(() => {
    let ws;
    let timer;
    let deadCheck;
    function connect() {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${proto}//${location.host}/api/ws/telemetry`;
      ws = new WebSocket(url);
      ws.onopen = () => {};
      ws.onmessage = (e) => {
        try {
          const frame = JSON.parse(e.data);
          setWsData(frame);
          setWsActive(true);
        } catch (err) {}
      };
      ws.onerror = () => { try { ws.close(); } catch (err) {} };
      ws.onclose = () => {
        setWsActive(false);
        timer = setTimeout(connect, 2000);
      };
    }
    connect();

    deadCheck = setInterval(() => {
      setWsData(current => {
        if (!current) return current;
        const age = (Date.now() - new Date(current.timestamp).getTime()) / 1000;
        if (age > 3.0) setWsActive(false);
        return current;
      });
    }, 1000);

    return () => {
      clearTimeout(timer);
      clearInterval(deadCheck);
      if (ws) ws.close();
    };
  }, []);

  const data = wsActive && wsData ? wsData : pollData;
  const error = pollError;

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setT(n => {
      if (n >= 120) { setPlaying(false); return 120; }
      return n + 1;
    }), 1000);
    return () => clearInterval(id);
  }, [playing]);

  if (error && !data) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const m = data.metrics || {};
  const isStream = wsActive && wsData;
  const simulated = data.mode === 'SIMULATION' || data.source_type === 'SIMULATION';
  const motTempF = m.motor_temp_f ?? m.temperature ?? 0;
  const warnTempF = prefs.warning_temp || 160;
  const warnBat = prefs.warning_battery || 20;
  const isHot = motTempF >= warnTempF;
  const isLowSoc = (m.battery ?? 100) <= warnBat;
  const tempTag = motTempF >= 195 ? 'HOT' : (motTempF >= 160 ? 'WARM' : 'OK');

  const history = (data.history || []).map((pt, idx) => ({
    seconds: pt.seconds != null ? Number(pt.seconds) : idx,
    speed: Number(pt.speed ?? m.speed ?? 0),
    rpm: Number(pt.rpm ?? m.rpm ?? 0),
    throttle: Number(pt.throttle ?? m.throttle_pct ?? 0),
    brake: Number(pt.brake ?? m.brake_pct ?? 0),
    power_kw: Number(pt.power_kw ?? (m.power_kw ?? 0)),
    temperature: Number(pt.temperature ?? motTempF),
  }));

  return (
    <>
      {/* 1. Telemetry Link Status Header */}
      {isStream ? (
        <div className="link-status-banner active">
          <div>
            <span className="pill green">🟢 TELEMETRY LINK: ACTIVE (CAN-0 · 20 Hz F1 PUSH)</span>
            <span style={{ marginLeft: 12, fontSize: 12, color: '#E2E8F0' }}>
              FRAME ID: <strong style={{ color: '#FFFFFF' }}>#{data.log_id || 'LIVE'}</strong> &nbsp;|&nbsp;
              MODE: <strong style={{ color: 'var(--v-primary)' }}>{m.drive_mode || 'DRIVE'}</strong> &nbsp;|&nbsp;
              TRANS: <strong style={{ color: '#FFFFFF' }}>{m.gear || 'D'} [{m.transmission_mode || 'AUTO'}]</strong>
            </span>
          </div>
          <div>
            <span className="pill green">&lt;15ms LATENCY</span>
          </div>
        </div>
      ) : simulated ? (
        <div className="link-status-banner standby">
          <div>
            <span className="pill amber">🟡 SIMULATION SCENARIO ACTIVE</span>
            <span style={{ marginLeft: 12, fontSize: 12, color: '#E2E8F0' }}>
              TIME: <strong style={{ color: '#FFB800' }}>{t}s</strong> &nbsp;|&nbsp;
              BENCHMARK SIMULATOR
            </span>
          </div>
          <div>
            <span className="pill amber">SYNTHETIC FEED</span>
          </div>
        </div>
      ) : (
        <div className={`link-status-banner ${data.stale ? 'disconnected' : 'active'}`}>
          <div>
            <span className={`pill ${data.stale ? 'red' : 'green'}`}>
              {data.stale ? '🔴 TELEMETRY LINK: STANDBY' : '🟢 POSTGRESQL LINK: ACTIVE'}
            </span>
            <span style={{ marginLeft: 12, fontSize: 12, color: '#E2E8F0' }}>
              LAST PACKET: <strong style={{ color: data.stale ? '#FF4D6D' : '#00F5D4' }}>{data.timestamp ? date(data.timestamp) : 'IDLE'}</strong>
            </span>
          </div>
          <div>
            <span className={`pill ${data.stale ? 'red' : 'green'}`}>{data.stale ? 'STANDBY' : 'DATABASE'}</span>
          </div>
        </div>
      )}

      {/* Simulation Slider if active */}
      {data.mode === 'SIMULATION' && (
        <div className="simulation-bar" style={{ marginBottom: 14 }}>
          <div><strong>Simulation time</strong><span>{t} seconds · adjust the development scenario</span></div>
          <input aria-label="Simulation time" type="range" min="0" max="120" value={t} onChange={e => { setPlaying(false); setT(Number(e.target.value)); }} />
          <button className="icon-button" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}>
            {playing ? <Pause size={18} /> : <Play size={18} />}
          </button>
        </div>
      )}

      {/* 2. Critical Warning Strip */}
      {isHot && (
        <div className="notice danger">
          <AlertTriangle size={18} />
          <strong>🚨 CRITICAL THERMAL LIMIT: Motor Core Temperature {fmt(motTempF, 1)} °F exceeds calibrated threshold ({warnTempF} °F)!</strong>
        </div>
      )}
      {isLowSoc && (
        <div className="notice danger">
          <AlertTriangle size={18} />
          <strong>⚠️ LOW ENERGY ALERT: Battery State-of-Charge at {fmt(m.battery, 1)}% (Limit: {warnBat}%)!</strong>
        </div>
      )}

      {/* 3. Primary 6-Card Telemetry Strip */}
      <div className="metrics-6">
        <section className="panel metric">
          <div className="metric-label">Vehicle Speed <Gauge size={18} /></div>
          <div className="metric-value">{fmt(m.speed, 1)}<small>MPH</small></div>
          <div className="metric-delta">{m.transmission_mode || 'AUTO'} [{m.gear || 'D'}]</div>
        </section>

        <section className="panel metric">
          <div className="metric-label">Motor Velocity <Activity size={18} /></div>
          <div className="metric-value">{fmt(m.rpm, 0)}<small>RPM</small></div>
          <div className="metric-delta">Mode: {m.drive_mode || 'DRIVE'}</div>
        </section>

        <section className="panel metric">
          <div className="metric-label">Battery Pack SoC <Battery size={18} /></div>
          <div className="metric-value">{fmt(m.battery, 1)}<small>%</small></div>
          <div className={`metric-delta ${isLowSoc ? 'inverse' : ''}`}>Range: {m.est_range_mi || 0} mi</div>
        </section>

        <section className="panel metric">
          <div className="metric-label">Net Power Flow <Zap size={18} /></div>
          <div className="metric-value">{m.power_kw != null && m.power_kw > 0 ? '+' : ''}{fmt(m.power_kw, 1)}<small>kW</small></div>
          <div className="metric-delta">{fmt(m.voltage, 0)}V • {m.current != null && m.current > 0 ? '+' : ''}{fmt(m.current, 1)}A</div>
        </section>

        <section className="panel metric">
          <div className="metric-label">Driver Demand <Cpu size={18} /></div>
          <div className="metric-value">THR {fmt(m.throttle_pct, 0)}<small>%</small></div>
          <div className="metric-delta">BRK {fmt(m.brake_pct, 0)}%</div>
        </section>

        <section className="panel metric">
          <div className="metric-label">Motor Core Temp <Thermometer size={18} /></div>
          <div className="metric-value">{fmt(motTempF, 1)}<small>°F</small></div>
          <div className={`metric-delta ${isHot ? 'inverse' : ''}`}>Status: {tempTag}</div>
        </section>
      </div>

      {/* 4. Real-Time Telemetry Traces (Stacked Synchronized Architecture) */}
      <div className="section-line" style={{ marginTop: 20 }}>
        <div>
          <h2>Real-Time Telemetry Traces</h2>
          <p>Synchronized dual-axis vehicle channels streaming at 20 Hz push frequency.</p>
        </div>
      </div>

      {/* Chart 1: Speed & Motor Velocity Trace (Dual-Axis) */}
      <section className="panel plot">
        <div className="panel-heading">
          <div>
            <h3>Speed &amp; Motor Velocity Trace</h3>
            <p>Velocity (MPH) &amp; Motor RPM dual-axis rolling window</p>
          </div>
          <Activity size={17} />
        </div>
        <div style={{ height: 230 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 10, right: 30, bottom: 5, left: -5 }}>
              <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="rgba(255, 255, 255, 0.08)" />
              <XAxis dataKey="seconds" tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={v => `${fmt(v, 0)}s`} tickLine={false} axisLine={false} />
              <YAxis yAxisId="speed" orientation="left" domain={[0, 120]} tick={{ fontSize: 10, fill: 'var(--v-primary)' }} tickLine={false} axisLine={false} width={45} />
              <YAxis yAxisId="rpm" orientation="right" domain={[0, 8500]} tick={{ fontSize: 10, fill: '#E2E8F0' }} tickLine={false} axisLine={false} width={50} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" align="right" height={24} iconType="plainline" wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="speed" name="Speed (MPH)" type="monotone" dataKey="speed" stroke="var(--v-primary)" strokeWidth={2.4} dot={false} isAnimationActive={false} />
              <Line yAxisId="rpm" name="Motor RPM" type="monotone" dataKey="rpm" stroke="#E2E8F0" strokeWidth={1.5} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Chart 2: Driver Demand & Net Power Flow (Dual-Axis Area/Line) */}
      <section className="panel plot">
        <div className="panel-heading">
          <div>
            <h3>Driver Demand &amp; Net Power Flow</h3>
            <p>Throttle / Brake demand (%) with net power flow (kW)</p>
          </div>
          <Zap size={17} />
        </div>
        <div style={{ height: 230 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 10, right: 30, bottom: 5, left: -5 }}>
              <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="rgba(255, 255, 255, 0.08)" />
              <XAxis dataKey="seconds" tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={v => `${fmt(v, 0)}s`} tickLine={false} axisLine={false} />
              <YAxis yAxisId="demand" orientation="left" domain={[0, 100]} tick={{ fontSize: 10, fill: '#00F5A0' }} tickLine={false} axisLine={false} width={45} />
              <YAxis yAxisId="power" orientation="right" domain={[-30, 150]} tick={{ fontSize: 10, fill: '#00E5FF' }} tickLine={false} axisLine={false} width={50} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" align="right" height={24} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
              <Area yAxisId="demand" name="Throttle %" type="monotone" dataKey="throttle" stroke="#00F5A0" fill="#00F5A0" fillOpacity={0.15} strokeWidth={2} isAnimationActive={false} />
              <Area yAxisId="demand" name="Brake %" type="monotone" dataKey="brake" stroke="#FF4D6D" fill="#FF4D6D" fillOpacity={0.25} strokeWidth={2} isAnimationActive={false} />
              <Line yAxisId="power" name="Power (kW)" type="monotone" dataKey="power_kw" stroke="#00E5FF" strokeWidth={2} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Chart 3: Motor Core Temperature Trend */}
      <section className="panel plot">
        <div className="panel-heading">
          <div>
            <h3>Motor Core Temperature Trend (°F)</h3>
            <p>Thermal trend with active warning threshold ({warnTempF} °F)</p>
          </div>
          <Thermometer size={17} />
        </div>
        <div style={{ height: 230 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 10, right: 30, bottom: 5, left: -5 }}>
              <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="rgba(255, 255, 255, 0.08)" />
              <XAxis dataKey="seconds" tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={v => `${fmt(v, 0)}s`} tickLine={false} axisLine={false} />
              <YAxis domain={[60, max => Math.max(max + 10, warnTempF + 15)]} tick={{ fontSize: 10, fill: 'var(--v-primary)' }} tickLine={false} axisLine={false} width={45} />
              <Tooltip content={<CustomTooltip unit="°F" />} />
              <ReferenceLine y={warnTempF} stroke="#FF4D6D" strokeDasharray="5 4" label={{ value: `Warning Limit (${warnTempF}°F)`, position: 'insideTopRight', fill: '#FF4D6D', fontSize: 10 }} />
              <Line name="Motor Temp (°F)" type="monotone" dataKey="temperature" stroke="var(--v-primary)" strokeWidth={2.4} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* 5. Powertrain & High-Voltage Detailed Matrix */}
      <div className="matrix-grid">
        <section className="panel matrix-card">
          <div className="matrix-title"><Thermometer size={15} /> ⚡ THERMAL TELEMETRY MATRIX (°F)</div>
          <div className="matrix-items">
            <div className="matrix-subcard">
              <label>Motor Core</label>
              <strong style={{ color: isHot ? '#FF4D6D' : '#FFFFFF' }}>{fmt(motTempF, 1)} °F</strong>
            </div>
            <div className="matrix-subcard">
              <label>Power Inverter</label>
              <strong>{fmt(m.inverter_temp_f, 1)} °F</strong>
            </div>
            <div className="matrix-subcard">
              <label>Battery Pack</label>
              <strong>{fmt(m.battery_temp_f, 1)} °F</strong>
            </div>
            <div className="matrix-subcard">
              <label>Warning Threshold</label>
              <strong style={{ color: '#FFB800' }}>{warnTempF} °F</strong>
            </div>
          </div>
        </section>

        <section className="panel matrix-card">
          <div className="matrix-title"><Zap size={15} /> ⚡ HIGH-VOLTAGE PACK BUS</div>
          <div className="matrix-items">
            <div className="matrix-subcard">
              <label>Bus Voltage</label>
              <strong>{fmt(m.voltage, 1)} V</strong>
            </div>
            <div className="matrix-subcard">
              <label>Instant Current</label>
              <strong>{m.current != null && m.current > 0 ? '+' : ''}{fmt(m.current, 1)} A</strong>
            </div>
            <div className="matrix-subcard">
              <label>Net Flow</label>
              <strong>{m.power_kw != null && m.power_kw > 0 ? '+' : ''}{fmt(m.power_kw, 1)} kW</strong>
            </div>
            <div className="matrix-subcard">
              <label>Estimated Range</label>
              <strong style={{ color: isLowSoc ? '#FF4D6D' : '#00F5D4' }}>{m.est_range_mi || 0} mi</strong>
            </div>
          </div>
        </section>
      </div>

      {/* 6. Two-Way Pit-Wall Telecommand Console */}
      <section className="panel pitwall-panel">
        <div className="panel-heading">
          <div>
            <h3>Two-Way Pit-Wall Telecommand Console</h3>
            <p>Direct low-latency uplink to vehicle ECU (Port 9872 UDP loopback)</p>
          </div>
          <Radio size={17} style={{ color: 'var(--v-primary)' }} />
        </div>

        <div className="pitwall-grid">
          {/* Drive Mode Override */}
          <div className="pitwall-subcard">
            <div className="pitwall-label">Drive Mode Override</div>
            <div className="button-group">
              {['ECO', 'DRIVE', 'SPORT'].map(mode => (
                <button
                  key={mode}
                  type="button"
                  className={`btn-mode ${m.drive_mode === mode ? 'active' : ''}`}
                  onClick={() => sendCmd({ action: 'SET_DRIVE_MODE', value: mode })}
                  disabled={cmdBusy}
                >
                  {mode}
                </button>
              ))}
            </div>
            <small className="pitwall-hint">Overrides motor torque map &amp; throttle curve in real-time.</small>
          </div>

          {/* Pit Speed Limiter */}
          <div className="pitwall-subcard">
            <div className="pitwall-label">Pit Speed Limiter (35 MPH)</div>
            <div className="button-group">
              <button
                type="button"
                className={`btn-toggle ${!m.pit_limiter ? 'active-off' : ''}`}
                onClick={() => sendCmd({ action: 'SET_PIT_LIMIT', enabled: false })}
                disabled={cmdBusy}
              >
                OFF
              </button>
              <button
                type="button"
                className={`btn-toggle ${m.pit_limiter ? 'active-warn' : ''}`}
                onClick={() => sendCmd({ action: 'SET_PIT_LIMIT', enabled: true })}
                disabled={cmdBusy}
              >
                ⚠️ 35 MPH LIMIT
              </button>
            </div>
            <small className="pitwall-hint">Pins vehicle governor to 35 MPH and notifies cockpit HUD.</small>
          </div>

          {/* Power Derate Limit */}
          <div className="pitwall-subcard">
            <div className="pitwall-label">Inverter Power Limit</div>
            <div className="button-group">
              {[25, 50, 75, 100].map(pct => (
                <button
                  key={pct}
                  type="button"
                  className={`btn-pct ${(m.power_limit_pct ?? 100) === pct ? 'active' : ''}`}
                  onClick={() => sendCmd({ action: 'SET_POWER_LIMIT', value: pct })}
                  disabled={cmdBusy}
                >
                  {pct}%
                </button>
              ))}
            </div>
            <small className="pitwall-hint">Limits peak high-voltage inverter output wattage.</small>
          </div>

          {/* Driver Name Assignment */}
          <div className="pitwall-subcard">
            <div className="pitwall-label"><User size={13} /> Driver Assignment</div>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const name = driverInputLive.trim();
                if (!name) return;
                setCmdBusy(true);
                try {
                  await sendCmd({ action: 'SET_DRIVER_NAME', value: name });
                  await api('/sessions/driver', { method: 'POST', body: JSON.stringify({ name }) });
                  setDriverInputLive('');
                } finally {
                  setCmdBusy(false);
                }
              }}
              style={{ display: 'flex', gap: '6px' }}
            >
              <input
                type="text"
                className="driver-input"
                style={{ flex: 1, minWidth: 0, padding: '6px 8px', fontSize: '11px' }}
                placeholder={m.driver ? `Current: ${m.driver}` : 'Enter driver...'}
                value={driverInputLive}
                onChange={e => setDriverInputLive(e.target.value)}
                disabled={cmdBusy}
                maxLength={64}
              />
              <button
                type="submit"
                className="btn-mode active"
                style={{ padding: '6px 12px', flex: '0 0 auto', cursor: 'pointer' }}
                disabled={cmdBusy || !driverInputLive.trim()}
              >
                Set
              </button>
            </form>
            <small className="pitwall-hint">
              Active Driver: <strong style={{ color: 'var(--v-highlight)' }}>{m.driver || 'Driver 1'}</strong>
            </small>
          </div>
        </div>

        {/* DTC Injection and Clear Console */}
        <div className="dtc-console-strip">
          <div className="dtc-console-header">
            <div className="pitwall-label"><AlertTriangle size={15} style={{ color: '#FF4D6D' }} /> Remote Diagnostic Fault (DTC) Console</div>
            <button
              type="button"
              className="btn-clear-dtc"
              onClick={() => sendCmd({ action: 'CLEAR_DTC' })}
              disabled={cmdBusy}
            >
              <Check size={14} /> CLEAR ALL FAULTS
            </button>
          </div>

          <div className="dtc-quick-actions">
            <span className="dtc-quick-label">SIMULATE FAULT:</span>
            <button
              type="button"
              className="btn-dtc-tag"
              onClick={() => sendCmd({ action: 'INJECT_DTC', code: 'P0A38', desc: 'Motor Core Overheat' })}
              disabled={cmdBusy}
            >
              + P0A38 (Motor Overheat)
            </button>
            <button
              type="button"
              className="btn-dtc-tag"
              onClick={() => sendCmd({ action: 'INJECT_DTC', code: 'P0A80', desc: 'Pack Degradation' })}
              disabled={cmdBusy}
            >
              + P0A80 (Pack Degradation)
            </button>
            <button
              type="button"
              className="btn-dtc-tag"
              onClick={() => sendCmd({ action: 'INJECT_DTC', code: 'C1A20', desc: 'Inverter Comms Timeout' })}
              disabled={cmdBusy}
            >
              + C1A20 (Inverter Timeout)
            </button>
          </div>

          {cmdStatus && (
            <div className="cmd-status-toast">
              🟢 Telecommand dispatched: <code>{JSON.stringify(cmdStatus)}</code>
            </div>
          )}
        </div>
      </section>

      <p className="footnote">
        {isStream ? 'Source: high-frequency UDP ring buffer (<15ms latency, 20 Hz F1 push).' : simulated ? 'Simulated benchmark dataset; formula-generated responses.' : 'Source: onboard PostgreSQL telemetry database.'}
      </p>
    </>
  );
}

function Sessions({ api, onSelect, selected }) {
  const [version, setVersion] = useState(0);
  const [selectedIds, setSelectedIds] = useState([]);
  const [driverInput, setDriverInput] = useState('');
  const [driverBusy, setDriverBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  const { data, error } = useResource('sessions:' + version, () => api('/sessions'));

  useEffect(() => {
    if (!statusMsg) return;
    const t = setTimeout(() => setStatusMsg(null), 4000);
    return () => clearTimeout(t);
  }, [statusMsg]);

  if (error) return <ErrorBox error={error} />;
  if (!data) return <Loading />;

  const activeDriver = data[0]?.driver_identifier || 'Driver 1';

  async function handleSetDriver(e) {
    e?.preventDefault();
    const name = driverInput.trim();
    if (!name) return;
    setDriverBusy(true);
    try {
      await api('/sessions/driver', {
        method: 'POST',
        body: JSON.stringify({ name })
      });
      setStatusMsg(`Driver profile updated to: ${name}`);
      setDriverInput('');
      setVersion(v => v + 1);
    } catch (err) {
      alert(`Could not set driver: ${err.message}`);
    } finally {
      setDriverBusy(false);
    }
  }

  async function handleDeleteSingle(sessionId, e) {
    e?.stopPropagation();
    if (!window.confirm(`Delete Session #${sessionId} and all its recorded telemetry logs?`)) return;
    setDeleteBusy(true);
    try {
      await api(`/sessions/${sessionId}`, { method: 'DELETE' });
      setSelectedIds(prev => prev.filter(id => id !== sessionId));
      if (selected === sessionId) onSelect(null);
      setVersion(v => v + 1);
      setStatusMsg(`Session #${sessionId} deleted.`);
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleDeleteSelected() {
    if (!selectedIds.length) return;
    if (!window.confirm(`Delete ${selectedIds.length} selected session(s) and all associated telemetry?`)) return;
    setDeleteBusy(true);
    try {
      const res = await api('/sessions/delete', {
        method: 'POST',
        body: JSON.stringify({ session_ids: selectedIds })
      });
      if (selectedIds.includes(selected)) onSelect(null);
      setSelectedIds([]);
      setVersion(v => v + 1);
      setStatusMsg(`Deleted ${res.deleted_count || selectedIds.length} sessions.`);
    } catch (err) {
      alert(`Batch delete failed: ${err.message}`);
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleClearAll() {
    if (!window.confirm("⚠️ DANGER: Are you sure you want to permanently delete ALL vehicle sessions and wipe all telemetry logs? This cannot be undone.")) return;
    setDeleteBusy(true);
    try {
      await api('/sessions/delete-all', { method: 'POST' });
      onSelect(null);
      setSelectedIds([]);
      setVersion(v => v + 1);
      setStatusMsg("All vehicle sessions and telemetry database logs cleared.");
    } catch (err) {
      alert(`Clear all failed: ${err.message}`);
    } finally {
      setDeleteBusy(false);
    }
  }

  const allSelected = data.length > 0 && selectedIds.length === data.length;
  const someSelected = selectedIds.length > 0 && !allSelected;

  function toggleSelectAll() {
    if (allSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.map(s => s.id));
    }
  }

  function toggleSelect(id, e) {
    e?.stopPropagation();
    setSelectedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  }

  return (
    <>
      <section className="driver-panel">
        <div className="driver-panel-left">
          <User size={20} style={{ color: 'var(--v-primary)' }} />
          <div>
            <h3>Driver Profile & Uplink</h3>
            <p>Active Cockpit Driver: <strong style={{ color: 'var(--v-highlight)' }}>{activeDriver}</strong></p>
          </div>
        </div>
        <form className="driver-form" onSubmit={handleSetDriver}>
          <input
            type="text"
            className="driver-input"
            placeholder={activeDriver ? `Current: ${activeDriver}` : "Enter Driver Name / Callsign"}
            value={driverInput}
            onChange={e => setDriverInput(e.target.value)}
            disabled={driverBusy}
            maxLength={64}
          />
          <button
            type="submit"
            className="btn-driver-save"
            disabled={driverBusy || !driverInput.trim()}
          >
            <UserCheck size={14} />
            {driverBusy ? 'Assigning...' : 'Assign Driver'}
          </button>
        </form>
      </section>

      <div className="section-line">
        <div>
          <h2>Recorded Vehicle Sessions</h2>
          <p>Review telemetry history, manage driver assignments, and prune data records.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {selectedIds.length > 0 && (
            <span className="pill amber">{selectedIds.length} SELECTED</span>
          )}
          <span className="pill">{data.length} SESSIONS</span>
        </div>
      </div>

      {statusMsg && (
        <div className="cmd-status-toast" style={{ marginBottom: '12px' }}>
          🟢 {statusMsg}
        </div>
      )}

      <div className="session-actions-bar">
        <div className="session-actions-left">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--v-silver)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              className="session-checkbox"
              checked={allSelected}
              ref={el => { if (el) el.indeterminate = someSelected; }}
              onChange={toggleSelectAll}
            />
            <span>{allSelected ? 'Deselect All' : 'Select All'}</span>
          </label>
          {selectedIds.length > 0 && (
            <button
              type="button"
              className="btn-danger-outline"
              onClick={handleDeleteSelected}
              disabled={deleteBusy}
            >
              <Trash2 size={13} />
              Delete Selected ({selectedIds.length})
            </button>
          )}
        </div>
        <div className="session-actions-right">
          <button
            type="button"
            className="btn-danger-solid"
            onClick={handleClearAll}
            disabled={deleteBusy || data.length === 0}
          >
            <Trash2 size={13} />
            Clear All Sessions
          </button>
        </div>
      </div>

      <section className="panel table-panel">
        <table>
          <thead>
            <tr>
              <th style={{ width: '40px', textAlign: 'center' }}></th>
              <th>Session</th>
              <th>Date</th>
              <th>Duration</th>
              <th>Peak Temp</th>
              <th>Source</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.map(s => {
              const maxF = s.max_temp != null ? Math.round((s.max_temp * 9 / 5) + 32) : null;
              const isRowSelected = selectedIds.includes(s.id);
              return (
                <tr key={s.id} className={(selected === s.id ? 'selected ' : '') + (isRowSelected ? 'checked-row' : '')}>
                  <td style={{ textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      className="session-checkbox"
                      checked={isRowSelected}
                      onChange={e => toggleSelect(s.id, e)}
                    />
                  </td>
                  <td>
                    <strong>#{s.id}</strong>
                    <small>{s.driver_identifier || 'Driver not specified'}</small>
                  </td>
                  <td>{date(s.start_timestamp)}</td>
                  <td>{duration(s.duration_seconds)}</td>
                  <td>{fmt(maxF != null ? maxF : s.max_temp, 0)} °F</td>
                  <td>
                    <span className={'pill ' + (s.source_type === 'SIMULATION' ? 'amber' : 'green')}>
                      {s.source_type}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => onSelect(s.id)}
                      >
                        View diagnostics
                        <ChevronRight size={15} />
                      </button>
                      <button
                        type="button"
                        className="btn-delete-row"
                        title={`Delete Session #${s.id}`}
                        onClick={e => handleDeleteSingle(s.id, e)}
                        disabled={deleteBusy}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!data.length && <div className="empty">No sessions yet recorded.</div>}
      </section>
    </>
  );
}

function Diagnostics({ api, prefs, selected, onSelect }) {
  const sessions = useResource('diagnostic-sessions', () => api('/sessions'));
  const result = useResource('diagnostic:' + selected, () => selected ? api(`/sessions/${selected}/diagnostics`) : Promise.resolve(null));
  const charts = result.data?.charts;
  return (
    <>
      <div className="section-line">
        <div><h2>Performance analysis</h2><p>Five views of your selected session (Imperial standardized).</p></div>
        <select aria-label="Select session" value={selected || ''} onChange={e => onSelect(Number(e.target.value) || null)}>
          <option value="">Select a session</option>
          {sessions.data?.map(s => <option key={s.id} value={s.id}>Session #{s.id} · {s.source_type}</option>)}
        </select>
      </div>
      {sessions.error && <ErrorBox error={sessions.error} />}
      {result.error && <ErrorBox error={result.error} />}
      {!selected ? (
        <div className="panel empty"><History size={28} /><h3>Select a recorded session</h3><p>Choose a session above or open one from Sessions.</p></div>
      ) : !charts && !result.error ? (
        <Loading />
      ) : charts && (
        <>
          <div className="notice">
            <History size={17} />
            Session #{selected}
            <span>{result.data.session.source_type === 'SIMULATION' ? 'Simulated session data' : 'Recorded vehicle data'}</span>
          </div>
          <div className="diagnostic-grid">
            <Plot title="Energy efficiency vs. speed" subtitle="Speed (MPH) / consumption (Wh/mi)" data={charts.efficiency} unit="Wh/mi" />
            <Plot title="Power draw vs. temperature" subtitle="Motor temperature (°F) / power (W)" data={charts.power_temp} unit="W" />
            <Plot title="Battery vs. distance" subtitle="Distance (mi) / battery remaining (%)" data={charts.battery} color="#00F5A0" unit="%" />
            <Plot title="Power draw vs. motor RPM" subtitle="Motor speed (RPM) / power (W)" data={charts.power_rpm} color="#00E5FF" unit="W" />
            <Plot title="Temperature rise over time" subtitle="Operation time (min) / temperature (°F)" data={charts.temperature} limit={prefs.warning_temp} unit="°F" />
          </div>
        </>
      )}
    </>
  );
}

function Settings({ api, prefs, onSaved }) {
  const [draft, setDraft] = useState(prefs);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    setDraft(prefs);
  }, [prefs]);

  async function save(e) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      const value = await api('/settings', { method: 'PUT', body: JSON.stringify(draft) });
      onSaved(value);
      setMessage('Warning thresholds & palette calibration saved to your account.');
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function selectPalette(pkey) {
    const updated = { ...draft, palette: pkey };
    setDraft(updated);
    document.documentElement.setAttribute('data-palette', pkey);
    api('/settings', { method: 'PUT', body: JSON.stringify(updated) }).then(onSaved).catch(() => {});
  }

  const activeP = PALETTES[draft.palette] || PALETTES.mint;

  return (
    <>
      <div className="section-line">
        <div>
          <h2>Dashboard Settings &amp; Calibration</h2>
          <p>Technician alert thresholds, Imperial calibrations, and Cockpit Ambient Palettes.</p>
        </div>
      </div>

      <form className="panel settings-panel" onSubmit={save}>
        <div className="panel-heading">
          <h3>Telemetry Warning Thresholds (Imperial)</h3>
          <Settings2 size={18} />
        </div>
        <p>These settings customize the technician dashboard and trigger live warning strips.</p>

        <div className="setting">
          <div>
            <label htmlFor="warning_temp"><Thermometer size={18} /> Motor Temperature Warning Limit</label>
            <strong>{draft.warning_temp} °F</strong>
          </div>
          <input
            id="warning_temp"
            type="range"
            min={110}
            max={230}
            step={5}
            value={draft.warning_temp}
            onChange={e => { setDraft({ ...draft, warning_temp: Number(e.target.value) }); setMessage(''); }}
          />
          <div className="range-labels">
            <span>110 °F (Cold)</span>
            <span>160 °F (Nominal)</span>
            <span>230 °F (Critical)</span>
          </div>
        </div>

        <div className="setting">
          <div>
            <label htmlFor="warning_battery"><Battery size={18} /> Low Battery SoC Warning Limit</label>
            <strong>{draft.warning_battery} %</strong>
          </div>
          <input
            id="warning_battery"
            type="range"
            min={5}
            max={40}
            step={5}
            value={draft.warning_battery}
            onChange={e => { setDraft({ ...draft, warning_battery: Number(e.target.value) }); setMessage(''); }}
          />
          <div className="range-labels">
            <span>5 % (Critical)</span>
            <span>20 % (Standard)</span>
            <span>40 % (Conservative)</span>
          </div>
        </div>

        {error && <ErrorBox error={error} />}
        <div className="save-row">
          <button className="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save warning limits'}<Check size={16} />
          </button>
          {message && <span role="status">{message}</span>}
        </div>
      </form>

      {/* 2. Cockpit Ambient Palette Calibration */}
      <section className="panel settings-panel">
        <div className="panel-heading">
          <h3>🎨 Cockpit Ambient Palette Calibration (v5.4.0)</h3>
          <Palette size={18} />
        </div>
        <p>
          Bench-calibrate and preview the 5 signature OLED colorways engineered for the Voltesse cockpit instrument cluster.
          Selecting a colorway immediately updates the technician GUI theme and active accents.
        </p>

        <div className="palette-grid">
          {Object.entries(PALETTES).map(([pkey, pval]) => {
            const isSel = draft.palette === pkey;
            return (
              <div
                key={pkey}
                className={`palette-card ${isSel ? 'selected' : ''}`}
                style={{
                  border: `2px solid ${isSel ? pval.primary : 'rgba(255, 255, 255, 0.1)'}`,
                  boxShadow: isSel ? `0 0 14px ${pval.primary}40` : 'none',
                }}
              >
                <div
                  className="palette-swatch"
                  style={{ background: `linear-gradient(90deg, ${pval.primary}, ${pval.highlight}, ${pval.secondary})` }}
                />
                <strong>{pval.display}</strong>
                <small>{pval.primary}</small>
                <button
                  type="button"
                  className={`palette-select-btn ${isSel ? 'primary' : ''}`}
                  style={{
                    background: isSel ? pval.primary : 'rgba(255, 255, 255, 0.08)',
                    color: isSel ? '#080C0E' : '#E2E8F0',
                    border: `1px solid ${isSel ? pval.highlight : 'rgba(255, 255, 255, 0.15)'}`
                  }}
                  onClick={() => selectPalette(pkey)}
                >
                  {isSel ? '✓ ACTIVE' : 'SELECT'}
                </button>
              </div>
            );
          })}
        </div>

        <div className="matrix-items" style={{ margin: '18px 0 14px' }}>
          <div className="matrix-subcard">
            <label>Active Colorway</label>
            <strong style={{ color: activeP.primary }}>{activeP.display}</strong>
          </div>
          <div className="matrix-subcard">
            <label>Primary Accent</label>
            <strong>{activeP.primary}</strong>
          </div>
          <div className="matrix-subcard">
            <label>Highlight Glow</label>
            <strong>{activeP.highlight}</strong>
          </div>
          <div className="matrix-subcard">
            <label>OLED Contrast</label>
            <strong style={{ color: '#00F5D4' }}>{activeP.contrast}</strong>
          </div>
        </div>
      </section>
    </>
  );
}

function Backups({ api }) {
  const [version, setVersion] = useState(0), [busy, setBusy] = useState(false), [error, setError] = useState(null), [success, setSuccess] = useState('');
  const result = useResource('backups:' + version, () => api('/backups'));
  async function backup() {
    setBusy(true);
    setError(null);
    setSuccess('');
    try {
      const r = await api('/backups', { method: 'POST' });
      setSuccess(`Backup #${r.backup_id} completed on the backend host.`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
      setVersion(n => n + 1);
    }
  }
  return (
    <>
      <div className="section-line">
        <div><h2>Database backups</h2><p>Create and review manual backups of the telemetry database.</p></div>
        <button className="primary" disabled={busy} onClick={backup}>
          <Download size={17} />{busy ? 'Creating backup…' : 'Create backup'}
        </button>
      </div>
      <div className="notice">
        <ShieldCheck size={17} />
        Backups remain on the backend host.
        <span>Includes account hashes. Access is restricted; files are never served publicly.</span>
      </div>
      {error && <ErrorBox error={error} />}
      {success && <div className="notice success" role="status"><Check size={17} />{success}</div>}
      {result.error ? (
        <ErrorBox error={result.error} />
      ) : !result.data ? (
        <Loading />
      ) : (
        <section className="panel table-panel">
          <table>
            <thead><tr><th>Backup</th><th>Created</th><th>Type</th><th>Status</th></tr></thead>
            <tbody>
              {result.data.map(b => (
                <tr key={b.backup_id}>
                  <td>#{b.backup_id}</td>
                  <td>{date(b.backup_timestamp)}</td>
                  <td>{b.backup_type}</td>
                  <td><span className={'pill ' + (b.backup_status === 'FAILED' ? 'red' : b.backup_status === 'SUCCESS' ? 'green' : 'amber')}>{b.backup_status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!result.data.length && <div className="empty">No backup records yet.</div>}
        </section>
      )}
    </>
  );
}

export default function App() {
  const [user, setUser] = useState(null), [checking, setChecking] = useState(true), [page, setPage] = useState('Live'), [selected, setSelected] = useState(null), [prefs, setPrefs] = useState(null), [error, setError] = useState(null), [sessionError, setSessionError] = useState(null), [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    request('/auth/me').then(setUser).catch(e => {
      if (e.status !== 401) setSessionError(e);
    }).finally(() => setChecking(false));
  }, []);

  async function api(path, options) {
    try {
      return await request(path, options, user?.csrf_token);
    } catch (e) {
      if (e.status === 401) {
        setUser(null);
        setPrefs(null);
        setSelected(null);
        setPage('Live');
        setSessionError(new Error('Your session has expired. Please sign in again.'));
      }
      throw e;
    }
  }

  useEffect(() => {
    let active = true;
    if (user) {
      request('/settings').then(v => {
        if (active) {
          setPrefs(v);
          if (v?.palette) {
            document.documentElement.setAttribute('data-palette', v.palette);
          }
        }
      }).catch(e => {
        if (active) setError(e);
      });
    }
    return () => { active = false; };
  }, [user]);

  async function signOut() {
    setLoggingOut(true);
    setError(null);
    try {
      await api('/auth/logout', { method: 'POST' });
      setUser(null);
      setPrefs(null);
      setSelected(null);
      setPage('Live');
      setSessionError(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoggingOut(false);
    }
  }

  if (checking) return <div className="startup"><Brand /><Loading /></div>;
  if (!user) return <Login initialError={sessionError} onLogin={u => { setError(null); setSessionError(null); setUser(u); }} />;

  return (
    <div className="workspace" data-palette={prefs?.palette || 'mint'}>
      <aside className="sidebar">
        <Brand />
        <div className="sidebar-label">WORKSPACE</div>
        <nav>
          {PAGES.map(([key, label, Icon]) => (
            <button key={key} className={page === key ? 'active' : ''} onClick={() => setPage(key)}>
              <Icon size={18} />{label}
              {page === key && <ChevronRight size={14} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="security-note">
            <ShieldCheck size={18} />
            <div>Authenticated access<span>Technician workspace</span></div>
          </div>
          <div className="account">
            <div className="avatar">{user.name.slice(0, 1).toUpperCase()}</div>
            <div>
              <strong>{user.name}</strong>
              <span>{user.role.toLowerCase()}</span>
            </div>
            <button aria-label="Sign out" title="Sign out" onClick={signOut} disabled={loggingOut}>
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      <main className="content">
        <header>
          <div>
            <span className="eyebrow">VOLTESSE DASH / WORKSPACE</span>
            <h1>{PAGES.find(p => p[0] === page)[1]}</h1>
          </div>
          <div className="header-tag"><span /> TECHNICIAN / ADMIN</div>
        </header>

        <div className="page-content">
          {error && <ErrorBox error={error} />}
          <ErrorBoundary key={page}>
            {!prefs ? (
              <Loading />
            ) : page === 'Live' ? (
              <Live api={api} prefs={prefs} />
            ) : page === 'Sessions' ? (
              <Sessions api={api} selected={selected} onSelect={id => { setSelected(id); setPage('Diagnostics'); }} />
            ) : page === 'Diagnostics' ? (
              <Diagnostics api={api} prefs={prefs} selected={selected} onSelect={setSelected} />
            ) : page === 'Settings' ? (
              <Settings api={api} prefs={prefs} onSaved={setPrefs} />
            ) : (
              <Backups api={api} />
            )}
          </ErrorBoundary>
        </div>

        <footer>
          <span>VOLTESSE FORMULA ELECTRIC</span>
          <span>Technician interface · laptop workspace</span>
        </footer>
      </main>
    </div>
  );
}
