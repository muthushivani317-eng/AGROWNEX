import { useRef, useState, type FormEvent } from 'react';
import { Eye, EyeOff, FileCheck2, Leaf, LockKeyhole, ShieldCheck, Users, AlertCircle } from 'lucide-react';
import { signInAdmin } from './auth';
import './Login.css';

export function loginErrorMessage(error: unknown): string {
  const code = typeof error === 'object' && error !== null && 'code' in error ? String(error.code) : '';
  if (['auth/invalid-credential', 'auth/wrong-password', 'auth/user-not-found', 'auth/invalid-email'].includes(code)) return 'Check your email and password, then try again.';
  if (code === 'auth/too-many-requests') return 'Too many sign-in attempts. Wait a few minutes before trying again.';
  if (code === 'auth/network-request-failed') return 'Could not connect. Check your connection and try again.';
  if (code === 'auth/invalid-verification-code') return 'The verification code was not accepted. Sign in again to request a new code.';
  if (code === 'auth/code-expired') return 'The verification code has expired. Sign in again to request a new code.';
  if (error instanceof Error && !code) return error.message;
  return 'Sign-in could not be completed. Try again or review sign-in help below.';
}

export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [help, setHelp] = useState<'access' | 'privacy' | null>(null);
  const pending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true; setBusy(true); setError(null);
    try { await signInAdmin(email.trim(), password); setPassword(''); setVisible(false); onSuccess(); }
    catch (failure) { setError(loginErrorMessage(failure)); setPassword(''); setVisible(false); }
    finally { pending.current = false; setBusy(false); }
  }
  return <main className="owner-login">
    <section className="ol-brand" aria-label="AgrowAI Admin">
      <div className="ol-contours ol-contours-top" aria-hidden="true"/>
      <div className="ol-contours ol-contours-bottom" aria-hidden="true"/>
      <div className="ol-brand-content">
        <div className="ol-wordmark"><Leaf size={66} strokeWidth={1.5} aria-hidden="true"/><div><strong>AGROWAI</strong><span>ADMIN</span></div></div>
        <h1>Operations,<br/>securely managed.</h1>
        <p className="ol-brand-description">Authorised access for the AgrowAI<br className="ol-desktop-break"/> operations team.</p>
        <ul className="ol-assurances"><li><span><ShieldCheck aria-hidden="true"/></span>Farmer data protected</li><li><span><Users aria-hidden="true"/></span>Owner-controlled access</li><li><span><FileCheck2 aria-hidden="true"/></span>Privileged actions audit-logged</li></ul>
        <p className="ol-brand-footer"><Leaf size={18} aria-hidden="true"/>Built around the people who grow.</p>
      </div>
    </section>
    <section className="ol-form-side" aria-label="Admin sign in">
      <div className="ol-portal-label">Admin portal <ShieldCheck size={20} aria-hidden="true"/></div>
      <div className="ol-form-wrap"><div className="ol-card">
        <div className="ol-welcome"><span className="ol-lock"><ShieldCheck size={54} strokeWidth={1.3} aria-hidden="true"/></span><h2>Welcome back</h2><p>Sign in with your authorised AgrowAI work account.</p></div>
        <div className="ol-mode"><strong>Sign in</strong><span><LockKeyhole size={14} aria-hidden="true"/>Owner access only</span></div>
        <form onSubmit={submit} aria-busy={busy}>
          {error && <div className="ol-error" role="alert"><AlertCircle size={19} aria-hidden="true"/><span>{error}</span></div>}
          <label htmlFor="owner-email">Work email</label>
          <input id="owner-email" name="email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} placeholder="name@agrowai.in" value={email} onChange={event => setEmail(event.target.value)} disabled={busy} required/>
          <label htmlFor="owner-password">Password</label>
          <div className="ol-password"><input id="owner-password" name="password" type={visible ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} required/><button type="button" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} disabled={busy} onClick={() => setVisible(value => !value)}>{visible ? <EyeOff size={21}/> : <Eye size={21}/>}</button></div>
          <div className="ol-session"><span><ShieldCheck size={16} aria-hidden="true"/>MFA required</span><button type="button" className="ol-text-button" aria-expanded={help === 'access'} aria-controls="ol-help" onClick={() => setHelp(help === 'access' ? null : 'access')}>Need help signing in?</button></div>
          <button type="submit" className="ol-submit" disabled={busy || !email.trim() || !password}>{busy ? 'Verifying access…' : 'Sign in securely'}</button>
          {busy && <p role="status" className="ol-busy">Complete the verification prompt on this device. Keep this page open.</p>}
          <div id="admin-recaptcha"/>
        </form>
        <div className="ol-access-note"><LockKeyhole size={18} aria-hidden="true"/><p>Access is restricted to the authorised owner.<br/><span>Public registration and invitations are disabled.</span></p></div>
        {help && <section id="ol-help" className="ol-help" aria-label={help === 'access' ? 'Sign-in help' : 'Session privacy'}><h3>{help === 'access' ? 'Sign-in help' : 'Session privacy'}</h3>{help === 'access' ? <><p>Use the account configured as the AgrowAI owner and your enrolled MFA phone. Farmer accounts cannot enter this portal.</p><p>If you forgot your password or lost access to your MFA phone, use your established Firebase account recovery process. This page cannot reset your password or bypass MFA.</p></> : <><p>Authentication is handled by Firebase. After verification, the server creates a secure, HttpOnly admin session cookie.</p><p>This page does not extend your session or remember this device. Sign out when finished, especially on a shared computer.</p></>}<button type="button" className="ol-text-button" onClick={() => setHelp(null)}>Close help</button></section>}
      </div><footer className="ol-links"><button type="button" aria-expanded={help === 'privacy'} aria-controls="ol-help" onClick={() => setHelp(help === 'privacy' ? null : 'privacy')}>Session privacy</button><span aria-hidden="true"/><button type="button" aria-expanded={help === 'access'} aria-controls="ol-help" onClick={() => setHelp(help === 'access' ? null : 'access')}>Sign-in help</button></footer></div>
    </section>
  </main>;
}
