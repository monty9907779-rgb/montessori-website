import { getPayments, getStudents, getClasses } from '../utils/database';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area
} from 'recharts';

const fmt = n => `SAR ${Number(n).toLocaleString()}`;
const COLORS = ['#2d5016', '#7ab648', '#c4712a', '#3b82f6', '#8b5cf6', '#f59e0b'];

export default function Reports() {
  const payments = getPayments();
  const students = getStudents();
  const classes = getClasses();

  // Revenue per month
  const monthlyMap = {};
  payments.forEach(p => {
    if (!monthlyMap[p.month]) monthlyMap[p.month] = { month: p.month, collected: 0, pending: 0 };
    if (p.status === 'paid') monthlyMap[p.month].collected += p.amount;
    else monthlyMap[p.month].pending += p.amount;
  });
  const monthlyData = Object.values(monthlyMap).sort((a, b) => a.month.localeCompare(b.month)).map(d => ({
    ...d,
    label: new Date(d.month + '-01').toLocaleDateString('en', { month: 'short', year: '2-digit' }),
  }));

  // Revenue per class
  const classRevenue = classes.map(cls => {
    const classStudents = students.filter(s => s.classId === cls.id).map(s => s.id);
    const collected = payments.filter(p => classStudents.includes(p.studentId) && p.status === 'paid').reduce((s, p) => s + p.amount, 0);
    const pending = payments.filter(p => classStudents.includes(p.studentId) && p.status === 'pending').reduce((s, p) => s + p.amount, 0);
    return { name: cls.name, collected, pending, color: cls.color };
  });

  // Payment method breakdown
  const methodCount = {};
  payments.filter(p => p.status === 'paid' && p.method).forEach(p => {
    methodCount[p.method] = (methodCount[p.method] || 0) + 1;
  });
  const methodData = Object.entries(methodCount).map(([name, value]) => ({ name: name.replace('_', ' '), value }));

  // Collection rate trend
  const rateData = monthlyData.map(d => ({
    label: d.label,
    rate: d.collected + d.pending > 0 ? Math.round((d.collected / (d.collected + d.pending)) * 100) : 0,
  }));

  const totalCollected = payments.filter(p => p.status === 'paid').reduce((s, p) => s + p.amount, 0);
  const totalPending = payments.filter(p => p.status === 'pending').reduce((s, p) => s + p.amount, 0);
  const avgMonthly = monthlyData.length ? Math.round(totalCollected / monthlyData.filter(d => d.collected > 0).length) : 0;

  return (
    <div>
      {/* KPI row */}
      <div className="stat-grid" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Collected (All Time)', value: fmt(totalCollected), color: 'var(--success)' },
          { label: 'Total Pending', value: fmt(totalPending), color: '#dc2626' },
          { label: 'Avg Monthly Revenue', value: fmt(avgMonthly), color: 'var(--green-main)' },
          { label: 'Active Students', value: students.filter(s => s.status === 'active').length, color: 'var(--green-deep)' },
        ].map(({ label, value, color }) => (
          <div key={label} className="stat-card">
            <div style={{ width: '100%' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color, fontWeight: 700 }}>{value}</div>
              <div style={{ color: 'var(--text-light)', fontSize: '0.78rem', marginTop: 4 }}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Collected vs Pending */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><span className="card-title">Collected vs Pending by Month</span></div>
        <div className="card-body">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={v => fmt(v)} />
              <Legend />
              <Bar dataKey="collected" name="Collected" fill="#2d5016" radius={[4,4,0,0]} />
              <Bar dataKey="pending" name="Pending" fill="#fca5a5" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="charts-row">
        {/* Revenue by Class */}
        <div className="card">
          <div className="card-header"><span className="card-title">Revenue by Class</span></div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={classRevenue} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
                <Tooltip formatter={v => fmt(v)} />
                <Bar dataKey="collected" name="Collected" radius={[0,4,4,0]}>
                  {classRevenue.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Payment Methods */}
        <div className="card">
          <div className="card-header"><span className="card-title">Payment Methods</span></div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={methodData} cx="50%" cy="50%" outerRadius={80} dataKey="value" nameKey="name" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                  {methodData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Collection Rate Trend */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header"><span className="card-title">Collection Rate Trend</span></div>
        <div className="card-body">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={rateData}>
              <defs>
                <linearGradient id="rate" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7ab648" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#7ab648" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={v => `${v}%`} />
              <Tooltip formatter={v => `${v}%`} />
              <Area type="monotone" dataKey="rate" stroke="#7ab648" strokeWidth={2} fill="url(#rate)" name="Collection Rate" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
