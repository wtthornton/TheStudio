/**
 * ProjectsSyncConfig — GitHub Projects v2 sync configuration UI.
 *
 * Epic 38.18: Connect a project, map fields, toggle sync behaviors, test sync,
 * and force a full re-sync. Consumes GET/PUT /api/v1/dashboard/github/projects/config
 * and POST /api/v1/dashboard/github/projects/sync.
 */

import { useCallback, useEffect, useState } from 'react';

interface ProjectsSyncConfigData {
  enabled: boolean;
  owner: string;
  project_number: number;
  auto_add: boolean;
  auto_close: boolean;
  respect_manual_overrides: boolean;
}

interface ProjectsSyncStatus {
  token_configured: boolean;
  last_sync_error: string | null;
}

interface ConfigResponse {
  config: ProjectsSyncConfigData;
  status: ProjectsSyncStatus;
}

interface ForceSyncResponse {
  triggered: boolean;
  active_tasks_found: number;
  errors: string[];
  message: string;
}

const API_BASE = '/api/v1/dashboard';

async function fetchConfig(): Promise<ConfigResponse> {
  const res = await fetch(`${API_BASE}/github/projects/config`);
  if (!res.ok) throw new Error(`Failed to fetch config: ${res.statusText}`);
  return res.json();
}

async function saveConfig(config: ProjectsSyncConfigData): Promise<ConfigResponse> {
  const res = await fetch(`${API_BASE}/github/projects/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`Failed to save config: ${res.statusText}`);
  return res.json();
}

async function forceSync(): Promise<ForceSyncResponse> {
  const res = await fetch(`${API_BASE}/github/projects/sync`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Sync failed (${res.status}): ${text}`);
  }
  return res.json();
}

interface ToggleRowProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function ToggleRow({ label, description, checked, onChange, disabled }: ToggleRowProps) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1 pr-4">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          'relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent',
          'transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2',
          'focus:ring-blue-500 focus:ring-offset-2 cursor-pointer',
          checked ? 'bg-blue-600' : 'bg-gray-200',
          disabled ? 'opacity-50 cursor-not-allowed' : '',
        ].join(' ')}
      >
        <span
          className={[
            'pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow',
            'transform ring-0 transition duration-200 ease-in-out',
            checked ? 'translate-x-4' : 'translate-x-0',
          ].join(' ')}
        />
      </button>
    </div>
  );
}

export function ProjectsSyncConfig() {
  const [config, setConfig] = useState<ProjectsSyncConfigData | null>(null);
  const [status, setStatus] = useState<ProjectsSyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<ForceSyncResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchConfig();
      setConfig(data.config);
      setStatus(data.status);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load config');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const result = await saveConfig(config);
      setConfig(result.config);
      setStatus(result.status);
      setSuccessMsg('Configuration saved successfully.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  const handleForceSync = async () => {
    setSyncing(true);
    setError(null);
    setSyncResult(null);
    try {
      const result = await forceSync();
      setSyncResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Force sync failed');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full" />
        <span className="ml-3 text-sm text-gray-500">Loading configuration…</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        {error ?? 'Failed to load Projects v2 configuration.'}
      </div>
    );
  }

  const isConfigured = status?.token_configured && !!config.owner && config.project_number > 0;

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900">GitHub Projects v2 Sync</h2>
        <p className="text-sm text-gray-500 mt-1">
          Keep your GitHub Projects board in sync with the pipeline. Stage transitions push
          Status, Trust Tier, and Complexity fields automatically.
        </p>
      </div>

      {/* Status banner */}
      <div
        className={[
          'flex items-center gap-3 px-4 py-3 rounded-lg text-sm',
          isConfigured
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-amber-50 border border-amber-200 text-amber-800',
        ].join(' ')}
      >
        <span className={`h-2 w-2 rounded-full shrink-0 ${isConfigured ? 'bg-green-500' : 'bg-amber-500'}`} />
        {isConfigured
          ? `Connected to project #${config.project_number} (${config.owner})`
          : 'Not configured — set THESTUDIO_PROJECTS_V2_* environment variables to enable sync.'}
        {status && !status.token_configured && (
          <span className="ml-auto text-xs font-medium uppercase tracking-wide">Token missing</span>
        )}
      </div>

      {/* Project details (read-only from env) */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Project Connection</h3>
        <div className="grid grid-cols-2 gap-4 mt-2">
          <div>
            <p className="text-xs text-gray-500">Owner</p>
            <p className="text-sm font-medium text-gray-900">{config.owner || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Project Number</p>
            <p className="text-sm font-medium text-gray-900">
              {config.project_number > 0 ? `#${config.project_number}` : '—'}
            </p>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Set via <code className="font-mono bg-white px-1 py-0.5 rounded border">THESTUDIO_PROJECTS_V2_OWNER</code>
          {' '}and{' '}
          <code className="font-mono bg-white px-1 py-0.5 rounded border">THESTUDIO_PROJECTS_V2_NUMBER</code>.
        </p>
      </div>

      {/* Sync behavior toggles */}
      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100 px-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide py-3">Sync Behaviors</h3>

        <ToggleRow
          label="Enable Projects v2 Sync"
          description="Push pipeline state to the GitHub Projects board on every stage transition."
          checked={config.enabled}
          onChange={(v) => setConfig((c) => c && { ...c, enabled: v })}
        />

        <ToggleRow
          label="Auto-add new TaskPackets"
          description="Automatically add new issues to the project when they enter the pipeline."
          checked={config.auto_add}
          onChange={(v) => setConfig((c) => c && { ...c, auto_add: v })}
          disabled={!config.enabled}
        />

        <ToggleRow
          label="Auto-close issues on completion"
          description="Close the GitHub issue when the pipeline publishes a PR or marks the task as Done."
          checked={config.auto_close}
          onChange={(v) => setConfig((c) => c && { ...c, auto_close: v })}
          disabled={!config.enabled}
        />

        <ToggleRow
          label="Respect manual overrides"
          description="Skip automatic field updates when a user has manually changed a field on the board."
          checked={config.respect_manual_overrides}
          onChange={(v) => setConfig((c) => c && { ...c, respect_manual_overrides: v })}
          disabled={!config.enabled}
        />
      </div>

      {/* Error / success feedback */}
      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          {successMsg}
        </div>
      )}

      {/* Force sync result */}
      {syncResult && (
        <div className="px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
          <p className="font-medium text-blue-900">{syncResult.message}</p>
          {syncResult.errors.length > 0 && (
            <ul className="mt-2 space-y-1 text-blue-700">
              {syncResult.errors.map((e, i) => (
                <li key={i} className="text-xs">• {e}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || loading}
          className={[
            'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
            'bg-blue-600 text-white hover:bg-blue-700 focus:outline-none',
            'focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            saving || loading ? 'opacity-50 cursor-not-allowed' : '',
          ].join(' ')}
        >
          {saving ? 'Saving…' : 'Save Configuration'}
        </button>

        <button
          type="button"
          onClick={handleForceSync}
          disabled={syncing || !isConfigured || !config.enabled}
          className={[
            'px-4 py-2 text-sm font-medium rounded-lg border transition-colors',
            'border-gray-300 bg-white text-gray-700 hover:bg-gray-50',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            syncing || !isConfigured || !config.enabled ? 'opacity-50 cursor-not-allowed' : '',
          ].join(' ')}
        >
          {syncing ? 'Syncing…' : 'Force Full Sync'}
        </button>
      </div>
    </div>
  );
}

export default ProjectsSyncConfig;
