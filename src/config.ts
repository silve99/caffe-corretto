// I dati del sito (nome, descrizione, contatti, social) stanno in src/data/sito.json,
// così si possono modificare dal pannello Pages CMS senza toccare il codice.
import dati from './data/sito.json';

const NOMI_SOCIAL: Record<string, string> = {
  instagram: 'Instagram',
  facebook: 'Facebook',
  x: 'X (Twitter)',
  telegram: 'Telegram',
  linkedin: 'LinkedIn',
  youtube: 'YouTube',
  tiktok: 'TikTok',
};

export const SITO = {
  nome: dati.nome,
  sottotitolo: dati.sottotitolo,
  descrizione: dati.descrizione,
  lingua: 'it-IT',
  immagineCondivisione: '/immagini/condivisione.png',
  logo: '/immagini/logo.png',
  emailContatti: (dati.emailContatti ?? '').trim(),
};

// Solo i social compilati, nell'ordine sopra.
export const SOCIAL = Object.entries(dati.social ?? {})
  .map(([chiave, url]) => ({ chiave, nome: NOMI_SOCIAL[chiave] ?? chiave, url: String(url ?? '').trim() }))
  .filter((s) => /^https?:\/\//.test(s.url));

// Chi pubblica, per i dati strutturati di Google (schema.org). Serve l'indirizzo del sito.
export const editore = (site: URL | undefined) => ({
  '@type': 'Organization',
  name: SITO.nome,
  url: new URL('/', site).toString(),
  logo: { '@type': 'ImageObject', url: new URL(SITO.logo, site).toString(), width: 512, height: 512 },
  ...(SITO.emailContatti ? { email: SITO.emailContatti } : {}),
  ...(SOCIAL.length ? { sameAs: SOCIAL.map((s) => s.url) } : {}),
});
