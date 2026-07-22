"use strict";

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, getToken } from "@/lib/api";
import { Lock, Mail, User, Shield, FlaskConical, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("researcher");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // If already logged in, redirect to dashboard
    if (getToken()) {
      router.push("/dashboard");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Build URL-encoded form data for OAuth2
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);
        await api.login(formData);
        router.push("/dashboard");
      } else {
        await api.register({
          email,
          password,
          full_name: fullName,
          role,
        });
        setIsLogin(true);
        setPassword("");
        setError("Account created successfully! Please log in.");
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Check your inputs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen w-full flex items-center justify-center relative overflow-hidden bg-background tech-grid px-4">
      {/* Dynamic Background Glows */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] rounded-full bg-primary/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full bg-accent/10 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md z-10">
        {/* Logo and title */}
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 bg-primary/10 rounded-2xl border border-primary/30 mb-3 pulse-primary">
            <FlaskConical className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight glow-text-cyan text-center">ARSA</h1>
          <p className="text-sm text-slate-400 mt-1">Autonomous Research Scientist Agent</p>
        </div>

        {/* Auth Box */}
        <div className="glass-card rounded-2xl p-8 border border-card-border">
          <h2 className="text-xl font-bold mb-6 text-center text-slate-200">
            {isLogin ? "Access Research Environment" : "Establish Researcher Profile"}
          </h2>

          {error && (
            <div className="flex items-center gap-2 bg-error/10 border border-error/30 text-error text-sm p-3 rounded-lg mb-6">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Dr. Sarah Jenkins"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="researcher@institute.edu"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm"
                />
              </div>
            </div>

            {!isLogin && (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Platform Role</label>
                <div className="relative">
                  <Shield className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm appearance-none cursor-pointer"
                  >
                    <option value="researcher">Researcher</option>
                    <option value="supervisor">Supervisor</option>
                  </select>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-primary hover:bg-primary/95 text-background font-semibold text-sm transition-all duration-200 shadow-lg shadow-primary/20 disabled:opacity-50 mt-2"
            >
              {loading ? "Authenticating..." : isLogin ? "Initiate Session" : "Create Account"}
            </button>
          </form>

          {/* Toggle link */}
          <p className="text-center text-xs text-slate-500 mt-6">
            {isLogin ? "New to the platform?" : "Already registered?"}{" "}
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setError("");
              }}
              className="text-primary hover:underline font-medium"
            >
              {isLogin ? "Create credentials" : "Log in to existing"}
            </button>
          </p>
        </div>
      </div>
    </main>
  );
}
