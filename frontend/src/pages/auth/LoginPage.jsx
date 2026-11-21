import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('admin@razorpay-demo.com');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleDemoSelect = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMsg('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      const user = await login(email, password);
      if (user.role === 'ADMIN') {
        navigate('/admin');
      } else {
        navigate('/');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#F7F9FC]">
      {/* Left Branding Hero Panel */}
      <div className="md:w-1/2 bg-gradient-to-br from-[#161F30] via-[#0F4C75] to-[#1B262C] p-8 md:p-14 flex flex-col justify-between text-white relative overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-primary-light/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-primary/30 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center text-white backdrop-blur-md shadow-lg">
              <ShieldCheck className="w-6 h-6 text-primary-subtle" />
            </div>
            <div>
              <h1 className="text-xl font-bold font-outfit uppercase tracking-tight">AI Finance Controller</h1>
              <p className="text-xs text-slate-300 font-medium tracking-wide">Autonomous Financial Reconciliation Platform</p>
            </div>
          </div>

          <div className="space-y-6 max-w-lg mt-8">
            <h2 className="text-3xl md:text-4xl font-extrabold font-outfit leading-tight text-white">
              Continuous 3-Way Reconciliation & Exception Intelligence
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Automated high-volume matching across Merchant Order Ledgers, Razorpay Gateway settlements, and Bank Nodal Accounts with Google Gemini RAG assistance and Section 194-O TDS compliance.
            </p>

            <div className="space-y-3 pt-4">
              {[
                'Strict 7-Rule deterministic reconciliation engine',
                'Zero-leakage tax & Section 194-O TDS compliance audit',
                '7-Day rolling cash forecasting with T+2 committed queue',
                'Immutable audit logging & multi-tenant store scoping',
              ].map((bullet, idx) => (
                <div key={idx} className="flex items-center gap-2.5 text-xs text-slate-200">
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{bullet}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="relative z-10 pt-10 text-xs text-slate-400">
          <p>© 2026 AI Finance Controller. Production Enterprise Migration.</p>
        </div>
      </div>

      {/* Right Sign-In Form Container */}
      <div className="md:w-1/2 flex items-center justify-center p-6 md:p-14">
        <div className="w-full max-w-md bg-white rounded-2xl p-8 border border-slate-200/80 shadow-xl">
          <div className="mb-6">
            <h3 className="text-2xl font-bold font-outfit text-navy">Sign In to Controller</h3>
            <p className="text-xs text-slate-500 mt-1">
              Select a pre-seeded enterprise role or enter your credentials.
            </p>
          </div>

          {/* Quick Demo Credentials Selector */}
          <div className="mb-6 p-3 bg-slate-50 border border-slate-200 rounded-xl">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Select Demo Role:
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleDemoSelect('admin@razorpay-demo.com', 'admin123')}
                className={`px-2 py-1.5 text-xs font-semibold rounded-lg border transition-all text-center ${
                  email === 'admin@razorpay-demo.com'
                    ? 'bg-primary text-white border-primary shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                }`}
              >
                Platform Admin
              </button>
              <button
                type="button"
                onClick={() => handleDemoSelect('flipkart.delhi@merchant-demo.com', 'flipkart123')}
                className={`px-2 py-1.5 text-xs font-semibold rounded-lg border transition-all text-center ${
                  email === 'flipkart.delhi@merchant-demo.com'
                    ? 'bg-primary text-white border-primary shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                }`}
              >
                Flipkart Store
              </button>
              <button
                type="button"
                onClick={() => handleDemoSelect('amazon.delhi@merchant-demo.com', 'amazon123')}
                className={`px-2 py-1.5 text-xs font-semibold rounded-lg border transition-all text-center ${
                  email === 'amazon.delhi@merchant-demo.com'
                    ? 'bg-primary text-white border-primary shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                }`}
              >
                Amazon Store
              </button>
            </div>
          </div>

          {errorMsg && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  required
                  className="w-full text-xs pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-slate-800"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-navy uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full text-xs pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-slate-800"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-primary hover:bg-primary-dark text-white text-xs font-bold font-outfit uppercase tracking-wider rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Workspace'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Security Notice */}
          <div className="mt-6 pt-4 border-t border-slate-100 text-center">
            <p className="text-[11px] text-slate-400">
              Secured with Argon2id cryptographic hashing & JWT HttpOnly cookie session guards.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
