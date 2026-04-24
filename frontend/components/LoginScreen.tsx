"use client";

import { useState } from "react";

interface LoginScreenProps {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === "tuev" && password === "TuevSmartcal2026##!") {
      onLogin();
    } else {
      setError("Ungültige Anmeldedaten");
    }
  };

  return (
    <div className="h-screen flex items-center justify-center bg-gradient-to-br from-stone-50 via-blue-50/30 to-stone-100">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/60 p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#0046ad] to-[#003890] flex items-center justify-center shadow-lg shadow-blue-800/25 mb-4">
              <span className="text-white font-bold text-lg">SO</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900">Synapse OS</h1>
            <p className="text-sm text-slate-400 font-medium">for TÜV Süd</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                Benutzername
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => { setUsername(e.target.value); setError(""); }}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0046ad]/30 focus:border-[#0046ad] transition-all"
                placeholder="tuev"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                Passwort
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(""); }}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0046ad]/30 focus:border-[#0046ad] transition-all"
                placeholder="••••••"
              />
            </div>

            {error && (
              <p className="text-sm text-red-500 text-center">{error}</p>
            )}

            <button
              type="submit"
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#0046ad] to-[#003890] text-white text-sm font-semibold shadow-lg shadow-blue-800/25 hover:shadow-blue-800/40 transition-all"
            >
              Anmelden
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          Synapse OS for TÜV Süd
        </p>
      </div>
    </div>
  );
}
