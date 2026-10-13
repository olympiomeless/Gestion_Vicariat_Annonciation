import { api, fileDownloadUrl, uploadWithProgress } from './client';
import type {
  ActualiteOut,
  AdminDashboardStats,
  AuditLogOut,
  BureauMemberOut,
  CourrierKind,
  CourrierOut,
  CourrierStatus,
  DocumentCategory,
  DocumentOut,
  EffectifCategorieOut,
  GalleryPhotoOut,
  MouvementContent,
  NotificationOut,
  Paginated,
  ProgrammeOut,
  Section,
  SectionBureauMemberOut,
  SectionCreateResult,
  SectionDashboardStats,
  UserAdminOut,
} from './types';

function qs(params: object): string {
  const usable = Object.entries(params as Record<string, string | number | boolean | undefined | null>).filter(
    ([, v]) => v !== undefined && v !== null && v !== ''
  );
  if (usable.length === 0) return '';
  const search = new URLSearchParams(usable.map(([k, v]) => [k, String(v)]));
  return `?${search.toString()}`;
}

// ---------- Sections ----------
export const sectionsApi = {
  list: (includeInactive = false) => api.get<Section[]>(`/sections${qs({ include_inactive: includeInactive ? 'true' : undefined })}`),
  get: (id: string) => api.get<Section>(`/sections/${id}`),
  // `username` est optionnel : s'il est renseigné, le compte de connexion de
  // la section (rôle SECTION) est créé dans la même opération, avec un mot
  // de passe par défaut généré côté serveur — voir SectionCreateResult.
  create: (payload: Partial<Section> & { slug: string; name: string; username?: string }) =>
    api.post<SectionCreateResult>('/sections', payload),
  update: (id: string, payload: Partial<Section>) => api.put<Section>(`/sections/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/sections/${id}`),
  photoUrl: (id: string) => fileDownloadUrl(`/public/sections/${id}/photo`),
  uploadPhoto: (id: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    return uploadWithProgress<Section>(`/sections/${id}/photo`, 'POST', form, onProgress ?? (() => {}));
  },
  removePhoto: (id: string) => api.delete<Section>(`/sections/${id}/photo`),
};

// ---------- Users ----------
export interface UserCreatePayload {
  username: string;
  email?: string | null;
  full_name: string;
  password: string;
  role: string;
  section_id?: string | null;
}
export interface UserUpdatePayload {
  full_name?: string;
  role?: string;
  section_id?: string | null;
}
export const usersApi = {
  list: () => api.get<UserAdminOut[]>('/users'),
  create: (payload: UserCreatePayload) => api.post<UserAdminOut>('/users', payload),
  update: (id: string, payload: UserUpdatePayload) => api.put<UserAdminOut>(`/users/${id}`, payload),
  deactivate: (id: string) => api.post<UserAdminOut>(`/users/${id}/deactivate`, {}),
  reactivate: (id: string) => api.post<UserAdminOut>(`/users/${id}/reactivate`, {}),
  remove: (id: string) => api.delete<void>(`/users/${id}`),
  resetPassword: (id: string, new_password: string) => api.post<void>(`/users/${id}/reset-password`, { new_password }),
};

// ---------- Authentification (compte connecté) ----------
export const authApi = {
  changePassword: (current_password: string, new_password: string) =>
    api.post<void>('/auth/change-password', { current_password, new_password }),
};

// ---------- Document categories ----------
export const categoriesApi = {
  list: () => api.get<DocumentCategory[]>('/documents/categories'),
  create: (name: string) => api.post<DocumentCategory>('/documents/categories', { name }),
  remove: (id: string) => api.delete<void>(`/documents/categories/${id}`),
};

// ---------- Documents ----------
export interface DocumentListParams {
  section_id?: string;
  category_id?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}
export const documentsApi = {
  list: (params: DocumentListParams) => api.get<Paginated<DocumentOut>>(`/documents${qs(params)}`),
  get: (id: string) => api.get<DocumentOut>(`/documents/${id}`),
  update: (id: string, payload: { name?: string; description?: string; category_id?: string }) =>
    api.put<DocumentOut>(`/documents/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/documents/${id}`),
  approve: (id: string) => api.post<DocumentOut>(`/documents/${id}/approve`, {}),
  reject: (id: string, reason: string) => api.post<DocumentOut>(`/documents/${id}/reject`, { reason }),
  upload: (
    fields: { name: string; description?: string; category_id: string; section_id?: string },
    file: File,
    onProgress?: (pct: number) => void
  ) => {
    const form = new FormData();
    form.append('name', fields.name);
    if (fields.description) form.append('description', fields.description);
    form.append('category_id', fields.category_id);
    if (fields.section_id) form.append('section_id', fields.section_id);
    form.append('file', file);
    return uploadWithProgress<DocumentOut>('/documents', 'POST', form, onProgress ?? (() => {}));
  },
  downloadUrl: (id: string) => `/documents/${id}/download`,
};

// ---------- Actualités ----------
export const actualitesApi = {
  list: (params: { section_id?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<Paginated<ActualiteOut>>(`/actualites${qs(params)}`),
  get: (id: string) => api.get<ActualiteOut>(`/actualites/${id}`),
  create: (payload: { title: string; body: string; section_id?: string }) => api.post<ActualiteOut>('/actualites', payload),
  update: (id: string, payload: { title?: string; body?: string }) => api.put<ActualiteOut>(`/actualites/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/actualites/${id}`),
  submit: (id: string) => api.post<ActualiteOut>(`/actualites/${id}/submit`, {}),
  approve: (id: string) => api.post<ActualiteOut>(`/actualites/${id}/approve`, {}),
  reject: (id: string, reason: string) => api.post<ActualiteOut>(`/actualites/${id}/reject`, { reason }),
};

// ---------- Programme ----------
export const programmeApi = {
  list: (params: { section_id?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<Paginated<ProgrammeOut>>(`/programme${qs(params)}`),
  get: (id: string) => api.get<ProgrammeOut>(`/programme/${id}`),
  create: (payload: {
    title: string;
    description?: string;
    activity_date: string;
    activity_time?: string;
    location?: string;
    target_audience?: string;
    section_id?: string;
  }) => api.post<ProgrammeOut>('/programme', payload),
  update: (
    id: string,
    payload: Partial<{
      title: string;
      description: string;
      activity_date: string;
      activity_time: string;
      location: string;
      target_audience: string;
    }>
  ) => api.put<ProgrammeOut>(`/programme/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/programme/${id}`),
  approve: (id: string) => api.post<ProgrammeOut>(`/programme/${id}/approve`, {}),
  reject: (id: string, reason: string) => api.post<ProgrammeOut>(`/programme/${id}/reject`, { reason }),
};

// ---------- Gallery ----------
export const galleryApi = {
  list: (params: { section_id?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<Paginated<GalleryPhotoOut>>(`/gallery${qs(params)}`),
  get: (id: string) => api.get<GalleryPhotoOut>(`/gallery/${id}`),
  update: (id: string, caption: string) => api.put<GalleryPhotoOut>(`/gallery/${id}`, { caption }),
  remove: (id: string) => api.delete<void>(`/gallery/${id}`),
  approve: (id: string) => api.post<GalleryPhotoOut>(`/gallery/${id}/approve`, {}),
  reject: (id: string, reason: string) => api.post<GalleryPhotoOut>(`/gallery/${id}/reject`, { reason }),
  upload: (fields: { caption?: string; section_id?: string; programme_id?: string }, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    if (fields.caption) form.append('caption', fields.caption);
    if (fields.section_id) form.append('section_id', fields.section_id);
    if (fields.programme_id) form.append('programme_id', fields.programme_id);
    form.append('file', file);
    return uploadWithProgress<GalleryPhotoOut>('/gallery', 'POST', form, onProgress ?? (() => {}));
  },
  fileUrl: (id: string) => `/gallery/${id}/file`,
};

// ---------- Bureau ----------
export const bureauApi = {
  list: () => api.get<BureauMemberOut[]>('/bureau'),
  create: (payload: {
    full_name: string;
    role_title: string;
    paroisse?: string;
    rang?: string;
    display_order?: number;
    is_active?: boolean;
  }) => api.post<BureauMemberOut>('/bureau', payload),
  update: (
    id: string,
    payload: Partial<{ full_name: string; role_title: string; paroisse: string; rang: string; display_order: number; is_active: boolean }>
  ) => api.put<BureauMemberOut>(`/bureau/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/bureau/${id}`),
  photoUrl: (id: string) => fileDownloadUrl(`/public/bureau/${id}/photo`),
  uploadPhoto: (id: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    return uploadWithProgress<BureauMemberOut>(`/bureau/${id}/photo`, 'POST', form, onProgress ?? (() => {}));
  },
  removePhoto: (id: string) => api.delete<BureauMemberOut>(`/bureau/${id}/photo`),
};

// ---------- Bureau de section (propre à chaque section, distinct du Bureau
// du Vicariat ci-dessus — soumis à validation de l'administrateur) ----------
export const sectionBureauApi = {
  list: (params: { section_id?: string; status?: string } = {}) =>
    api.get<SectionBureauMemberOut[]>(`/section-bureau${qs(params)}`),
  get: (id: string) => api.get<SectionBureauMemberOut>(`/section-bureau/${id}`),
  create: (payload: { full_name: string; role_title: string; display_order?: number; section_id?: string }) =>
    api.post<SectionBureauMemberOut>('/section-bureau', payload),
  update: (id: string, payload: Partial<{ full_name: string; role_title: string; display_order: number }>) =>
    api.put<SectionBureauMemberOut>(`/section-bureau/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/section-bureau/${id}`),
  approve: (id: string) => api.post<SectionBureauMemberOut>(`/section-bureau/${id}/approve`, {}),
  reject: (id: string, reason: string) => api.post<SectionBureauMemberOut>(`/section-bureau/${id}/reject`, { reason }),
  // Contrairement aux photos du Bureau du Vicariat (publiques), celles du
  // bureau de section ne sont pas exposées sans authentification : l'aperçu
  // doit passer par fetchAsObjectUrl (voir SectionBureauPage), pas un <img
  // src> direct — ce chemin relatif est fait pour cet usage, pas pour
  // fileDownloadUrl.
  photoPath: (id: string) => `/section-bureau/${id}/photo`,
  uploadPhoto: (id: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    return uploadWithProgress<SectionBureauMemberOut>(`/section-bureau/${id}/photo`, 'POST', form, onProgress ?? (() => {}));
  },
  removePhoto: (id: string) => api.delete<SectionBureauMemberOut>(`/section-bureau/${id}/photo`),
};

// ---------- Courriers (messages / demandes de fichiers entre une section et
// le Bureau du Vicariat — voir backend/app/api/v1/courriers.py) ----------
export const courrierApi = {
  list: (params: { section_id?: string; status?: CourrierStatus; kind?: CourrierKind } = {}) =>
    api.get<CourrierOut[]>(`/courriers${qs(params)}`),
  get: (id: string) => api.get<CourrierOut>(`/courriers/${id}`),
  create: (
    fields: { kind: CourrierKind; subject: string; body: string; section_id?: string },
    file: File | null,
    onProgress?: (pct: number) => void
  ) => {
    const form = new FormData();
    form.append('kind', fields.kind);
    form.append('subject', fields.subject);
    form.append('body', fields.body);
    if (fields.section_id) form.append('section_id', fields.section_id);
    if (file) form.append('file', file);
    return uploadWithProgress<CourrierOut>('/courriers', 'POST', form, onProgress ?? (() => {}));
  },
  remove: (id: string) => api.delete<void>(`/courriers/${id}`),
  respond: (id: string, responseNote: string, file: File | null, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    if (responseNote) form.append('response_note', responseNote);
    if (file) form.append('file', file);
    return uploadWithProgress<CourrierOut>(`/courriers/${id}/respond`, 'POST', form, onProgress ?? (() => {}));
  },
  attachmentUrl: (id: string) => `/courriers/${id}/attachment`,
  responseFileUrl: (id: string) => `/courriers/${id}/response-file`,
};

// ---------- Effectifs ----------
export const effectifsApi = {
  list: () => api.get<EffectifCategorieOut[]>('/effectifs'),
  create: (payload: { categorie: string; effectif: number; display_order?: number }) =>
    api.post<EffectifCategorieOut>('/effectifs', payload),
  update: (id: string, payload: Partial<{ effectif: number; display_order: number }>) =>
    api.put<EffectifCategorieOut>(`/effectifs/${id}`, payload),
  remove: (id: string) => api.delete<void>(`/effectifs/${id}`),
};

// ---------- Le mouvement (contenu éditorial du site public) ----------
export type MouvementUpdatePayload = Partial<Omit<MouvementContent, 'id' | 'updated_at'>>;
export const mouvementApi = {
  get: () => api.get<MouvementContent>('/mouvement'),
  update: (payload: MouvementUpdatePayload) => api.put<MouvementContent>('/mouvement', payload),
};

// ---------- Dashboard ----------
export const dashboardApi = {
  admin: () => api.get<AdminDashboardStats>('/dashboard/admin'),
  section: (sectionId?: string) => api.get<SectionDashboardStats>(`/dashboard/section${qs({ section_id: sectionId })}`),
};

// ---------- Notifications ----------
export const notificationsApi = {
  list: (page = 1, pageSize = 20) => api.get<Paginated<NotificationOut> & { unread_count: number }>(`/notifications${qs({ page, page_size: pageSize })}`),
  markRead: (id: string) => api.put<NotificationOut>(`/notifications/${id}/read`, {}),
  markAllRead: () => api.put<{ marked: number } | Record<string, unknown>>('/notifications/read-all', {}),
};

// ---------- Audit log ----------
export interface AuditLogParams {
  action?: string;
  resource_type?: string;
  user_id?: string;
  result?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}
export const auditLogApi = {
  list: (params: AuditLogParams) => api.get<Paginated<AuditLogOut>>(`/audit-logs${qs(params)}`),
};
