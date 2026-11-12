import { FormEvent, ReactNode, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, CheckCircle2, Eye, EyeOff, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "./api";
import { useAuth, usePreferences } from "./store";
import i18n from "./i18n";

function messageFor(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function AuthShell({ children }: { children: ReactNode }) {
  const { theme, toggleTheme, uiLanguage, setUiLanguage } = usePreferences();
  const { t } = useTranslation();
  const nextLanguage = uiLanguage === "en" ? "mm" : "en";
  return <div className="min-h-screen bg-mist px-4 py-5 dark:bg-[#0d1728] sm:px-8">
    <header className="mx-auto flex max-w-6xl items-center justify-between">
      <Link to="/" className="flex items-center gap-2 font-extrabold tracking-tight"><span className="grid h-9 w-9 place-items-center rounded-xl bg-navy text-white shadow-lg shadow-blue-900/15"><Sparkles size={18} /></span><span>{t("appName")}</span></Link>
      <div className="flex items-center gap-1"><button aria-label={t("toggleTheme")} onClick={toggleTheme} className="rounded-xl p-2.5 text-slate-500 hover:bg-white dark:hover:bg-slate-800">{theme === "light" ? "☾" : "☀"}</button><button aria-label={t("switchLanguage")} onClick={() => { setUiLanguage(nextLanguage); void i18n.changeLanguage(nextLanguage); }} className="rounded-xl px-3 py-2 text-sm font-bold text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-800">{uiLanguage === "en" ? "EN" : "MM"}</button></div>
    </header>
    <main className="mx-auto flex min-h-[calc(100vh-80px)] max-w-6xl items-center justify-center py-10">{children}</main>
  </div>;
}

function AuthCard({ eyebrow, title, copy, children }: { eyebrow: string; title: string; copy: string; children: ReactNode }) {
  return <section className="w-full max-w-md rounded-[28px] border border-slate-200 bg-white p-6 shadow-soft dark:border-slate-700 dark:bg-[#13233b] sm:p-9"><p className="mb-3 text-xs font-bold uppercase tracking-[.18em] text-blue-600">{eyebrow}</p><h1 className="text-3xl font-extrabold tracking-tight">{title}</h1><p className="subtle mt-2 text-sm leading-6">{copy}</p>{children}</section>;
}

function AuthField({ label, type = "text", value, onChange, autoComplete, error, placeholder }: { label: string; type?: string; value: string; onChange: (value: string) => void; autoComplete?: string; error?: string; placeholder?: string }) {
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";
  return <label className="block"><span className="field-label">{label}</span><span className="relative block"><input type={isPassword && visible ? "text" : type} value={value} onChange={(event) => onChange(event.target.value)} autoComplete={autoComplete} placeholder={placeholder} aria-invalid={Boolean(error)} className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-100 dark:border-slate-700 dark:bg-[#101d31] dark:text-white dark:focus:ring-blue-950" />{isPassword && <button type="button" aria-label={visible ? "Hide password" : "Show password"} onClick={() => setVisible(!visible)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">{visible ? <EyeOff size={16} /> : <Eye size={16} />}</button>}</span>{error && <span role="alert" className="mt-1.5 block text-xs font-semibold text-rose-600">{error}</span>}</label>;
}

function SubmitButton({ children, busy }: { children: ReactNode; busy: boolean }) {
  return <button type="submit" disabled={busy} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm font-bold text-white transition hover:bg-blue-900 disabled:cursor-not-allowed disabled:opacity-50">{busy ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : <ArrowRight size={16} />}{children}</button>;
}

function FormError({ error }: { error: string }) { return <div role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm font-semibold text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">{error}</div>; }

export function SignInPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setUser = useAuth((state) => state.setUser);
  const currentUser = useAuth((state) => state.user);
  const clearLocalLibrary = usePreferences((state) => state.clearLocalLibrary);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!email.includes("@") || !password) { setError(t("validCredentials")); return; } setBusy(true); try { const response = await api.login({ email, password }); if (currentUser && currentUser.id !== response.user.id) clearLocalLibrary(); setUser(response.user); navigate("/dashboard", { replace: true }); } catch (reason) { setError(messageFor(reason)); } finally { setBusy(false); } };
  return <AuthShell><AuthCard eyebrow={t("signInEyebrow")} title={t("signIn")} copy={t("signInCopy")}><form className="mt-7 space-y-4" onSubmit={submit} noValidate><AuthField label={t("email")} value={email} onChange={setEmail} autoComplete="email" placeholder="you@example.com" /><AuthField label={t("password")} type="password" value={password} onChange={setPassword} autoComplete="current-password" />{error && <FormError error={error} />}<SubmitButton busy={busy}>{t("signIn")}</SubmitButton></form><div className="mt-5 flex justify-between gap-3 text-xs font-bold"><Link className="text-blue-600 hover:underline" to="/auth/forgot-password">{t("forgotPassword")}</Link><Link className="text-slate-500 hover:text-navy dark:text-slate-300" to="/auth/register">{t("createAccount")}</Link></div></AuthCard></AuthShell>;
}

export function RegisterPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!email.includes("@") || password.length < 8 || password.length > 12 || password !== confirm) { setError(password !== confirm ? t("passwordsMustMatch") : t("passwordRule")); return; } setBusy(true); try { await api.register({ email, password }); setDone(true); } catch (reason) { setError(messageFor(reason)); } finally { setBusy(false); } };
  if (done) return <AuthShell><AuthCard eyebrow={t("registration")} title={t("checkYourEmail")} copy={t("verificationSent")}><div className="mt-7 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"><CheckCircle2 className="mb-3" /><p className="text-sm font-semibold">{t("verificationSentDetail")}</p></div><Link to="/auth/sign-in" className="mt-6 inline-flex text-sm font-bold text-blue-600 hover:underline">{t("backToSignIn")}</Link></AuthCard></AuthShell>;
  return <AuthShell><AuthCard eyebrow={t("registration")} title={t("createAccount")} copy={t("registerCopy")}><form className="mt-7 space-y-4" onSubmit={submit} noValidate><AuthField label={t("email")} value={email} onChange={setEmail} autoComplete="email" placeholder="you@example.com" /><AuthField label={t("password")} type="password" value={password} onChange={setPassword} autoComplete="new-password" /><AuthField label={t("confirmPassword")} type="password" value={confirm} onChange={setConfirm} autoComplete="new-password" />{error && <FormError error={error} />}<p className="text-xs leading-5 text-slate-500 dark:text-slate-400">{t("passwordRule")}</p><SubmitButton busy={busy}>{t("createAccount")}</SubmitButton></form><p className="mt-5 text-center text-xs font-semibold text-slate-500">{t("alreadyHaveAccount")} <Link className="text-blue-600 hover:underline" to="/auth/sign-in">{t("signIn")}</Link></p></AuthCard></AuthShell>;
}

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "done">("idle");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!token && !email.includes("@")) { setError(t("validCredentials")); return; } setBusy(true); try { if (token) { await api.verifyEmail(token); setStatus("done"); } else { await api.resendVerification(email); setStatus("done"); } } catch (reason) { setError(messageFor(reason)); } finally { setBusy(false); } };
  return <AuthShell><AuthCard eyebrow={t("verification")} title={status === "done" ? t("emailVerified") : t("verifyEmail")} copy={status === "done" ? t("emailVerifiedCopy") : t("verifyEmailCopy")}><form className="mt-7 space-y-4" onSubmit={submit}>{token ? <div className="rounded-xl bg-sky p-4 text-sm text-navy"><ShieldCheck className="mb-2" size={19} />{t("verificationLinkReady")}</div> : <><AuthField label={t("email")} value={email} onChange={setEmail} autoComplete="email" /><p className="text-xs text-slate-500">{t("verificationResendHint")}</p></>}{error && <FormError error={error} />}<SubmitButton busy={busy}>{token ? t("verifyEmail") : t("resendVerification")}</SubmitButton></form><Link to="/auth/sign-in" className="mt-6 inline-flex text-sm font-bold text-blue-600 hover:underline">{t("backToSignIn")}</Link></AuthCard></AuthShell>;
}

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!email.includes("@")) { setError(t("validCredentials")); return; } setBusy(true); try { await api.forgotPassword(email); setDone(true); } catch (reason) { setError(messageFor(reason)); } finally { setBusy(false); } };
  return <AuthShell><AuthCard eyebrow={t("accountRecovery")} title={t("forgotPassword")} copy={done ? t("resetInstructionsSent") : t("forgotPasswordCopy")}><form className="mt-7 space-y-4" onSubmit={submit} noValidate><AuthField label={t("email")} value={email} onChange={setEmail} autoComplete="email" placeholder="you@example.com" />{done ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200">{t("resetInstructionsDetail")}</div> : <><p className="text-xs leading-5 text-slate-500">{t("genericRecoveryCopy")}</p>{error && <FormError error={error} />}<SubmitButton busy={busy}>{t("sendInstructions")}</SubmitButton></>}</form><Link to="/auth/sign-in" className="mt-6 inline-flex text-sm font-bold text-blue-600 hover:underline">{t("backToSignIn")}</Link></AuthCard></AuthShell>;
}

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); if (!token || password.length < 8 || password.length > 12 || password !== confirm) { setError(password !== confirm ? t("passwordsMustMatch") : t("passwordRule")); return; } setBusy(true); try { await api.resetPassword(token, password); setDone(true); } catch (reason) { setError(messageFor(reason)); } finally { setBusy(false); } };
  return <AuthShell><AuthCard eyebrow={t("accountRecovery")} title={done ? t("passwordReset") : t("resetPassword")} copy={done ? t("passwordResetCopy") : t("resetPasswordCopy")}><form className="mt-7 space-y-4" onSubmit={submit} noValidate>{!params.get("token") && <AuthField label={t("resetToken")} value={token} onChange={setToken} />}{!done && <><AuthField label={t("newPassword")} type="password" value={password} onChange={setPassword} autoComplete="new-password" /><AuthField label={t("confirmPassword")} type="password" value={confirm} onChange={setConfirm} autoComplete="new-password" />{error && <FormError error={error} />}<SubmitButton busy={busy}>{t("resetPassword")}</SubmitButton></>}</form>{done && <Link to="/auth/sign-in" className="mt-6 inline-flex text-sm font-bold text-blue-600 hover:underline">{t("backToSignIn")}</Link>}</AuthCard></AuthShell>;
}
