import { useCallback, useEffect, useState } from 'react';
import { Activity, ArrowUpRight, Box, BusFront, Check, CircleDollarSign, ClipboardList, LayoutDashboard, LogOut, Menu, Plus, Search, ShieldCheck, Truck, Users, Wrench, X } from 'lucide-react';
import { login, request, setToken } from './api';

const navItems = [
  ['Overview', LayoutDashboard], ['Shipments', Box], ['Trips', Truck], ['Fleet', BusFront], ['Drivers', Users], ['Maintenance', Wrench], ['Expenses', CircleDollarSign],
];
const emptyData = { dashboard: {}, shipments: [], trips: [], vehicles: [], drivers: [], maintenance: [], expenses: [] };
const fmtMoney = (v) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v || 0);

function App() {
  const [tokenReady, setTokenReady] = useState(Boolean(localStorage.getItem('bea_token')));
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('Overview');
  const [data, setData] = useState(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [dialog, setDialog] = useState(false);
  const [query, setQuery] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [dashboard, shipments, trips, vehicles, drivers, maintenance, expenses] = await Promise.all([
        request('/dashboard'), request('/shipments'), request('/trips'), request('/vehicles'), request('/drivers'), request('/maintenance'), request('/expenses'),
      ]);
      setData({ dashboard, shipments, trips, vehicles, drivers, maintenance, expenses });
      setError('');
    } catch (err) {
      setError(err.message);
      if (/token|credential|unauthorized/i.test(err.message)) { setToken(''); setTokenReady(false); }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!tokenReady) { setLoading(false); return; }
    request('/auth/me').then(setUser).then(loadData).catch((err) => { setError(err.message); setToken(''); setTokenReady(false); setLoading(false); });
  }, [tokenReady, loadData]);

  const flash = (message) => { setToast(message); window.setTimeout(() => setToast(''), 2800); };
  const onLogin = async (email, password) => {
    try { const profile = await login(email, password); setUser({ name: profile.name, role: profile.role }); setTokenReady(true); }
    catch (err) { setError(err.message); }
  };
  const save = async (path, payload, method = 'POST') => {
    try { await request(path, { method, body: JSON.stringify(payload) }); setDialog(false); await loadData(); flash('Changes saved'); }
    catch (err) { setError(err.message); }
  };
  const updateTrip = async (trip, update) => {
    try { await request(`/trips/${trip.id}/${update.kind}`, { method: update.method || 'POST', body: JSON.stringify(update.payload) }); await loadData(); flash(update.message); }
    catch (err) { setError(err.message); }
  };

  if (!tokenReady) return <Login onLogin={onLogin} error={error} />;
  const d = data.dashboard;
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Truck size={19} /></div><div><strong>Northstar</strong><span>LOGISTICS GROUP</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{navItems.map(([name, Icon]) => <button key={name} className={`nav-item ${page === name ? 'active' : ''}`} onClick={() => setPage(name)}><Icon size={18} /><span>{name}</span>{name === 'Shipments' && <small>{data.shipments.length}</small>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="secure-note"><ShieldCheck size={17} /><span>Secure workspace</span></div><div className="profile"><div className="avatar">{(user?.name || 'DA').split(' ').map(x => x[0]).slice(0, 2).join('')}</div><div className="profile-copy"><strong>{user?.name || 'Administrator'}</strong><span>{user?.role || 'admin'}</span></div><button className="icon-button logout" title="Sign out" onClick={() => { setToken(''); setTokenReady(false); setUser(null); }}><LogOut size={16} /></button></div></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="breadcrumb"><span>Operations</span><span className="slash">/</span><strong>{page}</strong></div><div className="top-actions"><label className="search-box"><Search size={16} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search current view" /></label><button className="avatar small-avatar">{(user?.name || 'DA').split(' ').map(x => x[0]).slice(0, 2).join('')}</button></div></header>
      <div className="content">
        {error && <div className="alert"><span>{error}</span><button className="icon-button" onClick={() => setError('')}><X size={16} /></button></div>}
        {loading ? <div className="loading"><span className="spinner" /> Loading operations data…</div> : <>
          {page === 'Overview' && <Dashboard stats={d} data={data} onPage={setPage} />}
          {page === 'Shipments' && <Shipments rows={filterRows(data.shipments, query, ['tracking_number', 'customer_name', 'origin', 'destination', 'status'])} onAdd={() => setDialog('shipment')} canCreate={['admin', 'logistics_manager'].includes(user?.role)} />}
          {page === 'Trips' && <Trips data={data} onAdd={() => setDialog('trip')} onUpdate={updateTrip} canSchedule={['admin', 'logistics_manager'].includes(user?.role)} canManage={['admin', 'logistics_manager', 'fleet_manager'].includes(user?.role)} />}
          {page === 'Fleet' && <Fleet rows={filterRows(data.vehicles, query, ['plate_number', 'model', 'status'])} onAdd={() => setDialog('vehicle')} canCreate={['admin', 'fleet_manager'].includes(user?.role)} />}
          {page === 'Drivers' && <Drivers rows={filterRows(data.drivers, query, ['name', 'license_number', 'phone', 'status'])} onAdd={() => setDialog('driver')} canCreate={['admin', 'fleet_manager'].includes(user?.role)} />}
          {page === 'Maintenance' && <Maintenance rows={filterRows(data.maintenance, query, ['description', 'status'])} vehicles={data.vehicles} onAdd={() => setDialog('maintenance')} canManage={['admin', 'fleet_manager'].includes(user?.role)} onComplete={async (id) => { try { await request(`/maintenance/${id}/complete`, { method: 'PATCH' }); await loadData(); flash('Service marked complete'); } catch (err) { setError(err.message); } }} />}
          {page === 'Expenses' && <Expenses rows={filterRows(data.expenses, query, ['category', 'notes'])} onAdd={() => setDialog('expense')} canCreate={['admin', 'logistics_manager', 'fleet_manager'].includes(user?.role)} />}
        </>}
      </div>
    </main>
    {dialog && <Modal kind={dialog} data={data} onClose={() => setDialog(false)} onSave={save} />}
    {toast && <div className="toast"><Check size={16} />{toast}</div>}
  </div>;
}

function Login({ onLogin, error }) {
  const [email, setEmail] = useState('admin@bea.local'); const [password, setPassword] = useState('Admin123!');
  return <div className="login-page"><div className="login-brand"><div className="brand-mark"><Truck size={20} /></div><div><strong>Northstar</strong><span>LOGISTICS GROUP</span></div></div><form className="login-card" onSubmit={e => { e.preventDefault(); onLogin(email, password); }}><div className="eyebrow">OPERATIONS PLATFORM</div><h1>Welcome back</h1><p>Sign in to manage your logistics operations.</p>{error && <div className="alert">{error}</div>}<label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label><label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label><button className="primary full">Sign in <ArrowUpRight size={16} /></button><div className="demo-info">Demo account <strong>admin@bea.local</strong><span>Admin123!</span></div></form><span className="login-footer">Enterprise fleet and shipment management</span></div>;
}

function PageHeading({ eyebrow, title, subtitle, action }) { return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action && <button className="primary" onClick={action.onClick}><Plus size={17} />{action.label}</button>}</div>; }

function Dashboard({ stats, data, onPage }) {
  const metrics = [
    { label: 'Total shipments', value: stats.shipments || 0, Icon: Box, tint: 'lavender', foot: 'Across all statuses' },
    { label: 'In transit', value: stats.in_transit || 0, Icon: Activity, tint: 'blue', foot: 'Currently on the road' },
    { label: 'Available vehicles', value: stats.available_vehicles || 0, Icon: BusFront, tint: 'green', foot: 'Ready for assignment' },
    { label: 'Operating expenses', value: fmtMoney(stats.expense_total), Icon: CircleDollarSign, tint: 'orange', foot: 'Recorded to date' },
  ];
  const latest = data.shipments.slice(0, 5);
  return <><PageHeading eyebrow="MONDAY, NOVEMBER 2, 2026" title="Operations overview" subtitle="A clear view of today’s shipments, fleet, and delivery activity." action={{ label: 'New shipment', onClick: () => onPage('Shipments') }} />
    <div className="metrics">{metrics.map(({ label, value, Icon, tint, foot }) => <div className="metric-card" key={label}><div className="metric-top"><span>{label}</span><span className={`metric-icon ${tint}`}><Icon size={18} /></span></div><strong className="metric-value">{value}</strong><span className="metric-foot">{foot}</span></div>)}</div>
    <div className="overview-grid"><section className="panel recent-panel"><div className="panel-heading"><div><h2>Recent shipments</h2><p>Latest activity across your network</p></div><button className="text-link" onClick={() => onPage('Shipments')}>View all <ArrowUpRight size={14} /></button></div><ShipmentTable rows={latest} compact /></section><section className="panel capacity-panel"><div className="panel-heading"><div><h2>Fleet availability</h2><p>Resources ready for dispatch</p></div><button className="more-button"><Menu size={17} /></button></div><div className="capacity-number"><strong>{stats.available_vehicles || 0}</strong><span>vehicles available</span></div><div className="capacity-bar"><i style={{ width: `${Math.min(100, data.vehicles.length ? (stats.available_vehicles / data.vehicles.length) * 100 : 0)}%` }} /></div><div className="capacity-legend"><span><i className="dot green-dot" />Available <b>{stats.available_vehicles || 0}</b></span><span><i className="dot gray-dot" />In use <b>{Math.max(0, data.vehicles.length - (stats.available_vehicles || 0))}</b></span></div><div className="capacity-divider" /><div className="mini-stats"><div><span>Drivers available</span><strong>{stats.available_drivers || 0}</strong></div><div><span>Open maintenance</span><strong>{stats.open_maintenance || 0}</strong></div></div></section></div>
  </>;
}

function SectionTitle({ title, count }) { return <div className="section-title"><h2>{title}</h2>{count !== undefined && <span>{count} records</span>}</div>; }
function Shipments({ rows, onAdd, canCreate }) { return <><PageHeading eyebrow="ORDER MANAGEMENT" title="Shipments" subtitle="Create, monitor, and trace customer deliveries." action={canCreate ? { label: 'Create shipment', onClick: onAdd } : null} /><section className="panel table-panel"><SectionTitle title="Shipment register" count={rows.length} /><ShipmentTable rows={rows} /></section></>; }
function ShipmentTable({ rows, compact = false }) { return <div className="table-wrap"><table><thead><tr><th>Tracking ID</th><th>Customer</th><th>Route</th><th>Status</th><th>Created</th></tr></thead><tbody>{rows.length ? rows.map(s => <tr key={s.id}><td><strong className="tracking">{s.tracking_number}</strong></td><td>{s.customer_name}</td><td><span className="route">{s.origin}<ArrowUpRight size={12} />{s.destination}</span></td><td><Status value={s.status} /></td><td>{date(s.created_at)}</td></tr>) : <Empty colSpan="5" text="No shipments found" />}</tbody></table></div>; }
function Trips({ data, onAdd, onUpdate, canSchedule, canManage }) {
  const [selection, setSelection] = useState({});
  const readyVehicles = data.vehicles.filter(v => v.status === 'available'); const readyDrivers = data.drivers.filter(v => v.status === 'available');
  return <><PageHeading eyebrow="DISPATCH" title="Trips" subtitle="Assign resources and update delivery progress." action={canSchedule ? { label: 'Schedule trip', onClick: onAdd } : null} /><section className="panel table-panel"><SectionTitle title="Trip schedule" count={data.trips.length} /><div className="table-wrap"><table><thead><tr><th>Trip</th><th>Shipment</th><th>Vehicle</th><th>Driver</th><th>Status</th><th>Next action</th></tr></thead><tbody>{data.trips.length ? data.trips.map(t => { const s = data.shipments.find(x => x.id === t.shipment_id); const v = data.vehicles.find(x => x.id === t.vehicle_id); const d = data.drivers.find(x => x.id === t.driver_id); const selected = selection[t.id] || {}; return <tr key={t.id}><td><strong>TR-{String(t.id).padStart(4, '0')}</strong></td><td>{s?.tracking_number || `Shipment ${t.shipment_id}`}</td><td>{v?.plate_number || 'Unassigned'}</td><td>{d?.name || 'Unassigned'}</td><td><Status value={t.status} /></td><td><div className="row-actions">{canManage && !t.vehicle_id && readyVehicles.length && readyDrivers.length ? <><select className="inline-select" aria-label="Choose vehicle" value={selected.vehicle_id || ''} onChange={e => setSelection({ ...selection, [t.id]: { ...selected, vehicle_id: e.target.value } })}><option value="">Vehicle…</option>{readyVehicles.map(x => <option key={x.id} value={x.id}>{x.plate_number}</option>)}</select><select className="inline-select" aria-label="Choose driver" value={selected.driver_id || ''} onChange={e => setSelection({ ...selection, [t.id]: { ...selected, driver_id: e.target.value } })}><option value="">Driver…</option>{readyDrivers.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select><button className="small-action" disabled={!selected.vehicle_id || !selected.driver_id} onClick={() => onUpdate(t, { kind: 'assign', payload: { vehicle_id: Number(selected.vehicle_id), driver_id: Number(selected.driver_id) }, message: 'Vehicle and driver assigned' })}>Assign</button></> : canManage && t.status === 'assigned' ? <button className="small-action" onClick={() => onUpdate(t, { kind: 'status', method: 'PATCH', payload: { status: 'in_transit' }, message: 'Trip started' })}>Start trip</button> : canManage && t.status === 'in_transit' ? <button className="small-action done" onClick={() => onUpdate(t, { kind: 'status', method: 'PATCH', payload: { status: 'delivered' }, message: 'Delivery completed' })}>Mark delivered</button> : <span className="muted">—</span>}</div></td></tr>; }) : <Empty colSpan="6" text="No trips scheduled yet" />}</tbody></table></div></section><p className="helper-note">Selecting resources reserves them for this trip. Completing or cancelling the trip releases them.</p></>;
}
function Fleet({ rows, onAdd, canCreate }) { return <><PageHeading eyebrow="RESOURCE MANAGEMENT" title="Fleet" subtitle="Register vehicles and keep availability current." action={canCreate ? { label: 'Add vehicle', onClick: onAdd } : null} /><section className="panel table-panel"><SectionTitle title="Vehicle register" count={rows.length} /><div className="table-wrap"><table><thead><tr><th>Vehicle</th><th>Model</th><th>Capacity</th><th>Status</th></tr></thead><tbody>{rows.length ? rows.map(v => <tr key={v.id}><td><strong>{v.plate_number}</strong></td><td>{v.model}</td><td>{Number(v.capacity_kg).toLocaleString()} kg</td><td><Status value={v.status} /></td></tr>) : <Empty colSpan="4" text="No vehicles registered" />}</tbody></table></div></section></>; }
function Drivers({ rows, onAdd, canCreate }) { return <><PageHeading eyebrow="PEOPLE" title="Drivers" subtitle="Maintain your driver directory and current availability." action={canCreate ? { label: 'Add driver', onClick: onAdd } : null} /><section className="panel table-panel"><SectionTitle title="Driver directory" count={rows.length} /><div className="table-wrap"><table><thead><tr><th>Driver</th><th>License number</th><th>Phone</th><th>Status</th></tr></thead><tbody>{rows.length ? rows.map(d => <tr key={d.id}><td><strong>{d.name}</strong></td><td>{d.license_number}</td><td>{d.phone || '—'}</td><td><Status value={d.status} /></td></tr>) : <Empty colSpan="4" text="No drivers registered" />}</tbody></table></div></section></>; }
function Maintenance({ rows, vehicles, onAdd, canManage, onComplete }) { return <><PageHeading eyebrow="FLEET CARE" title="Maintenance" subtitle="Record preventive and corrective service work." action={canManage ? { label: 'Record service', onClick: onAdd } : null} /><section className="panel table-panel"><SectionTitle title="Service records" count={rows.length} /><div className="table-wrap"><table><thead><tr><th>Vehicle</th><th>Service details</th><th>Cost</th><th>Date</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.length ? rows.map(m => <tr key={m.id}><td>{vehicles.find(v => v.id === m.vehicle_id)?.plate_number || `Vehicle ${m.vehicle_id}`}</td><td>{m.description}</td><td>{fmtMoney(m.cost)}</td><td>{date(m.service_date)}</td><td><Status value={m.status} /></td><td>{m.status === 'completed' || !canManage ? <span className="muted">—</span> : <button className="small-action done" onClick={() => onComplete(m.id)}>Complete service</button>}</td></tr>) : <Empty colSpan="6" text="No maintenance records" />}</tbody></table></div></section></>; }
function Expenses({ rows, onAdd, canCreate }) { const total = rows.reduce((s, r) => s + Number(r.amount), 0); return <><PageHeading eyebrow="FINANCE" title="Expenses" subtitle="Capture fleet and trip operating costs." action={canCreate ? { label: 'Add expense', onClick: onAdd } : null} /><div className="expense-summary panel"><span>Recorded expenses</span><strong>{fmtMoney(total)}</strong><small>{rows.length} entries</small></div><section className="panel table-panel"><SectionTitle title="Expense register" count={rows.length} /><div className="table-wrap"><table><thead><tr><th>Category</th><th>Notes</th><th>Amount</th><th>Date</th></tr></thead><tbody>{rows.length ? rows.map(e => <tr key={e.id}><td><strong>{e.category}</strong></td><td>{e.notes || '—'}</td><td>{fmtMoney(e.amount)}</td><td>{date(e.incurred_at)}</td></tr>) : <Empty colSpan="4" text="No expenses recorded" />}</tbody></table></div></section></>; }

function Modal({ kind, data, onClose, onSave }) {
  const [form, setForm] = useState({});
  const fields = {
    shipment: { title: 'Create shipment', path: '/shipments', inputs: [['customer_name', 'Customer name', 'text'], ['origin', 'Origin', 'text'], ['destination', 'Destination', 'text'], ['description', 'Package description', 'text']] },
    vehicle: { title: 'Add vehicle', path: '/vehicles', inputs: [['plate_number', 'Plate number', 'text'], ['model', 'Vehicle model', 'text'], ['capacity_kg', 'Capacity (kg)', 'number']] },
    driver: { title: 'Add driver', path: '/drivers', inputs: [['name', 'Driver name', 'text'], ['license_number', 'License number', 'text'], ['phone', 'Phone number', 'tel']] },
    trip: { title: 'Schedule trip', path: '/trips', inputs: [['shipment_id', 'Shipment', 'select', data.shipments.filter(s => !['delivered'].includes(s.status)).map(s => [s.id, `${s.tracking_number} · ${s.destination}`])]] },
    maintenance: { title: 'Record maintenance', path: '/maintenance', inputs: [['vehicle_id', 'Vehicle', 'select', data.vehicles.map(v => [v.id, `${v.plate_number} · ${v.model}`])], ['description', 'Service details', 'text'], ['cost', 'Service cost (₹)', 'number']] },
    expense: { title: 'Add expense', path: '/expenses', inputs: [['category', 'Category', 'text'], ['amount', 'Amount (₹)', 'number'], ['notes', 'Notes', 'text']] },
  }[kind];
  return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}><form className="modal" onSubmit={e => { e.preventDefault(); onSave(fields.path, Object.fromEntries(Object.entries(form).map(([k, v]) => [k, ['vehicle_id', 'shipment_id', 'capacity_kg', 'cost', 'amount'].includes(k) ? Number(v || 0) : v]))); }}><div className="modal-head"><div><span className="eyebrow">OPERATIONS</span><h2>{fields.title}</h2></div><button type="button" className="icon-button" onClick={onClose}><X size={19} /></button></div><div className="modal-fields">{fields.inputs.map(([key, label, type, options]) => <label key={key}>{label}{type === 'select' ? <select value={form[key] || ''} onChange={e => setForm({ ...form, [key]: e.target.value })} required><option value="">Select…</option>{options.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select> : <input type={type} min={type === 'number' ? '0.01' : undefined} step={type === 'number' ? 'any' : undefined} value={form[key] || ''} onChange={e => setForm({ ...form, [key]: e.target.value })} required={key !== 'description' && key !== 'notes'} />}</label>)}</div><div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary"><Plus size={16} />Save record</button></div></form></div>;
}

function Status({ value }) { const v = (value || 'pending').replaceAll('_', ' '); return <span className={`status status-${v.replaceAll(' ', '-')}`}><i />{v}</span>; }
function Empty({ colSpan, text }) { return <tr><td colSpan={colSpan} className="empty-cell"><div className="empty-icon"><ClipboardList size={21} /></div><strong>{text}</strong><span>Records will appear here once added.</span></td></tr>; }
function date(value) { return value ? new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'; }
function filterRows(rows, query, keys) { if (!query.trim()) return rows; const q = query.toLowerCase(); return rows.filter(row => keys.some(k => String(row[k] || '').toLowerCase().includes(q))); }

export default App;
