import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  Check,
  Download,
  History,
  KeyRound,
  Laptop,
  LogOut,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { api } from "./api";
import { useAuth, usePreferences, type SavedTranslation } from "./store";
import type { AuthSession, FavoriteItem, SyncRecordInput } from "./types";
import type { LucideIcon } from "lucide-react";

function errorMessage(reason: unknown): string {
  if (reason instanceof Error) return reason.message;
  return "Something went wrong. Please try again.";
}

function AccountLoading() {
  const { t } = useTranslation();
  return <div className="grid min-h-[360px] place-items-center"><div className="text-center"><div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-blue-100 border-t-blue-600" /><p className="subtle text-sm">{t("loading")}</p></div></div>;
}

function AccountError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  return <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-5 dark:border-rose-900/50 dark:bg-rose-950/30"><p className="font-bold text-rose-900 dark:text-rose-100">{t("accountError")}</p><p className="mt-1 text-sm text-rose-800 dark:text-rose-200">{errorMessage(error)}</p>{onRetry && <button className="mt-4 rounded-xl bg-rose-700 px-4 py-2 text-sm font-bold text-white" onClick={onRetry}>{t("retry")}</button>}</div>;
}

function AccountHeader({ eyebrow, title, copy, icon: Icon = UserRound }: { eyebrow: string; title: string; copy: string; icon?: LucideIcon }) {
  return <div className="mb-8 flex items-start gap-4"><div className="hidden h-12 w-12 shrink-0 place-items-center rounded-2xl bg-sky text-blue-600 sm:grid"><Icon size={22} /></div><div><p className="mb-2 text-xs font-bold uppercase tracking-[.18em] text-blue-600">{eyebrow}</p><h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1><p className="subtle mt-2 max-w-2xl text-sm leading-6 sm:text-base">{copy}</p></div></div>;
}

function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <section className="surface rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-[#13233b]"><div className="mb-5 flex items-center justify-between gap-3"><h2 className="font-bold">{title}</h2>{action}</div>{children}</section>;
}

function ActionButton({ children, busy = false, kind = "primary", type = "button", onClick, disabled = false }: { children: ReactNode; busy?: boolean; kind?: "primary" | "quiet" | "danger"; type?: "button" | "submit"; onClick?: () => void; disabled?: boolean }) {
  const styles = kind === "danger" ? "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200" : kind === "quiet" ? "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-[#101d31] dark:text-slate-200" : "bg-navy text-white hover:bg-blue-900";
  return <button type={type} disabled={busy || disabled} onClick={onClick} className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles}`}>{busy && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}{children}</button>;
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, checked } = useAuth();
  if (!checked) return <AccountLoading />;
  if (!user) return <Navigate to="/auth/sign-in" replace />;
  return <>{children}</>;
}

export function DashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const history = useQuery({ queryKey: ["account-history", user?.id, "dashboard"], queryFn: () => api.getHistory({ limit: 3, offset: 0 }), enabled: Boolean(user) });
  return <div className="mx-auto max-w-6xl"><AccountHeader eyebrow={t("dashboard")} title={`${t("welcomeBack")}, ${user?.email ?? ""}`} copy={t("dashboardCopy")} /><div className="grid gap-4 sm:grid-cols-3"><SummaryCard title={t("serverHistory")} value={history.data?.total ?? "—"} href="/history" icon={History} /><SummaryCard title={t("favorites")} value="—" href="/favorites" icon={ShieldCheck} /><SummaryCard title={t("security")} value={t("protected")} href="/security" icon={KeyRound} /></div><div className="mt-5 grid gap-5 lg:grid-cols-[1.3fr_.7fr]"><Panel title={t("recentTranslations")}>{history.isLoading ? <AccountLoading /> : history.isError ? <AccountError error={history.error} onRetry={() => void history.refetch()} /> : history.data?.items.length ? <div className="divide-y divide-slate-100 dark:divide-slate-700">{history.data.items.map((item) => <div className="py-4 first:pt-0 last:pb-0" key={item.id}><div className="flex items-center justify-between gap-3 text-xs font-bold text-blue-600"><span>{item.source_language} → {item.target_language}</span><span className="subtle font-normal">{new Date(item.created_at).toLocaleDateString()}</span></div><p className="mt-2 line-clamp-2 text-sm">{item.source_text}</p></div>)}</div> : <EmptyAccount title={t("noHistoryServer")} copy={t("historyEmptyCopy")} href="/translate" action={t("startTranslating")} />}</Panel><Panel title={t("account")}><div className="space-y-3"><AccountLink href="/profile" icon={UserRound} label={t("profile")} /><AccountLink href="/security" icon={KeyRound} label={t("security")} /><AccountLink href="/privacy" icon={ShieldCheck} label={t("privacySettings")} /></div></Panel></div></div>;
}

function SummaryCard({ title, value, href, icon: Icon }: { title: string; value: string | number; href: string; icon: LucideIcon }) { return <Link to={href} className="surface rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:shadow-soft dark:border-slate-700 dark:bg-[#13233b]"><Icon className="mb-5 text-blue-600" size={19} /><p className="subtle text-xs font-bold uppercase tracking-wider">{title}</p><p className="mt-1 text-2xl font-extrabold">{value}</p></Link>; }
function AccountLink({ href, icon: Icon, label }: { href: string; icon: LucideIcon; label: string }) { return <Link to={href} className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-3 text-sm font-semibold hover:border-blue-200 hover:bg-sky dark:border-slate-700 dark:hover:border-slate-600"><span className="flex items-center gap-3"><Icon size={17} className="text-blue-600" />{label}</span><ArrowRight size={16} className="subtle" /></Link>; }
function EmptyAccount({ title, copy, href, action }: { title: string; copy: string; href?: string; action?: string }) { return <div className="rounded-xl border border-dashed border-slate-200 p-7 text-center dark:border-slate-700"><p className="font-semibold">{title}</p><p className="subtle mt-1 text-sm">{copy}</p>{href && action && <Link to={href} className="mt-4 inline-flex text-sm font-bold text-blue-600 hover:underline">{action} <ArrowRight size={15} /></Link>}</div>; }

export function ProfilePage() {
  const { t } = useTranslation();
  const query = useQuery({ queryKey: ["profile"], queryFn: api.getProfile });
  const [displayName, setDisplayName] = useState("");
  const mutation = useMutation({ mutationFn: api.updateProfile, onSuccess: (profile) => { setDisplayName(profile.display_name ?? ""); void query.refetch(); } });
  useEffect(() => { if (query.data) setDisplayName(query.data.display_name ?? ""); }, [query.data]);
  if (query.isLoading) return <AccountLoading />;
  if (query.isError || !query.data) return <AccountError error={query.error} onRetry={() => void query.refetch()} />;
  const profile = query.data;
  return <div className="mx-auto max-w-4xl"><AccountHeader eyebrow={t("profile")} title={t("yourProfile")} copy={t("profileCopy")} /><Panel title={t("accountDetails")}><form className="grid gap-5 sm:grid-cols-2" onSubmit={(event: FormEvent) => { event.preventDefault(); mutation.mutate({ display_name: displayName.trim() || null }); }}><Field label={t("email")} value={profile.email} readOnly /><Field label={t("displayName")} value={displayName} onChange={setDisplayName} maxLength={100} placeholder={t("displayNamePlaceholder")} /><div className="sm:col-span-2 flex flex-wrap items-center gap-3"><ActionButton type="submit" busy={mutation.isPending}>{t("saveChanges")}</ActionButton>{mutation.isSuccess && <span className="inline-flex items-center gap-1 text-sm font-semibold text-emerald-700 dark:text-emerald-300"><Check size={15} />{t("saved")}</span>}{mutation.isError && <span role="alert" className="text-sm text-rose-700 dark:text-rose-300">{errorMessage(mutation.error)}</span>}</div></form><div className="mt-6 flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400"><span>{profile.email_verified ? t("verified") : t("unverified")}</span><span>·</span><span>{t("memberSince")} {new Date(profile.created_at).toLocaleDateString()}</span></div></Panel></div>;
}

function Field({ label, value, onChange, readOnly = false, maxLength, placeholder, type = "text", autoComplete }: { label: string; value: string; onChange?: (value: string) => void; readOnly?: boolean; maxLength?: number; placeholder?: string; type?: string; autoComplete?: string }) { return <label className="block"><span className="mb-1.5 block text-sm font-bold">{label}</span><input type={type} value={value} readOnly={readOnly} maxLength={maxLength} placeholder={placeholder} autoComplete={autoComplete} onChange={(event) => onChange?.(event.target.value)} className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none ring-blue-500 focus:ring-2 read-only:bg-slate-50 dark:border-slate-700 dark:bg-[#101d31] dark:read-only:bg-slate-800" /></label>; }

export function SecurityPage() {
  const { t } = useTranslation();
  const { clearUser } = useAuth();
  const clearLocalLibrary = usePreferences((state) => state.clearLocalLibrary);
  const navigate = useNavigate();
  const sessions = useQuery({ queryKey: ["auth-sessions"], queryFn: api.getSessions });
  const revoke = useMutation({ mutationFn: api.revokeSession, onSuccess: () => void sessions.refetch() });
  const logout = useMutation({ mutationFn: api.logout, onSettled: () => { clearLocalLibrary(); clearUser(); navigate("/auth/sign-in", { replace: true }); } });
  return <div className="mx-auto max-w-4xl"><AccountHeader eyebrow={t("security")} title={t("securityTitle")} copy={t("securityCopy")} icon={KeyRound} /><div className="grid gap-5"><Panel title={t("activeSessions")} action={<Laptop className="subtle" size={18} />}>{sessions.isLoading ? <AccountLoading /> : sessions.isError ? <AccountError error={sessions.error} onRetry={() => void sessions.refetch()} /> : sessions.data?.length ? <div className="space-y-3">{sessions.data.map((session) => <SessionRow key={session.id} session={session} onRevoke={() => revoke.mutate(session.id)} busy={revoke.isPending && revoke.variables === session.id} />)}</div> : <EmptyAccount title={t("noSessions")} copy={t("noSessionsCopy")} />}</Panel><Panel title={t("signOut")}><p className="subtle mb-4 text-sm">{t("signOutCopy")}</p><ActionButton kind="quiet" busy={logout.isPending} onClick={() => logout.mutate()}><LogOut size={16} />{t("signOut")}</ActionButton></Panel></div></div>;
}

function SessionRow({ session, onRevoke, busy }: { session: AuthSession; onRevoke: () => void; busy: boolean }) { const { t } = useTranslation(); return <div className="flex flex-col gap-3 rounded-xl border border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700"><div className="flex min-w-0 items-start gap-3"><Laptop className="mt-0.5 shrink-0 text-blue-600" size={18} /><div className="min-w-0"><p className="truncate text-sm font-bold">{session.device_name || t("unknownDevice")} {session.current && <span className="ml-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">{t("currentSession")}</span>}</p><p className="subtle mt-1 text-xs">{t("lastActive")}: {new Date(session.last_seen_at).toLocaleString()} · {t("sessionExpires")}: {new Date(session.expires_at).toLocaleDateString()}</p></div></div>{!session.current && <ActionButton kind="quiet" busy={busy} onClick={onRevoke}>{t("revoke")}</ActionButton>}</div>; }

export function ServerHistoryPage() {
  const { t } = useTranslation();
  const [page, setPage] = useState(0);
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["account-history", page], queryFn: () => api.getHistory({ limit: 10, offset: page * 10 }) });
  const remove = useMutation({ mutationFn: api.deleteHistory, onSuccess: () => void client.invalidateQueries({ queryKey: ["account-history"] }) });
  const clear = useMutation({ mutationFn: api.clearHistory, onSuccess: () => { setPage(0); void client.invalidateQueries({ queryKey: ["account-history"] }); } });
  return <div className="mx-auto max-w-5xl"><AccountHeader eyebrow={t("history")} title={t("serverHistory")} copy={t("historyServerCopy")} icon={History} /><Panel title={t("translationHistory")} action={query.data?.total ? <ActionButton kind="quiet" busy={clear.isPending} onClick={() => { if (window.confirm(t("confirmClearHistory"))) clear.mutate(); }}><Trash2 size={15} />{t("clearAll")}</ActionButton> : undefined}>{query.isLoading ? <AccountLoading /> : query.isError ? <AccountError error={query.error} onRetry={() => void query.refetch()} /> : query.data?.items.length ? <><div className="space-y-3">{query.data.items.map((item) => <article className="rounded-xl border border-slate-100 p-4 dark:border-slate-700" key={item.id}><div className="flex items-center justify-between gap-3 text-xs font-bold text-blue-600"><span>{item.source_language} → {item.target_language}</span><time className="subtle font-normal">{new Date(item.created_at).toLocaleString()}</time></div><div className="mt-3 grid gap-3 md:grid-cols-2"><p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800/60">{item.source_text}</p><p className="whitespace-pre-wrap rounded-lg bg-sky p-3 text-sm dark:bg-blue-950/30">{item.translated_text}</p></div><button className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-rose-600 hover:underline" onClick={() => remove.mutate(item.id)} disabled={remove.isPending && remove.variables === item.id}><Trash2 size={13} />{t("delete")}</button></article>)}</div><Pagination page={page} total={query.data.total} onPage={setPage} /></> : <EmptyAccount title={t("noHistoryServer")} copy={t("historyEmptyCopy")} href="/translate" action={t("startTranslating")} />}</Panel></div>;
}

export function ServerFavoritesPage() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["account-favorites"], queryFn: () => api.getFavorites({ limit: 20, offset: 0 }) });
  const remove = useMutation({ mutationFn: api.deleteFavorite, onSuccess: () => void client.invalidateQueries({ queryKey: ["account-favorites"] }) });
  return <div className="mx-auto max-w-5xl"><AccountHeader eyebrow={t("favorites")} title={t("savedFavorites")} copy={t("favoritesServerCopy")} icon={ShieldCheck} /><Panel title={t("favorites")}>{query.isLoading ? <AccountLoading /> : query.isError ? <AccountError error={query.error} onRetry={() => void query.refetch()} /> : query.data?.items.length ? <div className="grid gap-4 md:grid-cols-2">{query.data.items.map((favorite) => <FavoriteCard key={favorite.id} favorite={favorite} onDelete={() => remove.mutate(favorite.id)} />)}</div> : <EmptyAccount title={t("noFavoritesServer")} copy={t("favoritesEmptyCopy")} />}</Panel></div>;
}

function FavoriteCard({ favorite, onDelete }: { favorite: FavoriteItem; onDelete: () => void }) { const { t } = useTranslation(); return <article className="rounded-xl border border-slate-100 p-4 dark:border-slate-700"><p className="text-xs font-bold text-blue-600">{favorite.translation.source_language} → {favorite.translation.target_language}</p><p className="mt-3 line-clamp-3 text-sm">{favorite.translation.translated_text}</p><button className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-rose-600 hover:underline" onClick={onDelete}><Trash2 size={13} />{t("removeFavorite")}</button></article>; }
function Pagination({ page, total, onPage }: { page: number; total: number; onPage: (page: number) => void }) { const { t } = useTranslation(); const max = Math.max(0, Math.ceil(total / 10) - 1); return <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-sm dark:border-slate-700"><button className="font-bold text-blue-600 disabled:opacity-35" disabled={page === 0} onClick={() => onPage(page - 1)}>{t("previous")}</button><span className="subtle">{page + 1} / {max + 1}</span><button className="font-bold text-blue-600 disabled:opacity-35" disabled={page >= max} onClick={() => onPage(page + 1)}>{t("next")}</button></div>; }

export function PrivacySettingsPage() {
  const { t } = useTranslation();
  const { localLibraryOptIn, setLocalLibraryOptIn } = usePreferences();
  const query = useQuery({ queryKey: ["user-preferences"], queryFn: api.getPreferences });
  const mutation = useMutation({ mutationFn: api.updatePreferences, onSuccess: () => void query.refetch() });
  const exportMutation = useMutation({ mutationFn: api.exportAccount, onSuccess: (blob) => { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "lingua-account-export.json"; link.click(); URL.revokeObjectURL(url); } });
  if (query.isLoading) return <AccountLoading />;
  if (query.isError || !query.data) return <AccountError error={query.error} onRetry={() => void query.refetch()} />;
  const preferences = query.data;
  return <div className="mx-auto max-w-4xl"><AccountHeader eyebrow={t("privacySettings")} title={t("privacyTitle")} copy={t("privacyCopy")} icon={ShieldCheck} /><div className="grid gap-5"><Panel title={t("serverHistory")}><ToggleRow title={t("enableHistory")} copy={t("historyOptInCopy")} checked={preferences.history_enabled} disabled={mutation.isPending} onChange={(checked) => mutation.mutate({ history_enabled: checked })} /></Panel><Panel title={t("localPrivacy")}><ToggleRow title={t("localLibrary")} copy={t("localPrivacyCopy")} checked={localLibraryOptIn} onChange={setLocalLibraryOptIn} /><p className="subtle mt-4 text-xs">{t("localPrivacyWarning")}</p></Panel><SyncPanel /><Panel title={t("exportData")}><p className="subtle mb-4 text-sm">{t("exportDataCopy")}</p><ActionButton kind="quiet" busy={exportMutation.isPending} onClick={() => exportMutation.mutate()}><Download size={16} />{t("downloadExport")}</ActionButton>{exportMutation.isError && <p role="alert" className="mt-3 text-sm text-rose-700 dark:text-rose-300">{errorMessage(exportMutation.error)}</p>}</Panel><Panel title={t("accountDeletion")}><p className="subtle mb-4 text-sm">{t("accountDeletionCopy")}</p><Link to="/account/delete" className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-bold text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200"><Trash2 size={16} />{t("deleteAccount")}</Link></Panel></div></div>;
}

function SyncPanel() {
  const { t } = useTranslation();
  const { history, favorites, mergeSynced, uiLanguage, theme, setUiLanguage, setTheme } = usePreferences();
  const [selected, setSelected] = useState<string[]>([]);
  const status = useQuery({ queryKey: ["sync-status"], queryFn: api.getSyncStatus });
  const consent = useMutation({ mutationFn: api.setSyncConsent, onSuccess: () => void status.refetch() });
  const records: SyncRecordInput[] = [
    ...history.map((item) => ({ entity_type: "translation" as const, client_record_id: item.id, client_updated_at: item.updatedAt ?? item.createdAt, source_language: item.sourceLanguage, target_language: item.targetLanguage, source_text: item.sourceText, translated_text: item.translatedText, provider: "local" })),
    ...favorites.map((item) => ({ entity_type: "favorite" as const, client_record_id: `${item.id}:favorite`, translation_client_record_id: item.id, client_updated_at: item.updatedAt ?? item.createdAt })),
  ];
  const preview = useMutation({ mutationFn: () => api.previewSync(records.filter((record) => selected.includes(record.client_record_id))) });
  const upload = useMutation({ mutationFn: async () => { await api.updateSyncPreferences({ locale: uiLanguage === "mm" ? "my" : "en", theme }); return api.importSync(records.filter((record) => selected.includes(record.client_record_id)), crypto.randomUUID()); }, onSuccess: () => void preview.reset() });
  const download = useMutation({ mutationFn: async () => { let cursor: string | undefined; const pages = []; do { const page = await api.getSyncChanges(cursor); pages.push(...page.items); cursor = page.has_more ? page.next_cursor ?? undefined : undefined; if (page.has_more && !cursor) break; } while (cursor); const remote = await api.getSyncStatus(); return { items: pages, remote }; }, onSuccess: ({ items, remote }) => {
    setUiLanguage(remote.preferences.locale === "my" ? "mm" : "en");
    if (remote.preferences.theme !== "system") setTheme(remote.preferences.theme);
    const translations: SavedTranslation[] = items.filter((item) => item.entity_type === "translation" && !item.deleted && item.source_text && item.translated_text).map((item) => ({ id: item.client_record_id, sourceLanguage: item.source_language!, targetLanguage: item.target_language!, sourceText: item.source_text!, translatedText: item.translated_text!, createdAt: item.client_updated_at, updatedAt: item.updated_at }));
    const deleted = items.filter((item) => item.deleted && item.entity_type === "translation").map((item) => item.client_record_id);
    const favoriteIds = items.filter((item) => item.entity_type === "favorite" && !item.deleted && item.translation_client_record_id).map((item) => item.translation_client_record_id!);
    mergeSynced(translations, deleted, favoriteIds);
  } });
  if (status.isLoading) return <Panel title={t("cloudSync")}><p className="subtle text-sm">{t("loading")}</p></Panel>;
  if (status.isError) return <Panel title={t("cloudSync")}><p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{t("syncError")}: {errorMessage(status.error)}</p><ActionButton kind="quiet" onClick={() => void status.refetch()}>{t("retry")}</ActionButton></Panel>;
  const enabled = status.data?.enabled ?? false;
  return <Panel title={t("cloudSync")}><p className="subtle mb-4 text-sm">{t("cloudSyncCopy")}</p><ToggleRow title={t("enableCloudSync")} copy={enabled ? t("syncReady") : t("syncDisabled")} checked={enabled} disabled={consent.isPending} onChange={(checked) => consent.mutate(checked)} />{enabled && <><label className="mt-5 flex items-start gap-3 rounded-xl border border-blue-100 bg-sky p-3 text-sm dark:border-blue-900/50 dark:bg-blue-950/20"><input type="checkbox" className="mt-1 h-4 w-4 accent-blue-700" checked={selected.length === records.length && records.length > 0} onChange={(event) => setSelected(event.target.checked ? records.map((record) => record.client_record_id) : [])} /><span>{t("syncConsent")}</span></label>{records.length ? <div className="mt-4 max-h-48 space-y-2 overflow-auto">{records.map((record) => <label key={record.client_record_id} className="flex items-center gap-3 rounded-lg border border-slate-100 p-2 text-sm dark:border-slate-700"><input type="checkbox" checked={selected.includes(record.client_record_id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, record.client_record_id] : current.filter((id) => id !== record.client_record_id))} /><span className="truncate">{record.entity_type} · {record.client_record_id}</span></label>)}</div> : <p className="subtle mt-4 text-sm">{t("noLocalRecords")}</p>}<div className="mt-4 flex flex-wrap gap-2"><ActionButton kind="quiet" busy={preview.isPending} disabled={!selected.length} onClick={() => preview.mutate()}>{t("syncPreview")}</ActionButton><ActionButton busy={upload.isPending} disabled={!preview.data || preview.data.accepted_count === 0} onClick={() => upload.mutate()}>{t("uploadSelected")}</ActionButton><ActionButton kind="quiet" busy={download.isPending} onClick={() => download.mutate()}>{t("downloadUpdates")}</ActionButton></div>{preview.data && <p className="mt-3 text-xs font-semibold text-blue-700 dark:text-blue-300">{preview.data.accepted_count} {t("selected")}</p>}{(preview.isError || upload.isError || download.isError) && <p role="alert" className="mt-3 text-sm text-rose-700 dark:text-rose-300">{t("syncError")}</p>}</>}</Panel>;
}
function ToggleRow({ title, copy, checked, onChange, disabled = false }: { title: string; copy: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean }) { return <label className="flex cursor-pointer items-start justify-between gap-4"><span><span className="block text-sm font-bold">{title}</span><span className="subtle mt-1 block text-sm leading-5">{copy}</span></span><input className="mt-1 h-5 w-5 accent-blue-700" type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} /></label>; }

export function AccountDeletionPage() {
  const { t } = useTranslation();
  const { clearUser } = useAuth();
  const clearLocalLibrary = usePreferences((state) => state.clearLocalLibrary);
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState("");
  const mutation = useMutation({ mutationFn: api.deleteAccount, onSuccess: () => { clearLocalLibrary(); clearUser(); navigate("/auth/sign-in?deleted=1", { replace: true }); }, onError: (reason) => setError(errorMessage(reason)) });
  return <div className="mx-auto max-w-2xl"><AccountHeader eyebrow={t("accountDeletion")} title={t("deleteAccountTitle")} copy={t("accountDeletionCopy")} icon={Trash2} /><Panel title={t("deleteAccountConfirm")}><div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-900 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-100">{t("deleteAccountWarning")}</div><form className="mt-6 space-y-5" onSubmit={(event: FormEvent) => { event.preventDefault(); setError(""); if (confirmed && password) mutation.mutate(password); }}><Field label={t("reAuthPassword")} type="password" value={password} onChange={setPassword} autoComplete="current-password" /><label className="flex items-start gap-3 text-sm"><input className="mt-1 h-4 w-4 accent-rose-700" type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>{t("deleteAccountAcknowledge")}</span></label>{error && <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">{error}</p>}<div className="flex flex-wrap gap-3"><ActionButton kind="danger" type="submit" busy={mutation.isPending} disabled={false}>{t("deleteAccount")}</ActionButton><ActionButton kind="quiet" onClick={() => navigate(-1)}>{t("cancel")}</ActionButton></div></form></Panel></div>;
}
