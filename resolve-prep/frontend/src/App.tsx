import { FormEvent, useEffect, useState } from "react";
import {
  fetchHealth,
  fetchTemplates,
  PrepTemplate,
  runWorkflow,
  WorkflowRequest,
  WorkflowResult,
} from "./api/client";

const initialForm: WorkflowRequest = {
  project_name: "PROJET_TEST",
  production_root: "/Volumes/PROD",
  rushes_root: "/Volumes/RUSHES",
  template_id: "default-prep",
  card_grouping: "folder",
  create_timelines: true,
  queue_exports: false,
  dry_run: true,
};

export default function App() {
  const [templates, setTemplates] = useState<PrepTemplate[]>([]);
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiDryRunDefault, setApiDryRunDefault] = useState(false);

  useEffect(() => {
    void Promise.all([fetchTemplates(), fetchHealth()])
      .then(([templateList, health]) => {
        setTemplates(templateList);
        setApiDryRunDefault(health.dry_run_default);
        if (templateList.length > 0) {
          setForm((current) => ({ ...current, template_id: templateList[0].id }));
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const workflowResult = await runWorkflow(form);
      setResult(workflowResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const selectedTemplate = templates.find((template) => template.id === form.template_id);

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">Resolve Prep · V1</p>
          <h1>Prépa projet, ingest rushes, timelines & transcos</h1>
          <p className="subtitle">
            Base modulaire pour une app externe connectée à DaVinci Resolve Studio.
          </p>
        </div>
        <div className="badge">API dry-run default: {apiDryRunDefault ? "on" : "off"}</div>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>Workflow</h2>
          <form className="form" onSubmit={onSubmit}>
            <label>
              Nom du projet
              <input
                value={form.project_name}
                onChange={(e) => setForm({ ...form, project_name: e.target.value })}
                required
              />
            </label>

            <label>
              Dossier production
              <input
                value={form.production_root}
                onChange={(e) => setForm({ ...form, production_root: e.target.value })}
                required
              />
            </label>

            <label>
              Dossier rushes
              <input
                value={form.rushes_root}
                onChange={(e) => setForm({ ...form, rushes_root: e.target.value })}
                required
              />
            </label>

            <label>
              Template
              <select
                value={form.template_id}
                onChange={(e) => setForm({ ...form, template_id: e.target.value })}
              >
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Groupement par carte
              <select
                value={form.card_grouping}
                onChange={(e) =>
                  setForm({
                    ...form,
                    card_grouping: e.target.value as "folder" | "flat",
                  })
                }
              >
                <option value="folder">Sous-dossier = carte</option>
                <option value="flat">Tout dans une carte</option>
              </select>
            </label>

            <div className="checks">
              <label>
                <input
                  type="checkbox"
                  checked={form.create_timelines}
                  onChange={(e) => setForm({ ...form, create_timelines: e.target.checked })}
                />
                Créer une timeline par carte
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={form.queue_exports}
                  onChange={(e) => setForm({ ...form, queue_exports: e.target.checked })}
                />
                Lancer les transcos
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={form.dry_run}
                  onChange={(e) => setForm({ ...form, dry_run: e.target.checked })}
                />
                Dry-run (sans Resolve)
              </label>
            </div>

            <button type="submit" disabled={loading}>
              {loading ? "Exécution..." : "Lancer le workflow"}
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Template sélectionné</h2>
          {selectedTemplate ? (
            <div className="template-preview">
              <p>{selectedTemplate.description}</p>
              <div className="columns">
                <div>
                  <h3>Bins Resolve</h3>
                  <TreePreview nodes={selectedTemplate.resolve_bins} />
                </div>
                <div>
                  <h3>Dossiers prod</h3>
                  <TreePreview nodes={selectedTemplate.filesystem} />
                </div>
              </div>
              <div className="meta-grid">
                <div>
                  <strong>Timeline</strong>
                  <p>
                    {selectedTemplate.timeline.frame_rate} fps · {selectedTemplate.timeline.resolution}
                  </p>
                </div>
                <div>
                  <strong>Export</strong>
                  <p>{String(selectedTemplate.export.render_preset_name ?? "custom")}</p>
                </div>
              </div>
            </div>
          ) : (
            <p>Aucun template chargé.</p>
          )}
        </section>
      </main>

      {error && <section className="panel error">{error}</section>}

      {result && (
        <section className="panel">
          <h2>Résultat</h2>
          <p>
            Projet <strong>{result.project_name}</strong> · dry-run {result.dry_run ? "oui" : "non"}
          </p>
          {result.scan && (
            <p>
              Scan: {result.scan.total_files} fichiers · {Object.keys(result.scan.cards).length} cartes
            </p>
          )}
          <ol className="steps">
            {result.steps.map((step) => (
              <li key={step.step} className={step.success ? "ok" : "ko"}>
                <strong>{step.step}</strong> — {step.message}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

function TreePreview({ nodes }: { nodes: PrepTemplate["resolve_bins"] }) {
  return (
    <ul className="tree">
      {nodes.map((node) => (
        <li key={node.name}>
          {node.name}
          {node.children.length > 0 && <TreePreview nodes={node.children} />}
        </li>
      ))}
    </ul>
  );
}
