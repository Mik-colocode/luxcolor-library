# Resolve Prep

Base modulaire pour automatiser la préparation de projets DaVinci Resolve :

1. **Prépa projet** — arborescence Resolve + dossiers prod (templates JSON)
2. **Scan rushes** — analyse métadonnées vidéo (`ffprobe`)
3. **Import** — classement par carte dans les bins
4. **Timelines** — une timeline par carte, settings configurables
5. **Transcos** — file de rendu via preset Deliver

## Prérequis

- **DaVinci Resolve Studio** (scripting externe)
- Python **3.10+**
- Node.js **18+** (UI)
- `ffprobe` dans le PATH (recommandé)

Dans Resolve : **Preferences → General → External scripting using → Local**

## Structure

```text
resolve-prep/
├── backend/          # FastAPI + moteur workflow Python
├── frontend/         # UI React + Vite
├── templates/        # Templates d'arborescence (JSON)
└── scripts/
```

## Format template (V1)

Chaque template JSON décrit :

| Section | Rôle |
|---|---|
| `resolve_bins` | Arborescence Media Pool |
| `filesystem` | Arborescence disque prod |
| `timeline` | FPS, résolution, color timeline |
| `color_management` | CST / color management projet |
| `export` | Preset transco + dossier cible |

Les sous-dossiers du dossier rushes sont traités comme des **cartes** (`card_grouping: folder`).

## Lancer en dev

### Backend

```bash
cd resolve-prep/backend
python -m pip install -e ".[dev]"
RESOLVE_PREP_DRY_RUN=true uvicorn app.main:app --reload --port 8765
```

### Frontend

```bash
cd resolve-prep/frontend
npm install
npm run dev
```

UI : http://localhost:5173

## Workflow API

`POST /workflow/run`

```json
{
  "project_name": "MA_PROD",
  "production_root": "/Volumes/PROD/MA_PROD",
  "rushes_root": "/Volumes/RUSHES/DAY01",
  "template_id": "default-prep",
  "card_grouping": "folder",
  "create_timelines": true,
  "queue_exports": false,
  "dry_run": false
}
```

## Mode dry-run

Sans Resolve ouvert, active `dry_run: true` pour tester :

- création arborescence disque (si chemins valides)
- scan rushes + métadonnées
- simulation bins / timelines / exports

## Roadmap V2

- [ ] Éditeur visuel de templates dans l'UI
- [ ] Profils CST sauvegardés par type de prod
- [ ] Détection carte par métadonnée (reel / card / camera)
- [ ] Packaging desktop (Tauri)
- [ ] Logs détaillés + rapport PDF d'ingest

## Limites API Resolve

- Pas de montage fin (cut/trim) via script
- Presets Deliver : créer d'abord dans Resolve, puis référencer par nom
- Color page node graph non scriptable — on pilote le color management projet + clip input spaces
