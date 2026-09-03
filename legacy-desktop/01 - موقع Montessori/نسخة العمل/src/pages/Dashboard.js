import { getDashboardStats, getPayments, getStudents, getClasses } from '../utils/database';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area
} from 'recharts';
import { Users, DollarSign, AlertCircle, TrendingUp } from 'lucide-react';

const fmt = (n) => `SAR ${Number(n).toLocaleString()}`;

export default function Dashboard() {
  const stats = getDashboardStats();
  const payments = getPayments();
  const students = getStudents();
  const classes = getClasses();

  const overdue = payments.filter(p => p.status === 'pending');
  const overdueByStudent = overdue.reduce((acc, p) => {
    if (!acc[p.studentId]) acc[p.studentId] = { total: 0, months: 0 };
    acc[p.studentId].total += p.amount;
    acc[p.studentId].months += 1;
    return acc;
  }, {});

  const COLORS = ['#2d5016', '#7ab648', '#c4712a', '#3b82f6', '#8b5cf6', '#f59e0b'];

  return (
    <div>
      {/* Stat Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon green"><Users size={22} /></div>
          <div>
            <div className="stat-value">{stats.activeStudents}</div>
            <div className="stat-label">Active Students</div>
            <div className="stat-change up">↑ All enrolled</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon clay"><DollarSign size={22} /></div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.4rem' }}>{fmt(stats.totalRevenue)}</div>
            <div className="stat-label">Total Collected</div>
            <div className="stat-change up">↑ All time</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red"><AlertCircle size={22} /></div>
          <div>
            <div className="stat-value" style={{ fontSize: '1.4rem', color: '#dc2626' }}>{fmt(stats.pendingAmount)}</div>
            <div className="stat-label">Pending Payments</div>
            <div className="stat-change down">⚠ Needs attention</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon blue"><TrendingUp size={22} /></div>
          <div>
            <div className="stat-value">{stats.collectionData.at(-1)?.rate ?? 0}%</div>
            <div className="stat-label">Collection Rate</div>
            <div className="stat-change up">↑ This month</div>
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="charts-grid" style={{ marginBottom: 20 }}>
        {/* Revenue Chart */}
        <div className="card">
          <div className="card-header"><span className="card-title">Monthly Revenue</span></div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={stats.monthlyData}>
                <defs>
                  <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2d5016" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#2d5016" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={v => fmt(v)} />
                <Area type="monotone" dataKey="revenue" stroke="#2d5016" strokeWidth={2} fill="url(#rev)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Class Distribution */}
        <div className="card">
          <div className="card-header"><span className="card-title">By Class</span></div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={stats.classData}
                  cx="50%" cy="50%"
                  innerRadius={55} outerRadius={90}
                  dataKey="students"
                  nameKey="name"
                  paddingAngle={3}
                >
                  {stats.classData.map((entry, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend formatter={v => <span style={{ fontSize: '0.78rem' }}>{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Collection Rate */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><span className="card-title">Collection Rate by Month</span></div>
        <div className="card-body">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.collectionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0ebe0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={v => `${v}%`} />
              <Tooltip formatter={v => `${v}%`} />
              <Bar dataKey="rate" fill="#7ab648" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Overdue Table */}
      {overdue.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">⚠️ Overdue Payments</span>
            <span className="badge badge-danger">{overdue.length} pending</span>
          </div>
          <div className="card-body" style={{ padding: '12px 0 0' }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Class</th>
                    <th>Month</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {overdue.slice(0, 8).map(p => {
                    const student = students.find(s => s.id === p.studentId);
                    const cls = classes.find(c => c.id === student?.classId);
                    return (
                      <tr key={p.id} className="overdue-row">
                        <td><strong>{student?.name}</strong></td>
                        <td>{cls?.name}</td>
                        <td>{new Date(p.month + '-01').toLocaleDateString('en', { month: 'long', year: 'numeric' })}</td>
                        <td style={{ color: '#dc2626', fontWeight: 600 }}>{fmt(p.amount)}</td>
                        <td><span className="badge badge-danger">Pending</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
