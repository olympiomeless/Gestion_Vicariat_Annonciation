import { useEffect, useState, type FormEvent } from 'react';
import { mouvementApi } from '../../api/resources';
import type { MouvementContent } from '../../api/types';
import { useToast } from '../../components/ToastContext';
import { LoadingState, ErrorState } from '../../components/UiStates';

type FormState = Omit<MouvementContent, 'id' | 'updated_at'>;

const EMPTY: FormState = {
  intro_title: '',
  intro_paragraph_1: '',
  intro_paragraph_2: '',
  intro_paragraph_3: '',
  theme_annee_label: '',
  theme_annee_quote: '',
  limite_nord: '',
  limite_sud: '',
  limite_ouest: '',
  tutelle: '',
  aumonier_name: '',
  aumonier_role: '',
  vicaire_text: '',
  rang_diocese: '',
};

export default function MouvementPage() {
  const { showError, showToast } = useToast();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await mouvementApi.get();
      const { id, updated_at, ...rest } = data;
      setForm(rest);
      setUpdatedAt(updated_at);
    } catch {
      setError('Impossible de charger le contenu de la section « Le mouvement ».');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const data = await mouvementApi.update(form);
      const { id, updated_at, ...rest } = data;
      setForm(rest);
      setUpdatedAt(updated_at);
      showToast('Contenu mis à jour — visible immédiatement sur le site public.', 'success');
    } catch (err) {
      showError(err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Le mouvement</h1>
          <p>
            Contenu de la section « Le mouvement » du site public (identité du vicariat, thème de l'année,
            limites territoriales, accompagnement spirituel). Toute modification est visible immédiatement
            sur le site vitrine.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <h3 style={{ marginTop: 0 }}>Identité du vicariat</h3>
        <div className="field">
          <label>Titre</label>
          <input value={form.intro_title} onChange={(e) => set('intro_title', e.target.value)} disabled={saving} />
        </div>
        <div className="field">
          <label>Premier paragraphe</label>
          <textarea rows={4} value={form.intro_paragraph_1} onChange={(e) => set('intro_paragraph_1', e.target.value)} disabled={saving} />
        </div>
        <div className="field">
          <label>Deuxième paragraphe</label>
          <textarea rows={4} value={form.intro_paragraph_2} onChange={(e) => set('intro_paragraph_2', e.target.value)} disabled={saving} />
        </div>
        <div className="field">
          <label>Troisième paragraphe</label>
          <textarea rows={3} value={form.intro_paragraph_3} onChange={(e) => set('intro_paragraph_3', e.target.value)} disabled={saving} />
        </div>
        <div className="field" style={{ maxWidth: 220 }}>
          <label>Rang du vicariat au sein du diocèse (ex. « 1/13 »)</label>
          <input value={form.rang_diocese} onChange={(e) => set('rang_diocese', e.target.value)} disabled={saving} />
          <span style={{ fontSize: '.78rem', color: 'var(--ink-faint)' }}>
            Affiché dans le bandeau d'accueil du site public, avec le nombre de sections et le total des militants.
          </span>
        </div>

        <h3>Thème de l'année pastorale</h3>
        <div className="field">
          <label>Intitulé (ex. « Thème de l'année pastorale 2025-2026 — Diocèse de Yopougon »)</label>
          <input value={form.theme_annee_label} onChange={(e) => set('theme_annee_label', e.target.value)} disabled={saving} />
        </div>
        <div className="field">
          <label>Citation du thème</label>
          <textarea rows={3} value={form.theme_annee_quote} onChange={(e) => set('theme_annee_quote', e.target.value)} disabled={saving} />
        </div>

        <h3>Limites du vicariat forain</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div className="field">
            <label>Nord</label>
            <input value={form.limite_nord} onChange={(e) => set('limite_nord', e.target.value)} disabled={saving} />
          </div>
          <div className="field">
            <label>Sud</label>
            <input value={form.limite_sud} onChange={(e) => set('limite_sud', e.target.value)} disabled={saving} />
          </div>
          <div className="field">
            <label>Ouest</label>
            <input value={form.limite_ouest} onChange={(e) => set('limite_ouest', e.target.value)} disabled={saving} />
          </div>
          <div className="field">
            <label>Tutelle</label>
            <input value={form.tutelle} onChange={(e) => set('tutelle', e.target.value)} disabled={saving} />
          </div>
        </div>

        <h3>Accompagnement spirituel</h3>
        <div className="field">
          <label>Nom de l'aumônier</label>
          <input value={form.aumonier_name} onChange={(e) => set('aumonier_name', e.target.value)} disabled={saving} />
        </div>
        <div className="field">
          <label>Fonction de l'aumônier</label>
          <input value={form.aumonier_role} onChange={(e) => set('aumonier_role', e.target.value)} disabled={saving} />
        </div>
        <div className="field">
          <label>Texte sur le vicaire / autre accompagnement</label>
          <textarea rows={3} value={form.vicaire_text} onChange={(e) => set('vicaire_text', e.target.value)} disabled={saving} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
          {updatedAt && (
            <span style={{ fontSize: '.8rem', color: 'var(--ink-faint)' }}>
              Dernière modification : {new Date(updatedAt).toLocaleString('fr-FR')}
            </span>
          )}
          <button type="submit" className="btn btn-primary" disabled={saving} style={{ marginLeft: 'auto' }}>
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </form>
    </div>
  );
}
