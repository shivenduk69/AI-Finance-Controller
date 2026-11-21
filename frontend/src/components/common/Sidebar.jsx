import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileSpreadsheet,
  AlertTriangle,
  CreditCard,
  Building2,
  Receipt,
  Sparkles,
  TrendingUp,
  Download,
  Settings,
  HelpCircle,
  Users,
  ShieldCheck,
  FolderGit2,
  Sliders,
  BellRing,
  BookOpen,
  History,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';

export default function Sidebar() {
  const { user, isAdmin } = useAuth();
  const { unreadCount } = useNotifications();

  const merchantLinks = [
    { to: '/', label: 'Overview & KPIs', icon: LayoutDashboard, end: true },
    { to: '/transactions', label: 'Transactions Ledger', icon: FileSpreadsheet },
    { to: '/exceptions', label: 'Exceptions Queue', icon: AlertTriangle },
    { to: '/settlements', label: 'Settlements Ledger', icon: CreditCard },
    { to: '/bank', label: 'Bank Reconciliation', icon: Building2 },
    { to: '/tax', label: 'Tax & TDS Compliance', icon: Receipt },
    { to: '/insights', label: 'AI Assistant Console', icon: Sparkles },
    { to: '/forecast', label: 'Cash Forecasting', icon: TrendingUp },
    { to: '/reports', label: 'Reports & Exports', icon: Download },
    { to: '/tickets', label: 'Support Helpdesk', icon: HelpCircle },
    { to: '/settings', label: 'Store Settings', icon: Settings },
  ];

  const adminLinks = [
    { to: '/admin', label: 'Platform Overview', icon: LayoutDashboard, end: true },
    { to: '/admin/merchants', label: 'Merchants Registry', icon: Building2 },
    { to: '/admin/stores', label: 'Stores Management', icon: FolderGit2 },
    { to: '/admin/transactions', label: 'Platform Transactions', icon: FileSpreadsheet },
    { to: '/admin/exceptions', label: 'Central Exceptions Desk', icon: AlertTriangle },
    { to: '/admin/settlements', label: 'Settlements Oversight', icon: CreditCard },
    { to: '/admin/tickets', label: 'Ticket Helpdesk Queue', icon: HelpCircle },
    { to: '/admin/notifications', label: 'Notifications & Alerts', icon: BellRing },
    { to: '/admin/ai', label: 'AI & RAG Ops', icon: Sparkles },
    { to: '/admin/kb', label: 'Knowledge Base Hub', icon: BookOpen },
    { to: '/admin/users', label: 'User Access Control', icon: Users },
    { to: '/admin/audit', label: 'Audit Trail Logs', icon: History },
    { to: '/admin/config', label: 'Platform Settings', icon: Sliders },
  ];

  const links = isAdmin ? adminLinks : merchantLinks;

  return (
    <aside className="w-64 min-h-screen bg-sidebar flex flex-col border-r border-sidebar-border shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-sidebar-border">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary to-primary-light flex items-center justify-center text-white shadow-md shadow-primary/20">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-tight text-white font-outfit uppercase">
            AI Finance
          </h1>
          <p className="text-[10px] text-slate-400 font-medium tracking-wider uppercase">
            Controller
          </p>
        </div>
      </div>

      {/* Role / Tenant Badge */}
      <div className="px-5 py-3 border-b border-sidebar-border/60 bg-sidebar-hover/40">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold tracking-wider uppercase text-slate-400">
            {isAdmin ? 'Platform Admin' : 'Store Portal'}
          </span>
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              isAdmin
                ? 'bg-amber-400/10 text-amber-300 border border-amber-400/20'
                : 'bg-primary/20 text-primary-subtle border border-primary/30'
            }`}
          >
            {user?.merchant_id ? user.merchant_id.toUpperCase() : 'ALL'}
          </span>
        </div>
        {user?.store_id && (
          <p className="text-[11px] text-slate-400 font-mono mt-1 truncate">
            Store: {user.store_id}
          </p>
        )}
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          {isAdmin ? 'System Modules' : 'Finance Views'}
        </div>
        {links.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-sidebar-active text-white shadow-sm font-semibold'
                    : 'text-slate-300 hover:bg-sidebar-hover hover:text-white'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0 opacity-80" />
              <span className="truncate">{item.label}</span>
              {item.to === '/exceptions' && unreadCount > 0 && (
                <span className="ml-auto px-1.5 py-0.2 bg-rose-500 text-white text-[10px] rounded-full font-bold">
                  {unreadCount}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Profile Info */}
      <div className="p-4 border-t border-sidebar-border bg-sidebar-hover/30 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary/30 text-primary-subtle border border-primary/40 flex items-center justify-center font-bold font-outfit uppercase">
            {user?.name ? user.name.slice(0, 2) : 'FC'}
          </div>
          <div className="truncate">
            <p className="text-white font-medium truncate">{user?.name || 'Authorized User'}</p>
            <p className="text-slate-400 text-[10px] truncate">{user?.email}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
