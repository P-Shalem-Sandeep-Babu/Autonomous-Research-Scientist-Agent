"use strict";

"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Lock, Mail, User, Shield, FlaskConical, AlertCircle, KeyRound, CheckCircle2, ArrowLeft, Smartphone } from "lucide-react";

type AuthMode = "login" | "register" | "mfa" | "forgot_password" | "reset_password";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("researcher");
  const [mfaCode, setMfaCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // If user already holds a valid HttpOnly session cookie, redirect straight to dashboard
    api.getMe()
      .then(() => {
        router.push("/dashboard");
      })
      .catch(() => {
        // Not authenticated, stay on login page
      });
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (mode === "login") {
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);
        const res = await api.login(formData);

        if (res.mfa_required) {
          setMode("mfa");
          setSuccess("Two-factor authentication required. Enter your 6-digit code.");
        } else {
          router.push("/dashboard");
        }
      } else if (mode === "mfa") {
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);
        await api.login(formData, mfaCode);
        router.push("/dashboard");
      } else if (mode === "register") {
        await api.register({
          email,
          password,
          full_name: fullName,
          role,
        });
        setMode("login");
        setPassword("");
        setSuccess("Account successfully created. You can now log in.");
      } else if (mode === "forgot_password") {
        const res = await api.forgotPassword(email);
        setSuccess(res.message);
        if (res.reset_token) {
          setResetToken(res.reset_token);
        }
        setMode("reset_password");
      } else if (mode === "reset_password") {
        const res = await api.resetPassword(resetToken, newPassword);
        setSuccess(res.message);
        setMode("login");
        setPassword("");
        setNewPassword("");
        setResetToken("");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication request failed.";
      setError(msg);
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
        <div className="glass-card rounded-2xl p-8 border border-card-border shadow-2xl">
          <h2 className="text-xl font-bold mb-6 text-center text-slate-200">
            {mode === "login" && "Access Research Environment"}
            {mode === "register" && "Establish Researcher Profile"}
            {mode === "mfa" && "Two-Factor Verification"}
            {mode === "forgot_password" && "Recover Account Password"}
            {mode === "reset_password" && "Set New Password"}
          </h2>

          {error && (
            <div className="flex items-center gap-2 bg-error/10 border border-error/30 text-error text-sm p-3 rounded-lg mb-6">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm p-3 rounded-lg mb-6">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {mode === "register" && (
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

            {(mode === "login" || mode === "register" || mode === "forgot_password") && (
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
            )}

            {(mode === "login" || mode === "register") && (
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Password</label>
                  {mode === "login" && (
                    <button
                      type="button"
                      onClick={() => {
                        setMode("forgot_password");
                        setError("");
                        setSuccess("");
                      }}
                      className="text-xs text-primary/80 hover:text-primary transition"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
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
            )}

            {mode === "register" && (
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

            {mode === "mfa" && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Authenticator 6-Digit Code</label>
                <div className="relative">
                  <Smartphone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="123456"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm tracking-widest text-center text-lg font-mono"
                  />
                </div>
                <p className="text-xs text-slate-400">Open Google Authenticator, 1Password, or Authy to retrieve your temporary code.</p>
              </div>
            )}

            {mode === "reset_password" && (
              <>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Reset Token</label>
                  <div className="relative">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder="Paste reset token here"
                      className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm font-mono"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">New Password (min 8 chars)</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-4 py-2.5 rounded-lg glass-input text-sm"
                    />
                  </div>
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-primary hover:bg-primary/95 text-background font-semibold text-sm transition-all duration-200 shadow-lg shadow-primary/20 disabled:opacity-50 mt-2"
            >
              {loading ? (
                "Processing..."
              ) : mode === "login" ? (
                "Initiate Session"
              ) : mode === "register" ? (
                "Create Account"
              ) : mode === "mfa" ? (
                "Verify Code & Enter"
              ) : mode === "forgot_password" ? (
                "Request Reset Instructions"
              ) : (
                "Update Password"
              )}
            </button>
          </form>

          {/* Mode Switchers */}
          <div className="mt-6 pt-4 border-t border-slate-800 text-center">
            {mode === "login" && (
              <p className="text-xs text-slate-500">
                New to the platform?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("register");
                    setError("");
                    setSuccess("");
                  }}
                  className="text-primary hover:underline font-medium"
                >
                  Create credentials
                </button>
              </p>
            )}

            {mode === "register" && (
              <p className="text-xs text-slate-500">
                Already registered?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    setError("");
                    setSuccess("");
                  }}
                  className="text-primary hover:underline font-medium"
                >
                  Log in to existing
                </button>
              </p>
            )}

            {(mode === "forgot_password" || mode === "reset_password" || mode === "mfa") && (
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError("");
                  setSuccess("");
                }}
                className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Return to Login
              </button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
