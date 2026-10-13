export type RoleName = 'ADMIN' | 'SECTION';

export type DocumentStatus = 'EN_ATTENTE' | 'PUBLIE' | 'REFUSE';
export type ActualiteStatus = 'BROUILLON' | 'SOUMIS' | 'PUBLIE' | 'REFUSE';

export interface UserOut {
  id: string;
  username: string;
  email: string | null;
  full_name: string;
  role: RoleName;
  section_id: string | null;
  section_slug: string | null;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserOut;
}

export interface UserAdminOut {
  id: string;
  username: string;
  email: string | null;
  full_name: string;
  role: RoleName;
  section_id: string | null;
  section_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Section {
  id: string;
  slug: string;
  name: string;
  badge_label: string | null;
  quartier: string | null;
  responsable_name: string | null;
  description: string | null;
  effectif_total: number;
  photo_url: string | null;
  has_photo: boolean;
  is_active: boolean;
  display_order: number;
}

// Réponse à la création d'une section : si un compte a été créé en même
// temps (voir sectionsApi.create), le mot de passe généré n'apparaît QU'ICI,
// une seule fois — jamais récupérable ensuite.
export interface SectionCreateResult extends Section {
  generated_username: string | null;
  generated_password: string | null;
}

export interface DocumentCategory {
  id: string;
  name: string;
  is_system: boolean;
}

export interface DocumentOut {
  id: string;
  name: string;
  description: string | null;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  category_id: string;
  category_name: string | null;
  section_id: string | null;
  section_name: string | null;
  author_id: string;
  author_name: string | null;
  status: DocumentStatus;
  rejection_reason: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ActualiteOut {
  id: string;
  title: string;
  body: string;
  section_id: string | null;
  section_name: string | null;
  author_id: string;
  author_name: string | null;
  status: ActualiteStatus;
  rejection_reason: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProgrammeOut {
  id: string;
  title: string;
  description: string | null;
  activity_date: string;
  activity_time: string | null;
  location: string | null;
  target_audience: string | null;
  section_id: string | null;
  section_name: string | null;
  author_id: string;
  author_name: string | null;
  status: DocumentStatus;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface GalleryPhotoOut {
  id: string;
  caption: string | null;
  original_filename: string;
  section_id: string | null;
  section_name: string | null;
  programme_id: string | null;
  author_id: string;
  author_name: string | null;
  status: DocumentStatus;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface BureauMemberOut {
  id: string;
  full_name: string;
  role_title: string;
  paroisse: string | null;
  rang: string | null;
  photo_key: string | null;
  has_photo: boolean;
  display_order: number;
  is_active: boolean;
}

export interface SectionBureauMemberOut {
  id: string;
  section_id: string;
  section_name: string | null;
  full_name: string;
  role_title: string;
  display_order: number;
  has_photo: boolean;
  author_id: string;
  author_name: string | null;
  status: DocumentStatus;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export type CourrierKind = 'MESSAGE' | 'DEMANDE_FICHIER';
export type CourrierStatus = 'NOUVEAU' | 'TRAITE';

export interface CourrierOut {
  id: string;
  section_id: string;
  section_name: string | null;
  kind: CourrierKind;
  subject: string;
  body: string;
  has_attachment: boolean;
  attachment_original_filename: string | null;
  status: CourrierStatus;
  response_note: string | null;
  has_response_file: boolean;
  response_original_filename: string | null;
  handled_at: string | null;
  handled_by_id: string | null;
  handled_by_name: string | null;
  author_id: string;
  author_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface MouvementContent {
  id: string;
  intro_title: string;
  intro_paragraph_1: string;
  intro_paragraph_2: string;
  intro_paragraph_3: string;
  theme_annee_label: string;
  theme_annee_quote: string;
  limite_nord: string;
  limite_sud: string;
  limite_ouest: string;
  tutelle: string;
  aumonier_name: string;
  aumonier_role: string;
  vicaire_text: string;
  rang_diocese: string;
  updated_at: string;
}

export interface EffectifCategorieOut {
  id: string;
  categorie: string;
  effectif: number;
  display_order: number;
}

export interface NotificationOut {
  id: string;
  type: string;
  message: string;
  resource_type: string | null;
  resource_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface AuditLogOut {
  id: string;
  user_id: string | null;
  user_label: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  resource_label: string | null;
  result: string;
  ip_address: string | null;
  created_at: string;
}

export interface SectionStat {
  section_id: string;
  section_name: string;
  users_count: number;
  documents_count: number;
  documents_pending_count: number;
}

export interface AdminDashboardStats {
  sections_count: number;
  users_count: number;
  users_active_count: number;
  documents_count: number;
  documents_pending_count: number;
  documents_published_count: number;
  documents_refused_count: number;
  actualites_count: number;
  actualites_pending_count: number;
  programmes_count: number;
  gallery_photos_count: number;
  gallery_photos_pending_count: number;
  recent_documents: DocumentOut[];
  pending_documents: DocumentOut[];
  sections_breakdown: SectionStat[];
}

export interface SectionDashboardStats {
  section_id: string;
  section_name: string;
  documents_count: number;
  documents_pending_count: number;
  documents_published_count: number;
  documents_refused_count: number;
  actualites_count: number;
  programmes_count: number;
  gallery_photos_count: number;
  recent_documents: DocumentOut[];
}
