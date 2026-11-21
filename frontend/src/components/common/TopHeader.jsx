import React, { useState, useRef, useEffect } from 'react';
import {
  Bell,
  LogOut,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Calendar,
  ChevronDown,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';

export default function TopHeader() {
  const { user, logout, isAdmin } = useAuth();
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();

  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const getNotifIcon = (type) => {
    switch (type) {
      case 'EXCEPTION_RESOLVED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />;
      case 'TICKET_REPLY':
        return <HelpCircle className="w-4 h-4 text-blue-500 shrink-0" />;
      default:
        return <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />;
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200/80 px-6 flex items-center justify-between sticky top-0 z-20 shadow-sm">
      {/* Left: Store & Environment Context */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span>Active Batch: <strong className="text-navy font-semibold">August 2026 Close (T+2 Settlement)</strong></span>
        </div>
      </div>

      {/* Right: Notifications & User Menu */}
      <div className="flex items-center gap-4">
        {/* Real-time Notification Bell */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="p-2 rounded-lg text-slate-500 hover:text-navy hover:bg-slate-100 transition-colors relative"
            title="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-rose-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50">
              <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
                <span className="text-xs font-bold font-outfit text-navy uppercase">
                  Alerts & Notifications
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-[11px] text-primary hover:underline font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                {notifications.length === 0 ? (
                  <div className="p-4 text-center text-xs text-slate-400">
                    No recent notifications.
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.notification_id}
                      onClick={() => !n.is_read && markAsRead(n.notification_id)}
                      className={`p-3 text-xs flex items-start gap-2.5 hover:bg-slate-50 transition-colors cursor-pointer ${
                        !n.is_read ? 'bg-primary/5' : ''
                      }`}
                    >
                      {getNotifIcon(n.type)}
                      <div className="flex-1 truncate">
                        <p className={`text-slate-800 ${!n.is_read ? 'font-semibold' : ''}`}>
                          {n.title}
                        </p>
                        <p className="text-slate-500 text-[11px] mt-0.5 line-clamp-2">{n.message}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Separator */}
        <div className="h-6 w-px bg-slate-200" />

        {/* User Profile & Logout */}
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-semibold text-navy leading-tight">{user?.name || 'User'}</p>
            <p className="text-[10px] font-medium text-slate-400 capitalize">
              {isAdmin ? 'Platform Admin' : user?.role?.toLowerCase() || 'Merchant'}
            </p>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-rose-50 hover:text-rose-600 border border-slate-200 rounded-lg transition-colors"
            title="Log Out"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
