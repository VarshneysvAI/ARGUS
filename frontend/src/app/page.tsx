'use client';

import React, { useState, useEffect, useCallback } from 'react';
import MapView from '@/components/MapView';
import { Zap, Download, ChevronDown, Activity, ShieldAlert, FileText, Terminal, BarChart3, X, ExternalLink, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, BarChart, Bar, Brush } from 'recharts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

type ViewState = 'splash' | 'terminal' | 'dashboard';

export default function Dashboard() {
  const [viewState, setViewState] = useState<ViewState>('splash');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [pipelineData, setPipelineData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [streamLogs, setStreamLogs] = useState<string[]>([]);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [latency, setLatency] = useState<number | null>(null);
  
  const [inputText, setInputText] = useState("Tanker seizure reported in the Strait of Hormuz. Initial reports indicate 15 mbd blocked for at least 30 days.");
  const [argueMode, setArgueMode] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [challengePanel, setChallengePanel] = useState<{claim:string,source:string,result:any,loading:boolean}|null>(null);
  const [userObjection, setUserObjection] = useState("");
  const [osintOpen, setOsintOpen] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [graphData, setGraphData] = useState<any[]>([]);
  const [graphLoading, setGraphLoading] = useState(false);

  // Timer logic for Terminal state
  useEffect(() => {
      let interval: ReturnType<typeof setInterval>;
      if (viewState === 'terminal' && loading) {
          interval = setInterval(() => {
              setElapsedTime(prev => prev + 0.1);
          }, 100);
      }
      return () => clearInterval(interval);
  }, [viewState, loading]);

  const handleLiveSignal = async (overrideText?: string) => {
    if (viewState === 'splash') setViewState('terminal');
    setLoading(true);
    setStreamLogs([]);
    setElapsedTime(0);
    const t0 = performance.now();
    try {
      const payloadText = typeof overrideText === 'string' ? overrideText : inputText;
      
      const response = await fetch(`${API_BASE}/api/signal`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ signal_data: payloadText })
      });
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter(Boolean);
          for (const line of lines) {
              try {
                  const data = JSON.parse(line);
                  if (data.log) {
                      setStreamLogs(prev => [...prev, data.log]);
                  } else if (data.final) {
                      const t1 = performance.now();
                      setPipelineData(data.final);
                      setLatency(Number(((t1 - t0) / 1000).toFixed(3)));
                      
                      // Transition to dashboard after a short delay so user sees final log
                      setTimeout(() => {
                          setViewState('dashboard');
                      }, 1200);
                  }
              } catch {
                  // Ignore JSON parse errors
              }
          }
      }
      setArgueMode(false);
    } catch (e) {
      console.error(e);
      setStreamLogs(prev => [...prev, "[ERROR] Backend connection failed. Ensure uvicorn is running on port 8000."]);
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
      window.print();
  };

  const handleChallenge = useCallback((claimText: string, source: string) => {
    setChallengePanel({claim: claimText, source, result: null, loading: false});
    setUserObjection("");
  }, []);

  const runChallengeAudit = useCallback(async () => {
    if (!challengePanel) return;
    setChallengePanel(prev => prev ? {...prev, loading: true} : null);
    try {
      const res = await fetch(`${API_BASE}/api/challenge`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          claim_text: challengePanel.claim, 
          claim_source: challengePanel.source, 
          user_query: userObjection,
          math_context: JSON.stringify(pipelineData?.math_state || {})
        })
      });
      const data = await res.json();
      setChallengePanel(prev => prev ? {...prev, result: data, loading: false} : null);
    } catch { setChallengePanel(prev => prev ? {...prev, result: {verdict:'ERROR',reasoning:'Backend unreachable'}, loading: false} : null); }
  }, [challengePanel, userObjection, pipelineData]);

  const handleGraphAnalysis = useCallback(async () => {
    setGraphOpen(true); setGraphLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/graph-analysis`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({math_context: JSON.stringify(pipelineData?.math_state || {})})
      });
      const data = await res.json();
      setGraphData(data.charts || []);
    } catch { setGraphData([]); }
    setGraphLoading(false);
  }, [pipelineData]);

  const renderNarrative = (text: string) => {
      // Clean nested claims: flatten any [CLAIM...][CLAIM...] into single claims
      let cleaned = text.replace(/\[CLAIM[^\]]*\]\s*\[CLAIM/g, '[CLAIM');
      // Remove any remaining unclosed tags
      cleaned = cleaned.replace(/\[CLAIM[^\]]*\](?![\s\S]*?\[\/CLAIM\])/g, '');
      const parts = cleaned.split(/(\[CLAIM[\s\S]*?\[\/CLAIM\])/g);
      return parts.map((part, i) => {
          if (part.startsWith('[CLAIM')) {
              const match = part.match(/\[CLAIM.*?source=['"]([^'"]+)['"].*?\]([\s\S]*?)\[\/CLAIM\]/i);
              if (match) {
                  const source = match[1];
                  const content = match[2].replace(/\[\/?CLAIM[^\]]*\]/g, '').trim();
                  return (
                      <span key={i}
                            className="bg-blue-900/30 text-blue-300 px-1 rounded border-b border-blue-500/50 cursor-pointer hover:bg-blue-800/50 transition-colors relative group"
                            onClick={() => handleChallenge(content, source)}
                      >
                          {content}
                          <span className="absolute -top-6 left-0 bg-neutral-800 text-[10px] text-neutral-300 px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
                             Source: {source} (Click to Challenge)
                          </span>
                      </span>
                  );
              }
          }
          // Strip any leftover raw claim tags from non-matched text
          const cleanPart = part.replace(/\[\/?CLAIM[^\]]*\]/g, '').trim();
          return cleanPart ? <span key={i}>{cleanPart} </span> : null;
      });
  };

  // --- SPLASH SCREEN ---
  if (viewState === 'splash') {
      return (
          <div className="h-screen flex flex-col items-center justify-center bg-neutral-950 text-neutral-200">
              <div className="flex flex-col items-center text-center max-w-2xl gap-6">
                  <ShieldAlert size={64} className="text-blue-500 mb-4" />
                  <h1 className="text-5xl font-black tracking-widest bg-gradient-to-r from-blue-400 to-emerald-400 text-transparent bg-clip-text uppercase">ARGUS Resilience Engine</h1>
                  <p className="text-lg text-neutral-400">Institutional Grade Supply Chain Intelligence & Risk Mitigation</p>
                  
                  <div className="w-full bg-neutral-900 border border-neutral-800 rounded p-4 text-left my-4">
                      <p className="text-xs text-neutral-500 font-mono uppercase mb-2">Live Intel Signal Input</p>
                      <textarea 
                         className="w-full bg-black border border-neutral-800 rounded p-3 text-sm text-neutral-300 focus:outline-none focus:border-blue-500" 
                         rows={3}
                         value={inputText}
                         onChange={(e) => setInputText(e.target.value)}
                      />
                  </div>

                  <button 
                      onClick={() => handleLiveSignal()}
                      className="flex items-center gap-3 bg-red-600 hover:bg-red-500 text-white px-8 py-4 rounded font-bold transition-all shadow-[0_0_20px_rgba(220,38,38,0.3)] hover:scale-105"
                  >
                      <Zap size={20} />
                      INITIATE LIVE STREAMING DEMO
                  </button>
              </div>
          </div>
      );
  }

  // --- TERMINAL SCREEN ---
  if (viewState === 'terminal') {
      return (
          <div className="h-screen flex flex-col bg-black text-emerald-400 font-mono p-8">
              <div className="flex justify-between items-center mb-8 border-b border-emerald-900/50 pb-4">
                  <div className="flex items-center gap-3 text-emerald-500">
                      <Terminal size={24} />
                      <h2 className="text-xl font-bold tracking-widest uppercase">Agent Transparency Terminal</h2>
                  </div>
                  <div className="flex items-center gap-2 bg-emerald-950/30 px-4 py-2 border border-emerald-900/50">
                      <Activity size={16} className="animate-pulse" />
                      <span>Signal ➔ Recommendation: {elapsedTime.toFixed(1)}s</span>
                  </div>
              </div>
              <div className="flex-1 overflow-y-auto flex flex-col gap-2">
                  {streamLogs.map((log, i) => (
                      <div key={i} className="animate-fade-in flex gap-4">
                          <span className="text-emerald-700">[{new Date().toISOString().split('T')[1].slice(0,12)}]</span>
                          <span>{log}</span>
                      </div>
                  ))}
                  {loading && <div className="animate-pulse text-emerald-600 mt-4">_</div>}
                  {!loading && pipelineData && (
                      <div className="text-blue-400 mt-4 font-bold">
                          [OK] Stage 5 Validation Passed. Transitioning to Command Hub...
                      </div>
                  )}
              </div>
          </div>
      );
  }

  // --- MASTER DASHBOARD ---
  return (
    <div className="min-h-screen h-screen flex flex-col bg-neutral-950 text-neutral-200 font-sans print:h-auto print:bg-white print:text-black">
      
      {/* 1. HEADER ROW */}
      <header className="flex-none flex items-center justify-between px-6 py-3 bg-neutral-900 border-b border-neutral-800 print:hidden">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-widest text-neutral-100">ARGUS COMMAND PANEL</h1>
          {latency && (
            <div className="flex items-center gap-2 bg-emerald-950/50 text-emerald-400 px-3 py-1 rounded text-xs font-mono border border-emerald-900/50">
              <Activity size={14} />
              <span>Signal ➔ Recommendation: {latency}s</span>
            </div>
          )}
        </div>
        <div className="flex gap-3 items-center">
            {argueMode && (
                <div className="flex items-center gap-2">
                    <input type="text" className="bg-neutral-800 border border-neutral-700 rounded px-3 py-1.5 text-xs w-[400px] text-white focus:outline-none focus:border-blue-500" value={inputText} onChange={e=>setInputText(e.target.value)} />
                    <button onClick={() => handleLiveSignal(inputText)} className="bg-blue-600 hover:bg-blue-500 px-4 py-1.5 rounded text-xs font-bold transition-colors text-white">Recompute</button>
                    <button onClick={() => setArgueMode(false)} className="text-neutral-400 hover:text-white px-2 text-xs">Cancel</button>
                </div>
            )}
            <button onClick={handleGraphAnalysis} className="flex items-center gap-2 bg-purple-900/50 hover:bg-purple-800/50 border border-purple-700/50 px-3 py-1.5 rounded text-xs font-bold transition-colors text-purple-300">
              <BarChart3 size={14} /> GRAPH ANALYSIS
            </button>
            <button onClick={handlePrint} className="flex items-center gap-2 bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded text-xs font-bold transition-colors text-neutral-300">
              <Download size={14} /> EXPORT PDF
            </button>
        </div>
      </header>

      {/* 2. MAIN SPLIT CONTENT */}
      <main className="flex-1 flex overflow-hidden print:overflow-visible print:block">
        
        {/* LEFT PANEL: STRATEGIC INTEL (60%) */}
        <section className="w-[60%] flex flex-col border-r border-neutral-800 overflow-y-auto bg-neutral-950 print:w-full print:border-none print:overflow-visible">
            
            {/* BLUF */}
            <div className="p-6 border-b border-neutral-800 bg-neutral-900/30 print:break-inside-avoid print:border-b-2 print:border-black">
                <h2 className="text-xs uppercase tracking-widest text-neutral-500 font-bold mb-3 flex items-center gap-2 print:text-black">
                    <FileText size={14}/> BLUF (Bottom Line Up Front)
                </h2>
                {pipelineData && (
                    <p className="text-lg leading-relaxed text-neutral-200 print:text-black">
                        High-risk disruption in the <strong className="text-white uppercase print:text-black">{pipelineData.extraction.corridor}</strong> impacting <strong className="text-white uppercase print:text-black">{pipelineData.extraction.named_refinery}</strong>. 
                        Daily exposure <strong className="text-red-400 print:text-red-700">₹ {pipelineData.math_state.cost_metrics.c_delta_inr_crore_day} crore/day</strong>.
                        Volume Lost: {pipelineData.extraction.volume_lost_mbd} mbd.
                    </p>
                )}
            </div>

            {/* ADVERSARIAL SYNTHESIS */}
            {pipelineData && (
                <div className="p-6 border-b border-neutral-800 flex-1 print:break-inside-avoid print:border-b-2 print:border-black">
                    <h3 className="text-xs font-bold mb-4 text-neutral-500 uppercase tracking-widest flex items-center gap-2 print:text-black">
                        <ShieldAlert size={14}/> Strategic Intelligence Briefing
                    </h3>
                    <div className="prose prose-invert max-w-none text-neutral-300 text-base leading-relaxed print:text-black print:prose-p:text-black">
                        {renderNarrative(pipelineData.narrative)}
                    </div>
                </div>
            )}

            {/* ECONOMIC CASCADE */}
            {pipelineData && (
                <div className="p-6 bg-neutral-900/20 print:break-inside-avoid print:bg-white print:border-b-2 print:border-black">
                    <h3 className="text-xs font-bold mb-4 text-neutral-500 uppercase tracking-widest flex items-center gap-2 print:text-black">
                        NATIONAL ECONOMIC CASCADE
                    </h3>
                    <div className="flex gap-6">
                        <div className="flex-1 flex flex-col gap-1 p-4 border border-neutral-800 rounded bg-neutral-900/50 print:border-black print:bg-white">
                            <span className="text-[10px] text-neutral-500 uppercase tracking-widest font-bold print:text-neutral-700">Pump Price</span>
                            <span className="text-xl font-mono text-red-400 print:text-red-700">+₹{pipelineData.math_state.economic_impact.pump_price_impact_inr}/litre</span>
                        </div>
                        <div className="flex-1 flex flex-col gap-1 p-4 border border-neutral-800 rounded bg-neutral-900/50 print:border-black print:bg-white">
                            <span className="text-[10px] text-neutral-500 uppercase tracking-widest font-bold print:text-neutral-700">Power Sector</span>
                            <span className={`text-xl font-mono ${pipelineData.math_state.economic_impact.power_sector_stress === 'ELEVATED' ? 'text-yellow-500 print:text-yellow-700' : 'text-emerald-500 print:text-emerald-700'}`}>
                                {pipelineData.math_state.economic_impact.power_sector_stress}
                            </span>
                        </div>
                        <div className="flex-1 flex flex-col gap-1 p-4 border border-neutral-800 rounded bg-neutral-900/50 print:border-black print:bg-white">
                            <span className="text-[10px] text-neutral-500 uppercase tracking-widest font-bold print:text-neutral-700">GDP Impact</span>
                            <span className="text-xl font-mono text-red-400 print:text-red-700">{pipelineData.math_state.economic_impact.gdp_impact_bps} bps</span>
                            <span className="text-[10px] text-neutral-600 print:text-neutral-500">(heuristic)</span>
                        </div>
                    </div>
                </div>
            )}
        </section>

        {/* RIGHT PANEL: VISUAL EVIDENCE (40%) */}
        <section className="w-[40%] flex flex-col overflow-y-auto bg-neutral-950 print:w-full print:overflow-visible print:block">
            
            {/* MAP */}
            <div className="min-h-[300px] border-b border-neutral-800 shrink-0 relative bg-black print:break-inside-avoid print:border-b-2 print:border-black">
                <MapView />
                <div className="absolute top-2 right-2 bg-black/60 px-2 py-1 text-[10px] text-neutral-400 font-mono rounded">3D SATELLITE MAP — Mapbox</div>
            </div>
            
            {/* IMF PORTWATCH / AIS CAVEAT */}
            {pipelineData && (
                <div className="p-3 border-b border-neutral-800 bg-neutral-900/50 print:break-inside-avoid print:border-b-2 print:border-black print:bg-gray-100">
                    <p className="text-[10px] text-neutral-400 font-mono leading-relaxed print:text-black">
                        <span className="text-amber-500 font-bold uppercase mr-2 print:text-black">Dark Zone Warning:</span>
                        AIS-observed traffic in the primary corridor reflects significantly reduced pre-crisis volume. This is consistent with maritime intelligence reporting of deliberate transponder suppression and GPS spoofing during the active conflict. 
                        <a href="https://portwatch.imf.org/" target="_blank" rel="noreferrer" className="text-blue-400 ml-1 hover:underline print:text-blue-800">Verified via IMF PortWatch baseline.</a>
                    </p>
                </div>
            )}

            {/* SPR DRAWDOWN STRATEGIES */}
            {pipelineData && pipelineData.math_state.spr_strategy.s1_curve && (
                <div className="min-h-[250px] border-b border-neutral-800 p-4 shrink-0 flex flex-col bg-neutral-900/20 print:break-inside-avoid print:border-b-2 print:border-black print:bg-white">
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-2 flex justify-between items-center print:text-black">
                        <span>SPR DRAWDOWN STRATEGIES</span>
                        <span className="text-emerald-400 print:text-emerald-700">Recommended: {pipelineData.math_state.spr_strategy.recommended_strategy} — coverage {pipelineData.math_state.spr_strategy.coverage_days} days</span>
                    </h3>
                    <div className="flex-1 min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                            <LineChart data={pipelineData.math_state.spr_strategy.s1_curve.map((d: any, i: number) => ({ day: d.day, S1: d.stock, S2: pipelineData.math_state.spr_strategy.s2_curve[i]?.stock }))} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#555" vertical={false} />
                                <XAxis dataKey="day" stroke="#777" tick={{fontSize: 9}} axisLine={false} tickLine={false} label={{ value: 'days', position: 'insideBottomRight', offset: -5, fill: '#777', fontSize: 9 }} />
                                <YAxis stroke="#777" tick={{fontSize: 9}} axisLine={false} tickLine={false} domain={[0, pipelineData.math_state.spr_strategy.s_0 * 1.1]} />
                                <Tooltip contentStyle={{backgroundColor: '#000', border: '1px solid #333', fontSize: '10px'}} />
                                <ReferenceLine y={pipelineData.math_state.spr_strategy.s_min} stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'insideBottomLeft', value: 'S_min 20% floor', fill: '#ef4444', fontSize: 9 }} />
                                <Line type="stepAfter" dataKey="S1" stroke="#facc15" strokeWidth={1.5} dot={false} name="S1 max" />
                                <Line type="stepAfter" dataKey="S2" stroke="#60a5fa" strokeWidth={1.5} dot={false} name="S2 phased" />
                                <Brush dataKey="day" height={15} stroke="#333" fill="#111" tickFormatter={() => ''} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* PROCUREMENT CARDS */}
            {pipelineData && (
                <div className="p-4 border-b border-neutral-800 shrink-0 print:break-inside-avoid print:border-b-2 print:border-black">
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-3 print:text-black">
                        PROCUREMENT CARDS — HEURISTIC RANKED
                    </h3>
                    <div className="flex flex-col gap-2 font-mono text-xs">
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {pipelineData.math_state.procurement_cards.map((card: any, i: number) => {
                            const isClear = card.compliance_status === 'CLEAR';
                            return (
                                <div key={i} className={`flex items-center justify-between p-2 rounded print:border print:border-black ${isClear ? 'bg-neutral-900 border border-neutral-800 text-neutral-300 print:bg-white print:text-black' : 'bg-red-950/20 text-neutral-500 print:bg-gray-100 print:text-gray-500'}`}>
                                    <div className="flex items-center gap-4">
                                        {isClear ? (
                                            <span className="text-neutral-400 print:text-black">#{card.rank}</span>
                                        ) : (
                                            <span className="text-red-500 print:text-red-700">✕</span>
                                        )}
                                        <span className={isClear ? "text-neutral-200 print:text-black" : "text-neutral-500 line-through decoration-red-500/50 print:text-gray-500"}>{card.route}</span>
                                    </div>
                                    
                                    {isClear ? (
                                        <div className="flex items-center gap-4">
                                            <span>${card.landed_cost_usd_bbl}</span>
                                            <span>{card.lead_time_days}d</span>
                                            <span className="text-emerald-500 print:text-emerald-700">CLEAR</span>
                                        </div>
                                    ) : (
                                        <div className="text-red-500 print:text-red-700">COMPLIANCE-BLOCKED</div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* MATH X-RAY */}
            {pipelineData && (
                <div className="p-4 bg-neutral-900/30 flex-1 print:break-inside-avoid print:bg-white">
                    <details className="group cursor-pointer print:open" open>
                        <summary className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 flex items-center justify-between outline-none print:text-black">
                            <span>MATH X-RAY ▾ Data Origin Matrix + NumPy</span>
                            <ChevronDown size={14} className="group-open:rotate-180 transition-transform print:hidden"/>
                        </summary>
                        <div className="mt-3 text-[10px] font-mono text-neutral-400 print:text-black">
                            <table className="w-full text-left">
                                <thead className="text-neutral-600 border-b border-neutral-800 print:text-gray-700 print:border-gray-400">
                                    <tr>
                                        <th className="font-normal pb-1">Variable</th>
                                        <th className="font-normal pb-1">Value</th>
                                        <th className="font-normal pb-1">Origin Class</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr className="border-b border-neutral-800/50 print:border-gray-200">
                                        <td className="py-1 text-blue-400 print:text-blue-700">V_lost</td>
                                        <td className="py-1">{pipelineData.extraction.volume_lost_mbd} mbd</td>
                                        <td className="py-1">Live Extracted</td>
                                    </tr>
                                    <tr className="border-b border-neutral-800/50 print:border-gray-200">
                                        <td className="py-1 text-blue-400 print:text-blue-700">P_spot</td>
                                        <td className="py-1">${pipelineData.math_state.cost_metrics.p_spot || "79.20"}</td>
                                        <td className="py-1">EIA Daily Official Benchmark</td>
                                    </tr>
                                    <tr className="print:border-gray-200">
                                        <td className="py-1 text-blue-400 print:text-blue-700">fx</td>
                                        <td className="py-1">86.0</td>
                                        <td className="py-1">Static Adjustable</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </details>
                </div>
            )}

        </section>
      </main>

      {/* 3. FULL-WIDTH FOOTER: OSINT TICKER */}
      {pipelineData && (
          <footer className="flex-none bg-neutral-900 border-t border-neutral-800 py-3 px-6 flex items-center gap-4 print:break-inside-avoid print:bg-white print:border-t-2 print:border-black">
              <button onClick={() => setOsintOpen(true)} className="bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-bold px-3 py-1 rounded uppercase tracking-wider shrink-0 transition-colors cursor-pointer print:bg-blue-800">
                  OSINT TRACKER (TOP 3)
              </button>
              <div className="text-xs font-mono text-neutral-400 flex-1 truncate print:text-black">
                  {typeof pipelineData.osint_chatter === 'string' ? pipelineData.osint_chatter : pipelineData.osint_chatter?.summary}
              </div>
          </footer>
      )}

      {/* OSINT DETAIL MODAL */}
      {osintOpen && pipelineData && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8 print:hidden" onClick={() => setOsintOpen(false)}>
          <div className="bg-neutral-900 border border-neutral-700 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-neutral-800">
              <h3 className="text-sm font-bold uppercase tracking-widest text-blue-400 flex items-center gap-2"><ShieldAlert size={16}/> OSINT Intelligence Feed</h3>
              <button onClick={() => setOsintOpen(false)} className="text-neutral-500 hover:text-white"><X size={18}/></button>
            </div>
            <div className="p-4 flex flex-col gap-4">
              {(typeof pipelineData.osint_chatter === 'object' && pipelineData.osint_chatter?.articles ? pipelineData.osint_chatter.articles : [{title:'Intel Report',snippet:typeof pipelineData.osint_chatter==='string'?pipelineData.osint_chatter:pipelineData.osint_chatter?.summary,link:'#'}]).map((article: {title:string,snippet:string,link:string}, i: number) => (
                <div key={i} className="bg-neutral-800/50 border border-neutral-700/50 rounded-lg p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-[10px] font-bold text-blue-500 uppercase">RANK {i+1}</span>
                      <h4 className="text-sm font-bold text-neutral-200 mt-1">{article.title}</h4>
                      <p className="text-xs text-neutral-400 mt-2 leading-relaxed">{article.snippet}</p>
                    </div>
                    {article.link !== '#' && <a href={article.link} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 shrink-0"><ExternalLink size={14}/></a>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CLAIM CHALLENGE RIGHT PANEL */}
      {challengePanel && (
        <div className="fixed top-0 right-0 w-[420px] h-full bg-neutral-900 border-l border-neutral-700 z-50 flex flex-col shadow-2xl print:hidden">
          <div className="flex items-center justify-between p-4 border-b border-neutral-800 bg-neutral-950">
            <h3 className="text-xs font-bold uppercase tracking-widest text-amber-400">D-SHIELD Claim Audit</h3>
            <button onClick={() => setChallengePanel(null)} className="text-neutral-500 hover:text-white"><X size={18}/></button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            <div className="bg-blue-950/30 border border-blue-900/50 rounded p-3">
              <span className="text-[10px] text-blue-500 uppercase font-bold">Challenged Claim</span>
              <p className="text-sm text-blue-300 mt-1 leading-relaxed">{challengePanel.claim}</p>
              <span className="text-[10px] text-neutral-500 mt-2 block">Source: {challengePanel.source}</span>
            </div>
            {challengePanel.loading ? (
              <div className="flex items-center gap-3 text-amber-400 text-xs font-mono animate-pulse py-8 justify-center">
                <RefreshCw size={16} className="animate-spin"/> Querying adversarial LLM auditor...
              </div>
            ) : !challengePanel.result ? (
              <div className="flex flex-col gap-3 mt-2">
                <label className="text-[10px] text-neutral-500 uppercase font-bold">Specific Objection (Optional)</label>
                <textarea 
                  className="bg-neutral-950 border border-neutral-700 rounded p-2 text-xs text-neutral-300 focus:outline-none focus:border-amber-500" 
                  rows={3} 
                  placeholder="e.g. 'I believe the lead time for Saudi Aramco was updated recently to 10 days...'"
                  value={userObjection}
                  onChange={e => setUserObjection(e.target.value)}
                />
                <button onClick={runChallengeAudit} className="bg-amber-600 hover:bg-amber-500 text-white text-[10px] font-bold px-3 py-2 rounded transition-colors uppercase tracking-wider">
                  Run D-SHIELD Audit
                </button>
              </div>
            ) : challengePanel.result && (
              <>
                <div className={`rounded p-3 border ${challengePanel.result.verdict === 'CONFIRMED' ? 'bg-emerald-950/30 border-emerald-800/50' : challengePanel.result.verdict === 'DISPUTED' ? 'bg-red-950/30 border-red-800/50' : 'bg-yellow-950/30 border-yellow-800/50'}`}>
                  <span className="text-[10px] uppercase font-bold tracking-widest" style={{color: challengePanel.result.verdict === 'CONFIRMED' ? '#34d399' : challengePanel.result.verdict === 'DISPUTED' ? '#f87171' : '#fbbf24'}}>
                    Verdict: {challengePanel.result.verdict}
                  </span>
                  <span className="text-[10px] text-neutral-500 ml-2">Confidence: {((challengePanel.result.confidence||0)*100).toFixed(0)}%</span>
                </div>
                {challengePanel.result.reasoning && (
                  <div className="bg-neutral-800/50 rounded p-3">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold">Analysis</span>
                    <p className="text-xs text-neutral-300 mt-1 leading-relaxed">{challengePanel.result.reasoning}</p>
                  </div>
                )}
                {challengePanel.result.counter_evidence && (
                  <div className="bg-neutral-800/50 rounded p-3">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold">Counter Evidence</span>
                    <p className="text-xs text-neutral-300 mt-1 leading-relaxed">{challengePanel.result.counter_evidence}</p>
                  </div>
                )}
                {challengePanel.result.source_reliability && (
                  <div className="bg-neutral-800/50 rounded p-3">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold">Source Reliability</span>
                    <p className="text-xs text-neutral-300 mt-1 leading-relaxed">{challengePanel.result.source_reliability}</p>
                  </div>
                )}
                {challengePanel.result.source_link && challengePanel.result.source_link !== '#' && (
                  <div className="bg-neutral-800/50 rounded p-3">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold flex items-center gap-1"><ExternalLink size={10}/> Corroborating Source</span>
                    <a href={challengePanel.result.source_link} target="_blank" rel="noreferrer" className="text-[10px] text-blue-400 hover:text-blue-300 block mt-1 truncate">{challengePanel.result.source_link}</a>
                  </div>
                )}
                {challengePanel.result.verdict === 'DISPUTED' && challengePanel.result.suggested_revision && (
                  <div className="bg-amber-950/20 border border-amber-800/50 rounded p-3">
                    <span className="text-[10px] text-amber-500 uppercase font-bold">Suggested Revision</span>
                    <p className="text-xs text-amber-200 mt-1 leading-relaxed">{challengePanel.result.suggested_revision}</p>
                    <button className="mt-3 bg-amber-600 hover:bg-amber-500 text-white text-[10px] font-bold px-3 py-1.5 rounded transition-colors w-full" onClick={() => {
                      if (pipelineData) {
                        const updated = {...pipelineData, narrative: pipelineData.narrative.replace(challengePanel.claim, challengePanel.result.suggested_revision)};
                        setPipelineData(updated);
                        setChallengePanel(null);
                      }
                    }}>ACCEPT REVISION & UPDATE REPORT</button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* GRAPH ANALYSIS OVERLAY */}
      {graphOpen && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8 print:hidden" onClick={() => setGraphOpen(false)}>
          <div className="bg-neutral-900 border border-neutral-700 rounded-lg max-w-4xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-neutral-800">
              <h3 className="text-sm font-bold uppercase tracking-widest text-purple-400 flex items-center gap-2"><BarChart3 size={16}/> Strategic Graph Analysis</h3>
              <button onClick={() => setGraphOpen(false)} className="text-neutral-500 hover:text-white"><X size={18}/></button>
            </div>
            {graphLoading ? (
              <div className="flex items-center gap-3 text-purple-400 text-xs font-mono animate-pulse p-12 justify-center">
                <RefreshCw size={16} className="animate-spin"/> Generating strategic visualizations via LLM...
              </div>
            ) : (
              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Static charts from pipeline data */}
                {pipelineData && pipelineData.math_state.procurement_cards && (
                  <div className="bg-neutral-800/30 border border-neutral-700/50 rounded-lg p-4">
                    <h4 className="text-[10px] uppercase tracking-widest text-neutral-500 font-bold mb-3">Supplier Landed Cost Comparison ($/bbl)</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={pipelineData.math_state.procurement_cards.filter((c:{compliance_status:string})=>c.compliance_status==='CLEAR').map((c:{supplier:string,landed_cost_usd_bbl:number})=>({name:c.supplier,cost:c.landed_cost_usd_bbl}))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis dataKey="name" tick={{fontSize:9}} stroke="#777" />
                        <YAxis tick={{fontSize:9}} stroke="#777" domain={['dataMin - 5', 'dataMax + 5']} />
                        <Tooltip contentStyle={{backgroundColor:'#000',border:'1px solid #333',fontSize:'10px'}} />
                        <Bar dataKey="cost" fill="#60a5fa" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-[10px] text-neutral-500 mt-2">Lower landed cost indicates higher procurement priority after heuristic ranking.</p>
                  </div>
                )}
                {pipelineData && (
                  <div className="bg-neutral-800/30 border border-neutral-700/50 rounded-lg p-4">
                    <h4 className="text-[10px] uppercase tracking-widest text-neutral-500 font-bold mb-3">Lead Time vs Cost Tradeoff</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={pipelineData.math_state.procurement_cards.filter((c:{compliance_status:string})=>c.compliance_status==='CLEAR').map((c:{supplier:string,lead_time_days:number})=>({name:c.supplier,days:c.lead_time_days}))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis dataKey="name" tick={{fontSize:9}} stroke="#777" />
                        <YAxis tick={{fontSize:9}} stroke="#777" />
                        <Tooltip contentStyle={{backgroundColor:'#000',border:'1px solid #333',fontSize:'10px'}} />
                        <Bar dataKey="days" fill="#fbbf24" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-[10px] text-neutral-500 mt-2">Shorter lead times reduce exposure window but may command higher premiums.</p>
                  </div>
                )}
                {/* LLM-generated charts */}
                {graphData.map((chart: {title:string,data:{label:string,value:number}[],insight:string}, idx: number) => (
                  <div key={idx} className="bg-neutral-800/30 border border-neutral-700/50 rounded-lg p-4">
                    <h4 className="text-[10px] uppercase tracking-widest text-neutral-500 font-bold mb-3">{chart.title}</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={chart.data?.map(d => ({name: d.label, value: d.value})) || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis dataKey="name" tick={{fontSize:9}} stroke="#777" />
                        <YAxis tick={{fontSize:9}} stroke="#777" />
                        <Tooltip contentStyle={{backgroundColor:'#000',border:'1px solid #333',fontSize:'10px'}} />
                        <Bar dataKey="value" fill="#a78bfa" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-[10px] text-neutral-500 mt-2">{chart.insight}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* PRINT-ONLY SECTION (OSINT + CHARTS) */}
      <div className="hidden print:block print:w-full print:mt-12 print:border-t-2 print:border-black print:pt-6">
        <h2 className="text-xl font-bold uppercase tracking-widest text-black mb-6 border-b-2 border-black pb-2">APPENDIX A: Detailed Intelligence & Analytics</h2>
        
        {/* OSINT PRINT */}
        {pipelineData && pipelineData.osint_chatter && (
          <div className="mb-8">
            <h3 className="text-sm font-bold uppercase tracking-widest text-black mb-4 bg-gray-200 p-2">OSINT Feed Analysis</h3>
            <div className="flex flex-col gap-4">
              {(typeof pipelineData.osint_chatter === 'object' && pipelineData.osint_chatter?.articles ? pipelineData.osint_chatter.articles : [{title:'Intel Report',snippet:typeof pipelineData.osint_chatter==='string'?pipelineData.osint_chatter:pipelineData.osint_chatter?.summary,link:'#'}]).map((article: {title:string,snippet:string,link:string}, i: number) => (
                <div key={i} className="border border-black p-3 break-inside-avoid">
                  <span className="text-[10px] font-bold text-gray-500 uppercase block mb-1">RANK {i+1}</span>
                  <h4 className="text-sm font-bold text-black">{article.title}</h4>
                  <p className="text-xs text-black mt-2 leading-relaxed">{article.snippet}</p>
                  {article.link !== '#' && <span className="text-[10px] text-gray-500 mt-2 block break-all">Source: {article.link}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GRAPHS PRINT */}
        <div className="mb-8">
          <h3 className="text-sm font-bold uppercase tracking-widest text-black mb-4 bg-gray-200 p-2">Strategic Graph Analysis</h3>
          <div className="grid grid-cols-2 gap-4">
            {/* Print static charts */}
            {pipelineData && pipelineData.math_state.procurement_cards && (
              <div className="border border-black p-3 break-inside-avoid h-[250px] flex flex-col">
                <h4 className="text-[10px] uppercase tracking-widest text-black font-bold mb-3">Supplier Landed Cost Comparison ($/bbl)</h4>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pipelineData.math_state.procurement_cards.filter((c:{compliance_status:string})=>c.compliance_status==='CLEAR').map((c:{supplier:string,landed_cost_usd_bbl:number})=>({name:c.supplier,cost:c.landed_cost_usd_bbl}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                      <XAxis dataKey="name" tick={{fontSize:9, fill:'#000'}} stroke="#000" />
                      <YAxis tick={{fontSize:9, fill:'#000'}} stroke="#000" domain={['dataMin - 5', 'dataMax + 5']} />
                      <Bar dataKey="cost" fill="#3b82f6" radius={[2,2,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            {pipelineData && pipelineData.math_state.procurement_cards && (
              <div className="border border-black p-3 break-inside-avoid h-[250px] flex flex-col">
                <h4 className="text-[10px] uppercase tracking-widest text-black font-bold mb-3">Lead Time vs Cost Tradeoff</h4>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pipelineData.math_state.procurement_cards.filter((c:{compliance_status:string})=>c.compliance_status==='CLEAR').map((c:{supplier:string,lead_time_days:number})=>({name:c.supplier,days:c.lead_time_days}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                      <XAxis dataKey="name" tick={{fontSize:9, fill:'#000'}} stroke="#000" />
                      <YAxis tick={{fontSize:9, fill:'#000'}} stroke="#000" />
                      <Bar dataKey="days" fill="#f59e0b" radius={[2,2,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            {/* Print LLM charts if they were fetched */}
            {graphData.map((chart: {title:string,data:{label:string,value:number}[],insight:string}, idx: number) => (
              <div key={idx} className="border border-black p-3 break-inside-avoid h-[250px] flex flex-col">
                <h4 className="text-[10px] uppercase tracking-widest text-black font-bold mb-3">{chart.title}</h4>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chart.data?.map(d => ({name: d.label, value: d.value})) || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                      <XAxis dataKey="name" tick={{fontSize:9, fill:'#000'}} stroke="#000" />
                      <YAxis tick={{fontSize:9, fill:'#000'}} stroke="#000" />
                      <Bar dataKey="value" fill="#8b5cf6" radius={[2,2,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-[9px] text-gray-700 mt-2">{chart.insight}</p>
              </div>
            ))}
          </div>
        </div>
      </div>


    </div>
  );
}
