import { useCallback, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createClient } from '@supabase/supabase-js';
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, Check,
  CheckCircle2, ChevronDown, CircleHelp, Clapperboard, Clock3, Command,
  Compass, CreditCard, FileText, Film, Gauge, Layers3, Lightbulb, LoaderCircle, LogOut,
  Menu, Mic2, Plus, RefreshCw, Search, Send, Settings2, ShieldCheck,
  Sparkles, Upload, WandSparkles, X,
} from 'lucide-react';
import { API_BASE_URL, api, mediaUrl } from './api';
import './styles.css';
import './billing.css';
import './topic-discovery.css';

const SUPABASE_URL = __SUPABASE_URL__;
const SUPABASE_PUBLISHABLE_KEY = __SUPABASE_PUBLISHABLE_KEY__;
const supabase = SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY
  ? createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
  : null;

const VOICES = ['en-US-GuyNeural', 'en-US-JennyNeural', 'en-US-ChristopherNeural', 'en-GB-SoniaNeural', 'en-GB-RyanNeural', 'en-IN-PrabhatNeural', 'en-IN-NeerjaNeural', 'en-AU-WilliamNeural'];
const NAV = [
  { id: 'ideas', label: 'Topic discovery', icon: Compass, group: 'CREATE' },
  { id: 'studio', label: 'Script studio', icon: FileText, group: 'CREATE' },
  { id: 'videos', label: 'Video library', icon: Clapperboard, group: 'MANAGE' },
  { id: 'analytics', label: 'Performance', icon: BarChart3, group: 'MANAGE' },
  { id: 'billing', label: 'Plan & billing', icon: CreditCard, group: 'WORKSPACE' },
  { id: 'settings', label: 'Settings', icon: Settings2, group: 'WORKSPACE' },
];

function errorText(error) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

function getAuthCallbackError() {
  if (typeof window === 'undefined' || !window.location.hash) return null;
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const error = params.get('error');
  const code = params.get('error_code');
  const description = params.get('error_description');
  if (!error && !code) return null;
  return {
    error: error || 'access_denied',
    code: code || 'auth_error',
    description: description || 'This sign-in link has expired or is invalid. Please request a fresh one.',
  };
}

function AuthScreen({ onSession }) {
  const [mode, setMode] = useState('login');
  const [authMethod, setAuthMethod] = useState('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  async function submit(event) {
    event.preventDefault();
    setError(''); setInfo(''); setBusy(true);
    try {
      if (!supabase) throw new Error('Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the root .env, or in Vercel project environment variables.');

      if (authMethod === 'magic') {
        const result = await supabase.auth.signInWithOtp({
          email: email.trim(),
          options: {
            emailRedirectTo: window.location.origin,
          },
        });
        if (result.error) throw result.error;
        setInfo('Magic link sent. Check your inbox and open the link from this device to continue.');
        return;
      }

      const result = mode === 'login'
        ? await supabase.auth.signInWithPassword({ email: email.trim(), password })
        : await supabase.auth.signUp({ email: email.trim(), password, options: { data: { full_name: name.trim() } } });
      if (result.error) throw result.error;
      if (!result.data.session) {
        setInfo('Account created. Check your inbox to confirm your email, then sign in.');
        setMode('login');
        return;
      }
      await onSession(result.data.session);
    } catch (err) { setError(errorText(err)); }
    finally { setBusy(false); }
  }

  return <main className="auth-shell">
    <div className="auth-glow auth-glow-one" /><div className="auth-glow auth-glow-two" />
    <section className="auth-card">
      <a className="brand brand-auth" href="#"><span className="brand-mark"><Sparkles size={18} /></span><span>studio<span className="brand-light">flow</span></span></a>
      <div className="auth-heading"><span className="eyebrow"><span className="live-dot" /> YOUR CREATOR WORKSPACE</span><h1>Good ideas deserve<br /><span>a bigger stage.</span></h1><p>Research, write, and manage your next great video—all in one focused space.</p></div>
      <div className="auth-tabs"><button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(''); }}>Sign in</button><button className={mode === 'signup' ? 'active' : ''} onClick={() => { setMode('signup'); setError(''); }}>Create account</button></div>
      <div className="auth-tabs" style={{ marginTop: 12 }}>
        <button type="button" className={authMethod === 'password' ? 'active' : ''} onClick={() => { setAuthMethod('password'); setError(''); }}>Password</button>
        <button type="button" className={authMethod === 'magic' ? 'active' : ''} onClick={() => { setAuthMethod('magic'); setError(''); }}>Magic link</button>
      </div>
      <form className="auth-form" onSubmit={submit}>
        {mode === 'signup' && authMethod === 'password' && <label>Your name<input value={name} onChange={e => setName(e.target.value)} placeholder="Alex Morgan" autoComplete="name" required /></label>}
        <label>Email address<div className="input-icon"><span>@</span><input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" required /></div></label>
        {authMethod === 'password' && <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 6 characters" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={6} required /></label>}
        {error && <div className="notice error"><X size={16} />{error}</div>}{info && <div className="notice success"><CheckCircle2 size={16} />{info}</div>}
        <button className="button primary auth-submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <>{authMethod === 'magic' ? 'Send magic link' : (mode === 'login' ? 'Continue to workspace' : 'Create your account')}<ArrowRight size={17} /></>}</button>
      </form>
      <div className="auth-foot"><ShieldCheck size={15} /> Secure sign-in powered by Supabase Auth</div>
    </section>
    <div className="auth-bottom"><span>Plan with intention. Publish with confidence.</span><span>API · {API_BASE_URL}</span></div>
  </main>;
}

function App() {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [active, setActive] = useState('ideas');
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState(null);
  const [busyKey, setBusyKey] = useState('');
  const [db, setDb] = useState(null);
  const [topics, setTopics] = useState([]);
  const [topicsNote, setTopicsNote] = useState('');
  const [seeds, setSeeds] = useState([]);
  const [seedInput, setSeedInput] = useState('');
  const [customTopic, setCustomTopic] = useState('');
  const [researched, setResearched] = useState(null);
  const [scriptForm, setScriptForm] = useState({ topic: '', title: '', description: '', script: '', voice: 'en-US-GuyNeural', duration: 60 });
  const [videos, setVideos] = useState([]);
  const [filter, setFilter] = useState('all');
  const [analytics, setAnalytics] = useState({ topics: [], summary: {}, total_learned_topics: 0 });
  const [config, setConfig] = useState(null);
  const [settings, setSettings] = useState({ channel_name: '', target_seconds: 50, voice: VOICES[0], default_privacy: 'private', pexels_api_key: '' });
  const [billingPlans, setBillingPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingError, setBillingError] = useState('');

  const token = session?.access_token;
  const flash = useCallback((message, kind = 'success') => {
    setNotice({ message, kind });
    window.clearTimeout(flash.timer);
    flash.timer = window.setTimeout(() => setNotice(null), 4500);
  }, []);

  const acceptSession = useCallback(async nextSession => {
    const profile = await api('/api/auth/me', { token: nextSession.access_token });
    setSession(nextSession); setUser(profile);
  }, []);

  useEffect(() => {
    if (!supabase) { setAuthReady(true); return undefined; }

    const callbackError = getAuthCallbackError();
    if (callbackError) {
      flash(callbackError.description, 'error');
      window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    }

    let alive = true;
    supabase.auth.getSession().then(async ({ data }) => {
      if (!alive) return;
      if (data.session) {
        try { await acceptSession(data.session); }
        catch (error) { await supabase.auth.signOut(); if (alive) flash(errorText(error), 'error'); }
      }
      if (alive) setAuthReady(true);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (event === 'SIGNED_OUT') { setSession(null); setUser(null); }
      else if (nextSession && !session) setSession(nextSession);
    });
    return () => { alive = false; listener.subscription.unsubscribe(); };
  }, [acceptSession, flash]);

  const loadWorkspace = useCallback(async () => {
    if (!token) return;
    const jobs = await Promise.allSettled([
      api('/api/db/status'), api('/api/topics', { token }), api('/api/topics/seeds', { token }),
      api('/api/videos', { token }), api('/api/analytics', { token }), api('/api/config', { token }),
    ]);
    const [statusResult, topicsResult, seedsResult, videosResult, analyticsResult, configResult] = jobs;
    if (statusResult.status === 'fulfilled') setDb(statusResult.value);
    else setDb({ connected: false, message: errorText(statusResult.reason), dialect: 'Supabase Postgres' });
    if (topicsResult.status === 'fulfilled') {
      setTopics(topicsResult.value.topics || []);
      setTopicsNote(topicsResult.value.note || '');
    }
    if (seedsResult.status === 'fulfilled') setSeeds(seedsResult.value.seeds || []);
    if (videosResult.status === 'fulfilled') setVideos(videosResult.value.videos || []);
    if (analyticsResult.status === 'fulfilled') setAnalytics(analyticsResult.value);
    if (configResult.status === 'fulfilled') {
      const value = configResult.value;
      setConfig(value);
      setSettings(current => ({ ...current, channel_name: value.channel_name || '', target_seconds: value.target_seconds || 50, voice: value.voice || VOICES[0], default_privacy: value.default_privacy || 'private' }));
    }
  }, [token]);

  useEffect(() => { if (token) loadWorkspace(); }, [token, loadWorkspace]);

  async function run(key, task, successMessage) {
    setBusyKey(key);
    try { const result = await task(); if (successMessage) flash(successMessage); return result; }
    catch (error) { flash(errorText(error), 'error'); return null; }
    finally { setBusyKey(''); }
  }

  async function signOut() {
    if (supabase) await supabase.auth.signOut();
    setSession(null); setUser(null);
  }

  async function saveSeeds(nextSeeds) {
    const payload = [...new Set(nextSeeds.map(item => item.trim()).filter(Boolean))].slice(0, 20);
    const result = await run('seeds', () => api('/api/topics/seeds', { token, method: 'POST', body: { seeds: payload } }), 'Your seed topics are saved.');
    if (result) { setSeeds(result.seeds || payload); setSeedInput(''); const updated = await api('/api/topics', { token }); setTopics(updated.topics || []); setTopicsNote(updated.note || ''); }
  }

  async function research() {
    const value = await run('research', () => api('/api/topics/research', { token, method: 'POST', body: { topic: customTopic } }));
    if (value) setResearched(value);
  }

  async function generateScript(topic = scriptForm.topic) {
    if (!topic.trim()) return flash('Enter a topic first.', 'error');
    const result = await run('generate', () => api('/api/scripts/generate', { token, method: 'POST', body: { topic, duration_seconds: Number(scriptForm.duration) } }), 'Your script is ready.');
    if (result) { setScriptForm(current => ({ ...current, topic: result.topic, title: result.title, description: result.description, script: result.script })); setActive('studio'); }
  }

  async function saveDraft() {
    const value = await run('save', () => api('/api/scripts/save', { token, method: 'POST', body: { topic: scriptForm.topic, title: scriptForm.title, description: scriptForm.description, script: scriptForm.script, voice: scriptForm.voice } }), 'Draft saved to your library.');
    if (value) { await refreshVideos(); setActive('videos'); }
  }

  async function buildVideo() {
    const value = await run('build', () => api('/api/videos/build', { token, method: 'POST', body: { topic: scriptForm.topic, title: scriptForm.title, description: scriptForm.description, script: scriptForm.script, voice: scriptForm.voice, duration_seconds: Number(scriptForm.duration), fast_mode: false } }), 'Video generation has started in the background.');
    if (value) { await refreshVideos(); setActive('videos'); }
  }

  async function refreshVideos() {
    const result = await api('/api/videos', { token }); setVideos(result.videos || []);
  }

  useEffect(() => {
    if (!token || active !== 'videos') return undefined;
    if (!videos.some(video => video.status === 'building')) return undefined;
    const id = window.setInterval(() => {
      refreshVideos();
    }, 5000);
    return () => window.clearInterval(id);
  }, [token, active, videos]);

  function getVideoProgress(video) {
    if (video.status === 'ready' || video.status === 'uploaded') return 100;
    if (video.status === 'build_failed') return 0;
    return Math.max(0, Math.min(100, Number(video.progress_percent || 0)));
  }

  function getVideoProgressLabel(video) {
    if (video.status === 'draft') return 'Draft saved';
    if (video.status === 'building') return `Rendering ${getVideoProgress(video)}%`;
    if (video.status === 'ready') return 'Ready to publish';
    if (video.status === 'uploaded') return 'Published';
    if (video.status === 'build_failed') return 'Build failed';
    return video.status.replaceAll('_', ' ');
  }

  async function videoAction(video, action) {
    if (action === 'delete' && !window.confirm(`Delete “${video.title}”? This cannot be undone.`)) return;
    if (action === 'upload' && !window.confirm(`Try uploading “${video.title}” to YouTube?`)) return;
    const value = await run(`${action}-${video.local_id}`, async () => {
      if (action === 'delete') return api(`/api/videos/${video.local_id}`, { token, method: 'DELETE' });
      return api(`/api/videos/${video.local_id}/upload`, { token, method: 'POST', body: { privacy_status: video.privacy_status || 'private' } });
    }, action === 'delete' ? 'Project deleted.' : 'Upload request completed.');
    if (value) await refreshVideos();
  }

  async function sendFeedback(item, event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await run(`feedback-${item.topic}`, () => api('/api/analytics/feedback', { token, method: 'POST', body: { topic: item.topic, score: Number(form.get('score')), attempts: Number(form.get('attempts')), views: Number(form.get('views')), subscribers_gained: Number(form.get('subscribers')) } }), 'Performance feedback saved.');
    if (result) { event.currentTarget.reset(); const next = await api('/api/analytics', { token }); setAnalytics(next); }
  }

  async function saveSettings(event) {
    event.preventDefault();
    const payload = { ...settings, target_seconds: Number(settings.target_seconds) };
    const result = await run('settings', () => api('/api/config', { token, method: 'POST', body: payload }), 'Workspace settings updated.');
    if (result) { const next = await api('/api/config', { token }); setConfig(next); }
  }

  const loadBilling = useCallback(async () => {
    if (!token) return;
    setBillingLoading(true);
    setBillingError('');
    try {
      const [plansResult, subscriptionResult] = await Promise.allSettled([
        api('/api/billing/plans'),
        api('/api/billing/subscription', { token }),
      ]);
      if (plansResult.status === 'fulfilled') setBillingPlans(plansResult.value.plans || []);
      else throw plansResult.reason;
      if (subscriptionResult.status === 'fulfilled') setSubscription(subscriptionResult.value.subscription || null);
      else throw subscriptionResult.reason;
    } catch (error) {
      setBillingError(errorText(error));
    } finally {
      setBillingLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (active === 'billing') loadBilling();
  }, [active, loadBilling]);

  async function startPlanCheckout(planCode) {
    const result = await run(`checkout-${planCode}`, () => api('/api/billing/subscriptions', {
      token,
      method: 'POST',
      body: { plan_code: planCode },
    }));
    if (!result) return;
    if (result.checkout_url) {
      window.location.assign(result.checkout_url);
      return;
    }
    flash('Checkout was created, but no payment link was returned. Please contact support.', 'error');
  }

  const filteredVideos = useMemo(() => filter === 'all' ? videos : videos.filter(item => item.status === filter), [videos, filter]);
  const pageTitle = NAV.find(item => item.id === active)?.label || 'Topic discovery';
  const isConfigured = Boolean(supabase);

  if (!authReady) return <div className="splash"><div className="splash-logo"><Sparkles size={19} /></div><LoaderCircle className="spin" size={18} /></div>;
  if (!session || !user) return <AuthScreen onSession={acceptSession} />;

  return <div className="app-shell">
    {mobileNav && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <a href="#" className="brand"><span className="brand-mark"><Sparkles size={17} /></span><span>studio<span className="brand-light">flow</span></span></a>
      <button className="workspace-switch"><span className="workspace-avatar">{(config?.channel_name || user.full_name || 'S').slice(0, 1).toUpperCase()}</span><span className="workspace-copy"><b>{config?.channel_name || 'My channel'}</b><small>Creator workspace</small></span><ChevronDown size={15} /></button>
      <div className="nav-scroll">
        {['CREATE', 'MANAGE', 'WORKSPACE'].map(group => <div className="nav-group" key={group}><div className="nav-label">{group}</div>{NAV.filter(item => item.group === group).map(item => <button key={item.id} className={`nav-item ${active === item.id ? 'selected' : ''}`} onClick={() => { setActive(item.id); setMobileNav(false); }}><item.icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'videos' && videos.length > 0 && <span className="nav-count">{videos.length}</span>}</button>)}</div>)}
      </div>
      <div className="sidebar-bottom"><button className="plan-card" type="button" onClick={() => { setActive('billing'); setMobileNav(false); }} aria-label="Open plan and billing"><span className="plan-icon"><Gauge size={16} /></span><span className="plan-copy"><b>{subscription?.plan ? `${subscription.plan} plan` : 'Creator plan'}</b><small>{subscription?.status ? `Status: ${subscription.status}` : 'View plans & billing'}</small></span><ArrowUpRight size={15} /></button><div className="profile-row"><div className="profile-avatar">{(user.full_name || user.email || 'C').slice(0, 1).toUpperCase()}</div><div className="profile-copy"><b>{user.full_name || user.email}</b><small>{user.email}</small></div><button className="icon-button quiet" title="Sign out" onClick={signOut}><LogOut size={16} /></button></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button><div className="breadcrumb"><span>Workspace</span><span className="crumb-sep">/</span><b>{pageTitle}</b></div></div><div className="topbar-right"><div className={`connection ${db?.connected ? 'connected' : 'disconnected'}`}><span className="connection-dot" />{db?.connected ? 'Supabase connected' : 'Checking database'}</div><button className="icon-button help-button" title="Refresh workspace data" onClick={() => run('refresh', loadWorkspace)}><RefreshCw size={16} /></button><div className="top-avatar">{(user.full_name || user.email || 'C').slice(0, 1).toUpperCase()}</div></div></header>
      <div className="content-wrap">
        {active === 'billing' && <section className="billing-page">
          <div className="page-intro"><div><div className="eyebrow"><span className="live-dot" /> YOUR WORKSPACE PLAN</div><h1>Plan & <span>billing.</span></h1><p>Choose the plan that fits your publishing rhythm. Checkout is handled securely by Razorpay.</p></div><button className="button secondary" onClick={loadBilling} disabled={billingLoading}>{billingLoading ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />} Refresh plans</button></div>
          {billingError && <div className="notice error"><X size={16} /><span>{billingError}</span><button className="button secondary" onClick={loadBilling} disabled={billingLoading}>Try again</button></div>}
          {subscription && <div className="panel current-plan"><div className="current-plan-icon"><CheckCircle2 size={18} /></div><div><span className="section-kicker">CURRENT SUBSCRIPTION</span><h2>{subscription.plan || 'Creator plan'}</h2><p>Status: <b>{subscription.status}</b>{subscription.current_period_end ? ` · Renews ${new Date(subscription.current_period_end).toLocaleDateString()}` : ''}{subscription.cancel_at_cycle_end ? ' · Scheduled to cancel at period end' : ''}</p></div></div>}
          {billingLoading && !billingPlans.length ? <div className="billing-loading"><LoaderCircle className="spin" size={20} /> Loading plans…</div> : billingPlans.length ? <div className="billing-grid">{billingPlans.map(plan => {
            const isCurrent = subscription?.plan === plan.code;
            const checkoutBusy = busyKey === `checkout-${plan.code}`;
            return <article className={`panel billing-card ${isCurrent ? 'billing-current' : ''}`} key={plan.code}>
              <div className="billing-card-top"><div><span className="section-kicker">{plan.interval || 'monthly'} PLAN</span><h2>{plan.name}</h2></div>{isCurrent && <span className="current-badge">Current plan</span>}</div>
              <div className="billing-price"><b>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: plan.currency || 'INR', maximumFractionDigits: 0 }).format((plan.price_paise || 0) / 100)}</b><span>/ {plan.interval || 'month'}</span></div>
              <ul className="billing-features"><li><Check size={15} />{plan.videos_per_month} videos per month</li><li><Check size={15} />Up to {Math.floor(plan.max_duration_seconds / 60)} min {plan.max_duration_seconds % 60 ? `${plan.max_duration_seconds % 60} sec` : ''} per video</li><li><Check size={15} />{plan.scheduled_posts_per_month} scheduled posts per month</li></ul>
              <button className={`button ${isCurrent ? 'secondary' : 'primary'} full-button`} disabled={isCurrent || checkoutBusy} onClick={() => startPlanCheckout(plan.code)}>{checkoutBusy ? <><LoaderCircle className="spin" size={16} /> Preparing checkout…</> : isCurrent ? 'Current plan' : 'Choose plan'}{!isCurrent && !checkoutBusy && <ArrowRight size={15} />}</button>
            </article>;
          })}</div> : !billingError && <div className="empty-state billing-empty"><div className="empty-icon"><CreditCard size={22} /></div><h3>No plans are available yet</h3><p>Plans have not been published for this workspace. Please check back later.</p><button className="button secondary" onClick={loadBilling} disabled={billingLoading}><RefreshCw size={15} /> Check again</button></div>}
          <p className="billing-footnote"><ShieldCheck size={14} /> Payment details are entered only on Razorpay. Your account credentials are never shared with the app.</p>
        </section>}
        {notice && <div className={`toast ${notice.kind}`}><span>{notice.kind === 'error' ? <X size={16} /> : <Check size={16} />}</span>{notice.message}<button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={15} /></button></div>}
        {active === 'ideas' && <section>
          <div className="page-intro"><div><div className="eyebrow"><span className="live-dot" /> YOUR NEXT BIG IDEA STARTS HERE</div><h1>Find your next <span>great story.</span></h1><p>Explore niche-specific subtopics, avoid repeating past videos, and pick the angle you want to make next.</p></div><button className="button secondary" onClick={() => run('refresh-topics', async () => { const data = await api('/api/topics', { token }); setTopics(data.topics || []); setTopicsNote(data.note || ''); }, 'Fresh ideas loaded.')}><RefreshCw size={15} /> Refresh ideas</button></div>
          <div className="idea-layout"><div className="main-column">
            <div className="section-heading"><div><span className="section-kicker">CURATED FOR YOUR CHANNEL</span><h2>Fresh ideas from your niche <span className="count-pill">{topics.length}</span></h2></div><span className="muted-inline"><Activity size={14} />{topicsNote || 'Ideas are personalized to your saved seed topics.'}</span></div>
            {!seeds.length && <div className="notice info"><Lightbulb size={16} /> Add a few niche seed topics on the right to get personalized ideas.</div>}
            {topics.length ? <div className="topic-grid">{topics.map((item, index) => <article className="topic-card" key={`${item.topic}-${index}`}><div className="topic-card-top"><span className="topic-index">{String(index + 1).padStart(2, '0')}</span><span className={`score-chip ${item.needs_review ? '' : 'score-high'}`}>{item.source?.includes('rising') ? 'RISING TREND' : item.source?.includes('Google Trends') ? 'RELATED TREND' : 'FRESH ANGLE'}</span></div><h3>{item.topic}</h3><div className="topic-card-bottom"><span className="topic-tag">{item.source || (item.needs_review ? 'Review suggested' : 'Worth exploring')}</span><button className="text-action" onClick={() => generateScript(item.topic)}>Use this angle <ArrowRight size={14} /></button></div></article>)}</div> : <div className="notice info idea-empty"><Lightbulb size={16} /><span>{topicsNote || 'No fresh subtopics yet. Refresh ideas or add another seed topic to widen the search.'}</span></div>}
            <div className="research-card">
              <div className="research-icon"><Search size={18} /></div>
              <div className="research-copy">
                <h3>Find a fresh angle from any topic</h3>
                <p>Enter a seed or a topic you’ve already covered. We’ll suggest related, unmade ideas that are worth exploring.</p>
                <div className="research-row">
                  <input value={customTopic} onChange={e => { setCustomTopic(e.target.value); setResearched(null); }} placeholder="Enter a niche seed or topic…" onKeyDown={e => e.key === 'Enter' && research()} />
                  <button className="button primary" onClick={research} disabled={busyKey === 'research'}>{busyKey === 'research' ? <LoaderCircle className="spin" size={16} /> : <>Find fresh angles <ArrowRight size={15} /></>}</button>
                </div>
                {researched && <div className={`research-result ${researched.allowed ? 'success' : 'warning'}`}><CheckCircle2 size={16} /><span><b>{researched.covered ? 'You have covered this topic' : researched.allowed ? 'Topic looks promising' : 'Needs a closer look'}</b>{researched.covered ? ' · Here are fresh angles instead.' : researched.reason ? ` · ${researched.reason}` : ''}</span></div>}
                {researched?.allowed && !researched.covered && <button className="text-action manual-topic-action" type="button" onClick={() => generateScript(researched.topic)}>Make a video on “{researched.topic}” <ArrowRight size={14} /></button>}
                {researched?.recommendations?.length > 0 && <div className="related-ideas"><div className="related-ideas-heading"><b>Fresh angles related to “{researched.topic}”</b><small>{researched.recommendations_note}</small></div><div className="related-ideas-list">{researched.recommendations.map((item, index) => <button className="related-idea" type="button" key={`${item.topic}-${index}`} onClick={() => generateScript(item.topic)}><span><b>{item.topic}</b><small>{item.source || 'Related idea'}{item.needs_review ? ' · Review suggested' : ''}</small></span><ArrowRight size={15} /></button>)}</div></div>}
                {researched && !researched.recommendations?.length && <div className="research-hint">{researched.recommendations_note}</div>}
              </div>
            </div>
          </div><aside className="side-column"><div className="panel seed-panel"><div className="panel-heading"><div><span className="section-kicker">YOUR NICHE</span><h2>Seed topics</h2></div><span className="tiny-counter">{seeds.length}/20</span></div><p className="panel-description">Topics that guide the ideas we find for you.</p><div className="seed-list">{seeds.map(seed => <span className="seed-chip" key={seed}>{seed}<button aria-label={`Remove ${seed}`} onClick={() => saveSeeds(seeds.filter(item => item !== seed))}><X size={12} /></button></span>)}{!seeds.length && <div className="empty-mini">No seeds yet. Add your first niche below.</div>}</div><form className="seed-add" onSubmit={e => { e.preventDefault(); if (seedInput.trim() && seeds.length < 20) saveSeeds([...seeds, seedInput]); }}><input value={seedInput} onChange={e => setSeedInput(e.target.value)} placeholder="Add a topic…" maxLength={255} /><button aria-label="Add seed topic" disabled={!seedInput.trim() || seeds.length >= 20 || busyKey === 'seeds'}><Plus size={17} /></button></form><small className="helper-copy">Up to 20 topics · press enter to add</small></div>
            <div className="panel tip-panel"><div className="tip-mark"><Lightbulb size={16} /></div><span className="section-kicker">A QUICK TIP</span><p>Specific seed topics lead to sharper, more relevant video ideas.</p><button className="text-action" onClick={() => setActive('studio')}>Open script studio <ArrowRight size={14} /></button></div>
          </aside></div>
        </section>}

        {active === 'studio' && <section><div className="page-intro"><div><div className="eyebrow"><span className="live-dot" /> FROM IDEA TO FIRST DRAFT</div><h1>Your script <span>studio.</span></h1><p>Shape a topic into a ready-to-record script, then save it or start a video build.</p></div><div className="studio-badge"><WandSparkles size={16} /> AI-assisted writing</div></div><div className="studio-layout"><div className="panel studio-form"><div className="panel-heading"><div><span className="section-kicker">THE BRIEF</span><h2>What are we making?</h2></div><span className="step-pill">01 <span>/</span> 02</span></div><label>Topic<input value={scriptForm.topic} onChange={e => setScriptForm({ ...scriptForm, topic: e.target.value })} placeholder="e.g. Why small habits compound over time" /></label><div className="two-fields"><label>Target length<select value={scriptForm.duration} onChange={e => setScriptForm({ ...scriptForm, duration: e.target.value })}><option value="30">30 seconds · Short</option><option value="60">60 seconds · Standard</option><option value="90">90 seconds</option><option value="180">3 minutes</option><option value="300">5 minutes</option></select></label><label>Voice<select value={scriptForm.voice} onChange={e => setScriptForm({ ...scriptForm, voice: e.target.value })}>{VOICES.map(voice => <option key={voice}>{voice}</option>)}</select></label></div><button className="button primary full-button" disabled={busyKey === 'generate'} onClick={() => generateScript()}>{busyKey === 'generate' ? <><LoaderCircle className="spin" size={17} /> Working on it…</> : <><Sparkles size={16} /> Generate script <ArrowRight size={16} /></>}</button><div className="studio-note"><ShieldCheck size={15} /> Generated copy may need a human review before publishing.</div></div><div className="panel script-editor"><div className="panel-heading"><div><span className="section-kicker">YOUR DRAFT</span><h2>{scriptForm.title || 'Your story takes shape here'}</h2></div><span className="editor-status"><span className={scriptForm.script ? 'live-dot' : 'status-ring'} />{scriptForm.script ? 'Draft ready' : 'Waiting for a topic'}</span></div><label>Video title<input value={scriptForm.title} onChange={e => setScriptForm({ ...scriptForm, title: e.target.value })} placeholder="Your video title" /></label><label>Description<textarea rows="3" value={scriptForm.description} onChange={e => setScriptForm({ ...scriptForm, description: e.target.value })} placeholder="A short description for your video…" /></label><label>Script<textarea className="script-textarea" rows="12" value={scriptForm.script} onChange={e => setScriptForm({ ...scriptForm, script: e.target.value })} placeholder="Your generated script will appear here. You can edit it freely." /></label><div className="editor-footer"><span>{scriptForm.script.trim() ? scriptForm.script.trim().split(/\s+/).length : 0} words</span><div><button className="button secondary" disabled={!scriptForm.script || busyKey === 'save'} onClick={saveDraft}><FileText size={15} /> Save draft</button><button className="button primary" disabled={!scriptForm.script || busyKey === 'build'} onClick={buildVideo}><Film size={15} /> Build video</button></div></div></div></div></section>}

        {active === 'videos' && <section><div className="page-intro"><div><div className="eyebrow"><span className="live-dot" /> YOUR CONTENT, ALL IN ONE PLACE</div><h1>The video <span>library.</span></h1><p>Keep track of your drafts, builds, and finished videos.</p></div><button className="button primary" onClick={() => { setScriptForm(current => ({ ...current, topic: '' })); setActive('studio'); }}><Plus size={16} /> New video</button></div><div className="library-toolbar"><div className="filter-tabs">{['all', 'draft', 'building', 'ready', 'uploaded', 'build_failed'].map(item => <button key={item} className={filter === item ? 'active' : ''} onClick={() => setFilter(item)}>{item === 'all' ? 'All projects' : item.replace('_', ' ')}</button>)}</div><button className="icon-button" title="Refresh videos" onClick={() => run('videos-refresh', refreshVideos)}><RefreshCw size={16} /></button></div>{filteredVideos.length ? <div className="video-grid">{filteredVideos.map(video => <article className="video-card" key={video.local_id}><div className="video-preview">{video.has_video ? <video controls preload="none" src={mediaUrl(video.video_url)} /> : <div className="video-placeholder"><Film size={26} /><span>{video.status === 'building' ? 'Your video is rendering' : 'No video preview yet'}</span></div>}<span className={`status-badge status-${video.status}`}>{video.status.replaceAll('_', ' ')}</span></div><div className="video-card-body"><div className="section-kicker">{video.topic}</div><h3>{video.title}</h3><p>{video.description || 'No description added.'}</p>{video.status === 'building' && <div className="video-progress"><div className="video-progress-bar"><span style={{ width: `${getVideoProgress(video)}%` }} /></div><small>{getVideoProgressLabel(video)}</small></div>}{video.status !== 'building' && <div className="video-progress compact"><small>{getVideoProgressLabel(video)}</small></div>}<div className="video-meta">
          <span><Clock3 size={13} />{video.created_at ? new Date(video.created_at).toLocaleDateString() : 'Just now'}</span>
          <span>{video.voice}</span>
        </div><div className="video-actions">{video.has_video && <a className="button secondary" href={mediaUrl(video.video_url)} target="_blank" rel="noreferrer"><Film size={14} /> Preview</a>}{video.has_video && <button className="button primary" onClick={() => videoAction(video, 'upload')} disabled={busyKey === `upload-${video.local_id}`}><Upload size={14} /> Upload</button>}{!video.has_video && video.status === 'draft' && <button className="button secondary" onClick={() => { setScriptForm({ topic: video.topic, title: video.title, description: video.description, script: video.script, voice: video.voice, duration: 60 }); setActive('studio'); }}><FileText size={14} /> Edit draft</button>}<button className="icon-button danger-quiet" title="Delete project" onClick={() => videoAction(video, 'delete')}><X size={15} /></button></div></div></article>)}</div> : <div className="empty-state"><div className="empty-icon"><Layers3 size={23} /></div><h3>{filter === 'all' ? 'Your library is ready for its first project.' : `No ${filter.replace('_', ' ')} projects.`}</h3><p>Start with a topic idea and build your first video from the script studio.</p><button className="button primary" onClick={() => setActive('studio')}><Sparkles size={15} /> Start a script</button></div>}</section>}

        {active === 'analytics' && <section><div className="page-intro"><div><div className="eyebrow"><span className="live-dot" /> LEARN FROM EVERY PUBLISH</div><h1>Ideas that <span>keep getting smarter.</span></h1><p>Track topic performance and feed real-world results into your next round of ideas.</p></div><button className="button secondary" onClick={() => run('analytics-refresh', async () => setAnalytics(await api('/api/analytics', { token })), 'Performance refreshed.')}><RefreshCw size={15} /> Refresh</button></div><div className="metric-grid"><div className="metric-card"><span className="metric-label">TOPICS LEARNED</span><b>{analytics.total_learned_topics || 0}</b><small><Layers3 size={14} /> Tracked in your workspace</small></div><div className="metric-card"><span className="metric-label">AVERAGE SCORE</span><b>{analytics.summary?.avg_score ? `${Math.round(analytics.summary.avg_score * 100)}%` : '—'}</b><small><Gauge size={14} /> Across reported topics</small></div><div className="metric-card metric-featured"><span className="metric-label">TOP PERFORMER</span><b>{analytics.summary?.top_performing || 'Not yet reported'}</b><small><ArrowUpRight size={14} /> Your current strongest topic</small></div></div><div className="panel performance-panel"><div className="panel-heading"><div><span className="section-kicker">TOPIC HISTORY</span><h2>Performance signals</h2></div><span className="muted-inline">Score is a 0–100% signal</span></div>{analytics.topics?.length ? <div className="table-scroll"><table><thead><tr><th>TOPIC</th><th>SCORE</th><th>ATTEMPTS</th><th>LAST VIEWS</th><th>REPORT RESULT</th></tr></thead><tbody>{analytics.topics.map(item => <tr key={item.topic}><td><b>{item.topic}</b></td><td><div className="score-cell"><span className="score-bar"><i style={{ width: `${Math.max(0, Math.min(100, item.score * 100))}%` }} /></span>{Math.round(item.score * 100)}%</div></td><td>{item.attempts}</td><td>{item.last_stats?.views ?? '—'}</td><td><form className="feedback-form" onSubmit={event => sendFeedback(item, event)}><select name="score" defaultValue="0.7" aria-label="Performance score"><option value="1">Great</option><option value="0.7">Good</option><option value="0.4">Average</option><option value="0.1">Low</option></select><input name="views" type="number" min="0" placeholder="Views" aria-label="Views" /><input name="subscribers" type="number" min="0" placeholder="Subs" aria-label="Subscribers gained" /><input name="attempts" type="hidden" value="1" /><button className="icon-button submit-feedback" title="Save result" disabled={busyKey === `feedback-${item.topic}`}><Send size={14} /></button></form></td></tr>)}</tbody></table></div> : <div className="empty-state compact"><div className="empty-icon"><BarChart3 size={22} /></div><h3>No performance data yet</h3><p>After a topic is used, report its results here to improve future recommendations.</p></div>}</div></section>}

        {active === 'settings' && <section><div className="page-intro"><div><div className="eyebrow"><span className="live-dot" /> MAKE THIS SPACE YOURS</div><h1>Workspace <span>settings.</span></h1><p>Connection health, channel preferences, and integrations.</p></div><button className="button secondary" onClick={() => run('settings-refresh', loadWorkspace)}><RefreshCw size={15} /> Refresh status</button></div><div className="settings-layout"><div className="panel settings-panel"><div className="panel-heading"><div><span className="section-kicker">CHANNEL DEFAULTS</span><h2>Publishing preferences</h2></div></div><form className="settings-form" onSubmit={saveSettings}><label>Channel name<input value={settings.channel_name} onChange={e => setSettings({ ...settings, channel_name: e.target.value })} disabled={!user.is_admin} /></label><div className="two-fields"><label>Target duration (seconds)<input type="number" min="15" max="600" value={settings.target_seconds} onChange={e => setSettings({ ...settings, target_seconds: e.target.value })} disabled={!user.is_admin} /></label><label>Default privacy<select value={settings.default_privacy} onChange={e => setSettings({ ...settings, default_privacy: e.target.value })} disabled={!user.is_admin}><option value="private">Private</option><option value="unlisted">Unlisted</option><option value="public">Public</option></select></label></div><label>Narration voice<select value={settings.voice} onChange={e => setSettings({ ...settings, voice: e.target.value })} disabled={!user.is_admin}>{VOICES.map(voice => <option key={voice}>{voice}</option>)}</select></label>{user.is_admin && <label>Pexels API key (optional)<input type="password" autoComplete="off" value={settings.pexels_api_key} onChange={e => setSettings({ ...settings, pexels_api_key: e.target.value })} placeholder="Leave blank to keep existing key" /></label>}<div className="settings-submit"><span>{user.is_admin ? 'Admin changes apply to the backend workspace.' : 'Only admins can change channel defaults.'}</span>{user.is_admin && <button className="button primary" disabled={busyKey === 'settings'}><Check size={15} /> Save settings</button>}</div></form></div><div className="side-column settings-side"><div className="panel health-panel"><div className="panel-heading"><div><span className="section-kicker">SERVICE HEALTH</span><h2>Database</h2></div><span className={`health-icon ${db?.connected ? '' : 'unhealthy'}`}>{db?.connected ? <CheckCircle2 size={17} /> : <Activity size={17} />}</span></div><div className="health-row"><span>Provider</span><b>Supabase Postgres</b></div><div className="health-row"><span>API</span><b className="health-value"><span className={`connection-dot ${db?.connected ? '' : 'off'}`} />{db?.connected ? 'Connected' : 'Unavailable'}</b></div><p className="health-message">{db?.message || 'Checking database status…'}</p></div><div className="panel integrations-panel"><div className="panel-heading"><div><span className="section-kicker">CONNECTED SERVICES</span><h2>Integrations</h2></div></div>{[['Pexels media', config?.integrations?.pexels_configured], ['YouTube client', config?.integrations?.youtube_client_secret], ['YouTube account', config?.integrations?.youtube_authenticated], ['AI provider', config?.integrations?.anthropic_configured]].map(([label, ok]) => <div className="integration-row" key={label}><span>{label}</span><span className={`integration-state ${ok ? 'ok' : ''}`}><i />{ok ? 'Connected' : 'Not set up'}</span></div>)}</div></div></div></section>}
      </div>
      <footer className="page-footer"><span>StudioFlow · Creator workspace</span><span><span className={`connection-dot ${db?.connected ? '' : 'off'}`} /> {db?.connected ? 'All systems operational' : 'Database connection needs attention'}</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
