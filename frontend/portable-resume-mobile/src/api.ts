import { Platform } from 'react-native';
declare const process: any;

// Android emulator reaches your computer at 10.0.2.2. On a real phone set the EXPO_PUBLIC_* vars to your computer's LAN IP.
const HOST = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
const API = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, '') || `http://${HOST}:8000`; // FastAPI backend
export const USE_SAMPLE_DATA = true; // resume scan is still a stub on the backend; set false when /resume/upload works

export type Entry = { organization: string; title: string; start: string; end: string; bullets: string };
export type Resume = { name: string; headline: string; email: string; phone: string; location: string; summary: string; skills: string; experience: Entry[]; education: Entry[] };
export type Tpl = { id: string; accent: string; font: string };

export const EMPTY_ENTRY: Entry = { organization: '', title: '', start: '', end: '', bullets: '' };
export const SAMPLE: Resume = {
  name: 'Jordan Lee', headline: 'UX Designer', email: 'jordan@example.com', phone: '', location: 'San Jose, CA',
  summary: 'Design student focused on accessible, human-centered products.',
  skills: 'Figma, User research, HTML/CSS, Prototyping',
  experience: [{ organization: 'SJSU Design Lab', title: 'Research Assistant', start: '2025-01', end: '', bullets: 'Ran 12 usability studies\nShipped a redesigned onboarding flow' }],
  education: [{ organization: 'San José State University', title: 'B.A. Design', start: '2023-08', end: '2027-05', bullets: '' }],
};
export const DEFAULT_TPLS: Tpl[] = [
  { id: 'classic', accent: '#1e3a8a', font: 'serif' }, { id: 'modern', accent: '#0f766e', font: 'sans' },
  { id: 'minimal', accent: '#475569', font: 'mono' }, { id: 'dark', accent: '#3f3f46', font: 'sans' },
];

const json = { 'Content-Type': 'application/json' };
export const errorMessage = (e: unknown) => e instanceof Error ? e.message : 'Something went wrong. Please try again.';

// Keep the timeout active while the response body is being read too.
async function request<T>(url: string, options: RequestInit, read: (res: Response) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try { return await read(await fetch(url, { ...options, signal: controller.signal })); }
  catch (e) {
    if (controller.signal.aborted) throw new Error('The server took too long. Please try again.');
    if (e instanceof TypeError) throw new Error('Cannot reach the server. Check its address and connection, or use demo mode.');
    throw e;
  } finally { clearTimeout(timeout); }
}
const serverMessage = (d: any, fallback: string): string => {
  const message = d?.detail?.message ?? d?.message ?? d?.detail;
  return typeof message === 'string' ? message : fallback;
};
const nz = (v: string) => (v.trim() ? v.trim() : null);
const lines = (v: string) => v.split('\n').map((x) => x.trim()).filter(Boolean);
const toEntry = (e: Entry) => ({ organization: e.organization.trim(), title: nz(e.title), start: nz(e.start), end: nz(e.end), bullets: lines(e.bullets) });
const fromEntry = (e: any): Entry => ({ organization: e.organization ?? '', title: e.title ?? '', start: e.start ?? '', end: e.end ?? '', bullets: (e.bullets ?? []).join('\n') });

// App shape <-> backend Resume schema (backend/portfolio/schema.py)
export const toApi = (r: Resume) => ({
  contact: { name: r.name.trim(), headline: nz(r.headline), email: nz(r.email), phone: nz(r.phone), location: nz(r.location), links: [] },
  summary: nz(r.summary),
  education: r.education.filter((e) => e.organization.trim()).map(toEntry),
  experience: r.experience.filter((e) => e.organization.trim()).map(toEntry),
  projects: [],
  skills: r.skills.split(',').map((x) => x.trim()).filter(Boolean),
  hidden_fields: [],
});
const fromApi = (d: any): Resume => ({
  name: d.contact?.name ?? '', headline: d.contact?.headline ?? '', email: d.contact?.email ?? '', phone: d.contact?.phone ?? '',
  location: d.contact?.location ?? '', summary: d.summary ?? '', skills: (d.skills ?? []).join(', '),
  experience: (d.experience ?? []).map(fromEntry), education: (d.education ?? []).map(fromEntry),
});

export async function extractResume(f: { uri: string; name: string; mimeType?: string }): Promise<Resume> {
  if (USE_SAMPLE_DATA) {
    await new Promise<void>((resolve) => setTimeout(resolve, 500));
    return JSON.parse(JSON.stringify(SAMPLE)) as Resume;
  }
  const form = new FormData();
  form.append('file', { uri: f.uri, name: f.name, type: f.mimeType ?? 'application/pdf' } as any);
  return request(`${API}/resume/upload`, { method: 'POST', body: form }, async (res) => {
    if (!res.ok) throw new Error('Could not read that file.');
    try { return fromApi(await res.json()); }
    catch { throw new Error('The server returned an unreadable resume. Please try another file.'); }
  });
}

export async function getTemplates(): Promise<Tpl[]> {
  try {
    return await request(`${API}/portfolio/templates`, {}, async (res) => {
      if (!res.ok) return DEFAULT_TPLS;
      const d = await res.json();
      if (!Array.isArray(d?.templates)) return DEFAULT_TPLS;
      const valid: Tpl[] = d.templates.filter((t: any) => t && typeof t.id === 'string' && t.id.trim() && typeof t.accent === 'string' && /^#[0-9a-f]{6}$/i.test(t.accent) && typeof t.font === 'string');
      const unique = valid.filter((t, i) => valid.findIndex((other) => other.id === t.id) === i);
      // Keep the four built-in colors consistent with the local picker.
      return unique.length ? unique.map((t) => ({
        ...t, accent: DEFAULT_TPLS.find((preset) => preset.id === t.id)?.accent ?? t.accent,
      })) : DEFAULT_TPLS;
    });
  } catch { return DEFAULT_TPLS; }
}

export async function previewHtml(resume: Resume, template_id: string, theme: { accent?: string; font?: string }): Promise<string> {
  const previewTheme = {
    ...theme,
    accent: theme.accent ?? DEFAULT_TPLS.find((t) => t.id === template_id)?.accent,
  };
  return request(`${API}/portfolio/preview`, {
    method: 'POST', headers: json, body: JSON.stringify({ resume: toApi(resume), template_id, theme: previewTheme }),
  }, async (res) => {
    if (res.status === 422) {
      const d = await res.json().catch(() => ({}));
      throw new Error(serverMessage(d, 'Check your resume fields (valid email, dates like 2024-06).'));
    }
    if (!res.ok) throw new Error('Preview failed. Check that the portfolio backend is running.');
    const html = await res.text();
    if (!html.trim()) throw new Error('The server returned an empty preview.');
    return html;
  });
}
