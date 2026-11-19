import { Platform } from 'react-native';
import { getWebCsrfToken } from './auth/AuthClients';
import { getApiBaseUrl } from './auth/ApiBaseUrl';

const isWeb = Platform.OS === 'web';
const API = getApiBaseUrl();

// The edit form works on flat strings: skills are comma separated, bullets are one per line.
export type Entry = { organization: string; title: string; start: string; end: string; bullets: string };
export type Resume = {
  name: string; headline: string; email: string; phone: string; location: string; summary: string; skills: string;
  experience: Entry[]; education: Entry[];
  hidden: string[]; // fields left off the public page, e.g. "contact.phone"
  links: unknown[]; projects: unknown[]; // kept from the upload as-is; not editable yet
};
export type Theme = { accent?: string; font?: string };
export type Draft = { slug?: string; resume: Resume; template_id: string; theme: Theme };
export type Portfolio = Draft & { slug: string; url: string };

// Template -> its default accent color (backend/portfolio/themes.py)
export const TEMPLATES: Record<string, string> = { modern: '#1e3a8a', classic: '#8b2e2e', minimal: '#b4321f', dark: '#fbbf24' };
export const EMPTY_ENTRY: Entry = { organization: '', title: '', start: '', end: '', bullets: '' };
export const EMPTY_RESUME: Resume = {
  name: '', headline: '', email: '', phone: '', location: '', summary: '', skills: '',
  experience: [], education: [], hidden: [], links: [], projects: [],
};

export const slugify = (name: string) =>
  name.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);

// Form shape <-> backend Resume schema (backend/portfolio/schema.py)
const orNull = (v: string) => v.trim() || null;
const lines = (v: string) => v.split('\n').map((x) => x.trim()).filter(Boolean);
const toEntry = (e: Entry) => ({ organization: e.organization.trim(), title: orNull(e.title), start: orNull(e.start), end: orNull(e.end), bullets: lines(e.bullets) });
const fromEntry = (e: any): Entry => ({ organization: e.organization ?? '', title: e.title ?? '', start: e.start ?? '', end: e.end ?? '', bullets: (e.bullets ?? []).join('\n') });

const toApi = (r: Resume) => ({
  contact: { name: r.name.trim(), headline: orNull(r.headline), email: orNull(r.email), phone: orNull(r.phone), location: orNull(r.location), links: r.links },
  summary: orNull(r.summary),
  experience: r.experience.filter((e) => e.organization.trim()).map(toEntry),
  education: r.education.filter((e) => e.organization.trim()).map(toEntry),
  projects: r.projects,
  skills: r.skills.split(',').map((x) => x.trim()).filter(Boolean),
  hidden_fields: r.hidden,
});
const fromApi = (d: any): Resume => ({
  name: d.contact?.name ?? '', headline: d.contact?.headline ?? '', email: d.contact?.email ?? '',
  phone: d.contact?.phone ?? '', location: d.contact?.location ?? '', summary: d.summary ?? '',
  skills: (d.skills ?? []).join(', '), experience: (d.experience ?? []).map(fromEntry), education: (d.education ?? []).map(fromEntry),
  hidden: d.hidden_fields ?? [], links: d.contact?.links ?? [], projects: d.projects ?? [],
});

// Every call goes through here. Web logs in with HttpOnly cookies (+ CSRF header); native sends the access token.
async function call<T>(path: string, init: RequestInit = {}, token?: string | null, timeoutMs = 15000): Promise<T> {
  const csrf = isWeb ? getWebCsrfToken() : undefined;
  const headers: Record<string, string> = {
    'X-Client-Platform': isWeb ? 'web' : 'native',
    ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    ...(!isWeb && token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init.headers as Record<string, string>),
  };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    let res: Response;
    try {
      res = await fetch(API + path, { ...init, headers, credentials: isWeb ? 'include' : 'omit', signal: controller.signal });
    } catch {
      throw new Error(controller.signal.aborted ? 'The server took too long. Try again.' : 'Cannot reach the server. Is the backend running?');
    }
    if (res.status === 401) throw new Error('Your session expired. Log in again.');
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      if (typeof body.detail === 'string') throw new Error(body.detail);
      throw new Error(res.status === 422 ? 'Check your fields: a valid email, and dates like 2024-06.' : `Something went wrong (${res.status}).`);
    }
    if (res.status === 204) return undefined as T;
    return (res.headers.get('content-type')?.includes('json') ? res.json() : res.text()) as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } });

export async function extractResume(file: { uri: string; name: string; mimeType?: string; file?: File }, token?: string | null): Promise<Resume> {
  const form = new FormData();
  // Browsers need the real File object; native sends a { uri, name, type } descriptor.
  form.append('file', isWeb && file.file ? file.file : ({ uri: file.uri, name: file.name, type: file.mimeType ?? 'application/pdf' } as any));
  return fromApi(await call('/resume/upload', { method: 'POST', body: form }, token, 60000)); // Claude takes ~5-15 s
}

export const previewHtml = (resume: Resume, template_id: string, theme: Theme) =>
  call<string>('/portfolio/preview', json('POST', { resume: toApi(resume), template_id, theme }));

export const listPortfolios = async (token?: string | null): Promise<Portfolio[]> =>
  (await call<any[]>('/portfolios', {}, token)).map((p) => ({ ...p, resume: fromApi(p.resume) }));

export const savePortfolio = (token: string | null | undefined, slug: string, { resume, template_id, theme }: Draft) =>
  call<Portfolio>(`/portfolios/${slug}`, json('PUT', { resume: toApi(resume), template_id, theme }), token);

export const deletePortfolio = (token: string | null | undefined, slug: string) =>
  call<void>(`/portfolios/${slug}`, { method: 'DELETE' }, token);
