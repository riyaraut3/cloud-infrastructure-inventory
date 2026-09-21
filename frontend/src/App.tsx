import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, AlertTriangle, ArrowDownToLine, Boxes, CheckCircle2, CloudUpload, Database, FileText, HardDrive, Layers, Loader2, LockKeyhole, PackageSearch, RefreshCcw, Search, Server, ShieldCheck, UploadCloud, X } from 'lucide-react';

const API = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const BEARER = import.meta.env.VITE_AUTH_MODE === 'bearer';
type Part = { id: number; sku: string; name: string; site: string; supplier: string; quantity: number; reorder_level: number; unit_cost: string; inventory_value: string; low_stock: boolean; updated_at: string };
type Site = { site: string; sku_count: number; units: number; low_stock_count: number; value: string };
type Summary = { total_skus: number; total_units: number; low_stock_count: number; total_value: string; by_site: Site[] };
type Paged = { total: number; items: Part[]; limit: number; offset: number };
const usd = (n: number | string) => Number(n).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });

export default function App() {
  const [credential, setCredential] = useState('');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [parts, setParts] = useState<Paged | null>(null);
  const [search, setSearch] = useState('');
  const [site, setSite] = useState('');
  const [lowOnly, setLowOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const headers = useCallback((): HeadersInit => BEARER ? { Authorization: `Bearer ${credential.trim()}` } : { 'X-API-Key': credential }, [credential]);
  const request = useCallback(async (path: string, options?: RequestInit) => {
    const response = await fetch(`${API}${path}`, { ...options, headers: { ...headers(), ...options?.headers } });
    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try { detail = (await response.json()).detail || detail; } catch { /* non-JSON error */ }
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return response;
  }, [headers]);
  const refresh = useCallback(async () => {
    if (!credential.trim()) return;
    setBusy(true); setError('');
    try {
      const p = new URLSearchParams({ limit: '10', offset: String(offset) });
      if (search.trim()) p.set('q', search.trim());
      if (site) p.set('site', site);
      if (lowOnly) p.set('low_stock', 'true');
      const [statsResponse, partsResponse] = await Promise.all([request('/api/reports/summary'), request(`/api/parts?${p}`)]);
      setSummary(await statsResponse.json()); setParts(await partsResponse.json());
    } catch (e) { setError((e as Error).message); setParts(null); setSummary(null); }
    finally { setBusy(false); }
  }, [credential, offset, search, site, lowOnly, request]);
  useEffect(() => { void refresh(); }, [refresh]);

  const upload = async (file?: File) => {
    if (!file) return;
    if (!credential.trim()) { setError('Enter your access credential before uploading.'); return; }
    if (!file.name.toLowerCase().endsWith('.csv')) { setError('Select a .csv file.'); return; }
    if (file.size > 2 * 1024 * 1024) { setError('CSV must be smaller than 2 MiB.'); return; }
    setUploading(true); setError(''); setMessage('');
    try {
      const body = new FormData(); body.append('file', file);
      const result = await (await request('/api/inventory/imports', { method: 'POST', body })).json();
      setMessage(result.duplicate ? 'This exact file was already imported. No changes were made.' : `${result.rows} rows processed: ${result.created} new, ${result.updated} updated.`);
      setOffset(0); await refresh();
    } catch (e) { setError((e as Error).message); }
    finally { setUploading(false); if (input.current) input.current.value = ''; }
  };
  const exportCsv = async () => {
    setError('');
    try {
      const blob = await (await request('/api/reports/low-stock.csv')).blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'low-stock.csv'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError((e as Error).message); }
  };
  const empty = !summary?.total_skus;
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-icon"><Layers size={23} /></div><div><strong>InfraStock</strong><span>Infrastructure intelligence</span></div></div>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav active" href="#overview"><Activity size={18}/> Overview</a>
        <a className="nav" href="#inventory"><Boxes size={18}/> Inventory</a>
        <a className="nav" href="#upload"><CloudUpload size={18}/> Import data</a>
        <div className="nav-label second">PLATFORM</div>
        <div className="nav muted"><Database size={18}/> PostgreSQL</div>
        <div className="nav muted"><ShieldCheck size={18}/> AWS-ready architecture</div>
        <div className="sidebar-footer"><div className="status-dot"/> Portfolio demonstration<br/><small>Use synthetic data only</small></div>
      </aside>
      <main className="main" id="overview">
        <div className="top"><div><div className="eyebrow">INFRASTRUCTURE / OVERVIEW</div><h1>Inventory command center</h1><p>Monitor component availability across data center sites.</p></div><div className="top-actions"><span className="pill"><span className="status-dot"/> API secured</span><button className="btn btn-ghost" onClick={() => void refresh()} disabled={busy || !credential}><RefreshCcw size={16}/> Refresh</button></div></div>
        <div className="credential-row"><LockKeyhole size={18}/><label htmlFor="credential">{BEARER ? 'Bearer access token' : 'Local API key'}</label><input id="credential" aria-label="API credential" type="password" value={credential} onChange={e => setCredential(e.target.value)} placeholder={BEARER ? 'Paste a JWT access token' : 'Enter API_KEY from your .env file'} autoComplete="off"/><span>Held in memory only</span></div>
        {error && <div className="notice error" role="alert"><AlertTriangle size={17}/>{error}<button aria-label="Dismiss error" onClick={() => setError('')}><X size={16}/></button></div>}
        {message && <div className="notice success" role="status"><CheckCircle2 size={17}/>{message}<button aria-label="Dismiss message" onClick={() => setMessage('')}><X size={16}/></button></div>}
        <div className="metrics"><div className="metric"><div className="metric-top">UNIQUE SKU / SITE <Boxes size={19}/></div><strong>{summary?.total_skus.toLocaleString() ?? '—'}</strong><span>Tracked inventory records</span></div><div className="metric"><div className="metric-top">TOTAL UNITS <HardDrive size={19}/></div><strong>{summary?.total_units.toLocaleString() ?? '—'}</strong><span>Across all facilities</span></div><div className="metric alert-metric"><div className="metric-top">LOW-STOCK ALERTS <AlertTriangle size={19}/></div><strong>{summary?.low_stock_count.toLocaleString() ?? '—'}</strong><span>At or below reorder threshold</span></div><div className="metric"><div className="metric-top">INVENTORY VALUE <Server size={19}/></div><strong>{summary ? usd(summary.total_value) : '—'}</strong><span>Estimated from unit costs</span></div></div>
        <div className="dashboard-grid"><section className="panel sites"><div className="panel-head"><div><div className="eyebrow">SITE OVERVIEW</div><h2>Inventory distribution</h2></div><span className="count">{summary?.by_site.length || 0} sites</span></div>
          {empty ? <div className="empty"><PackageSearch size={32}/><strong>No inventory yet</strong><span>Import a sample file to populate the dashboard.</span></div> : <div className="bars">{summary!.by_site.map(s => <div className="bar-row" key={s.site}><div className="bar-head"><b>{s.site}</b><span>{s.units.toLocaleString()} units · {s.sku_count} SKUs</span></div><div className="bar-bg"><div className="bar-fill" style={{width:`${Math.max(2, 100 * s.units / Math.max(...summary!.by_site.map(v => v.units), 1))}%`}}/></div></div>)}</div>}
        </section><section className="panel import-panel" id="upload"><div className="panel-head"><div><div className="eyebrow">DATA INGESTION</div><h2>Import inventory</h2></div><UploadCloud size={21}/></div><div className={`drop ${dragging ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); void upload(e.dataTransfer.files[0]); }}><CloudUpload size={30}/><strong>Drop a CSV file here</strong><span>Required headers: sku, name, site, supplier, quantity, reorder_level, unit_cost</span><input ref={input} id="file" type="file" accept=".csv,text/csv" hidden onChange={e => void upload(e.target.files?.[0])}/><button className="btn btn-primary" onClick={() => input.current?.click()} disabled={uploading || !credential}>{uploading ? <Loader2 className="spin" size={16}/> : <UploadCloud size={16}/>} {uploading ? 'Importing…' : 'Choose CSV'}</button></div><div className="import-note"><FileText size={15}/> Maximum 2 MiB · 5,000 rows · Deduplicated by file hash</div></section></div>
        <section className="panel inventory" id="inventory"><div className="panel-head"><div><div className="eyebrow">PARTS CATALOG</div><h2>Inventory records</h2></div><button className="btn btn-ghost" onClick={() => void exportCsv()} disabled={!credential}><ArrowDownToLine size={16}/> Export low stock</button></div><div className="filters"><div className="searchbox"><Search size={17}/><input aria-label="Search SKU" placeholder="Search by SKU…" value={search} onChange={e => { setSearch(e.target.value); setOffset(0); }}/></div><select aria-label="Filter site" value={site} onChange={e => {setSite(e.target.value);setOffset(0);}}><option value="">All sites</option>{summary?.by_site.map(s => <option key={s.site} value={s.site}>{s.site}</option>)}</select><label className="checkbox"><input type="checkbox" checked={lowOnly} onChange={e => {setLowOnly(e.target.checked);setOffset(0);}}/> Low stock only</label></div><div className="table-wrap"><table><thead><tr><th>PART / SKU</th><th>SITE</th><th>SUPPLIER</th><th>AVAILABLE</th><th>REORDER AT</th><th>UNIT COST</th><th>STATUS</th></tr></thead><tbody>{parts?.items.map(p => <tr key={p.id}><td><b>{p.sku}</b><span className="secondary">{p.name}</span></td><td>{p.site}</td><td>{p.supplier}</td><td className="numeric">{p.quantity.toLocaleString()}</td><td className="numeric">{p.reorder_level.toLocaleString()}</td><td>{usd(p.unit_cost)}</td><td><span className={`tag ${p.low_stock ? 'low' : 'healthy'}`}>{p.low_stock ? 'Reorder' : 'Healthy'}</span></td></tr>)}</tbody></table>{!parts?.items.length && <div className="table-empty">{credential ? 'No matching inventory records.' : 'Enter your API key to load inventory.'}</div>}</div><div className="pager"><span>{parts ? `${parts.total ? offset + 1 : 0}–${Math.min(offset + 10, parts.total)} of ${parts.total}` : 'No records loaded'}</span><div><button className="btn btn-ghost" disabled={!parts || offset === 0} onClick={() => setOffset(v => Math.max(0, v - 10))}>Previous</button><button className="btn btn-ghost" disabled={!parts || offset + 10 >= parts.total} onClick={() => setOffset(v => v + 10)}>Next</button></div></div></section>
        <footer>InfraStock · Synthetic demonstration data · Built with FastAPI, PostgreSQL & AWS</footer>
      </main>
    </div>
  );
}
