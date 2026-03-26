/**
 * TrustConfiguration — Epic 37 Slice 3 (task 37.17)
 *
 * Composed of four sub-components:
 *   - ActiveTierDisplay   : shows + edits the default trust tier
 *   - SafetyBoundsPanel   : hard limits on automated action scope
 *   - RuleBuilder         : form to add / edit a single tier rule
 *   - TrustConfiguration  : top-level settings panel that wires everything
 */

import { useEffect, useState, useCallback } from 'react'
import { Tooltip } from 'react-tooltip'
import { useTrustStore, selectRule } from '../stores/trust-store'
import type { TrustTierRuleRead, AssignedTier } from '../stores/trust-store'
import type { RuleCondition, ConditionOperator, TrustTierRuleCreate } from '../lib/api'
import { EmptyState } from './EmptyState'

// Shield icon for trust-tier empty state
function ShieldIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Helpers / constants
// ---------------------------------------------------------------------------

const TIERS: AssignedTier[] = ['observe', 'suggest', 'execute']
const TIER_DESCRIPTIONS: Record<AssignedTier, string> = {
  observe: 'Read-only: agent observes but takes no automated action',
  suggest: 'Agent suggests changes; a human must approve before merging',
  execute: 'Agent executes changes automatically without requiring approval',
}
/** SG 3.2: OBSERVE gray, SUGGEST blue, EXECUTE purple */
const TIER_COLORS: Record<AssignedTier, string> = {
  observe: 'bg-gray-800/60 text-gray-300 border border-gray-600',
  suggest: 'bg-blue-900/40 text-blue-300 border border-blue-700',
  execute: 'bg-purple-900/40 text-purple-300 border border-purple-700',
}
const OPERATORS: ConditionOperator[] = [
  'equals',
  'not_equals',
  'less_than',
  'greater_than',
  'contains',
  'matches_glob',
]
const OPERATOR_LABELS: Record<ConditionOperator, string> = {
  equals: '=',
  not_equals: '≠',
  less_than: '<',
  greater_than: '>',
  contains: '∋ contains',
  matches_glob: '* glob',
}
const KNOWN_FIELDS = [
  'complexity_index',
  'risk_flags.high_risk',
  'risk_flags.security',
  'risk_flags.migration',
  'scope.file_count',
  'status',
  'repo',
]

function tierBadge(tier: string) {
  const t = tier as AssignedTier
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium capitalize ${TIER_COLORS[t] ?? 'bg-gray-700 text-gray-300'}`}>
      {tier}
    </span>
  )
}

// ---------------------------------------------------------------------------
// ActiveTierDisplay
// ---------------------------------------------------------------------------

function ActiveTierDisplay() {
  const defaultTier = useTrustStore((s) => s.defaultTier)
  const saving = useTrustStore((s) => s.saving)
  const saveDefaultTier = useTrustStore((s) => s.saveDefaultTier)
  const [local, setLocal] = useState<AssignedTier>(defaultTier)

  useEffect(() => {
    setLocal(defaultTier)
  }, [defaultTier])

  const handleChange = useCallback(
    async (tier: AssignedTier) => {
      setLocal(tier)
      await saveDefaultTier(tier)
    },
    [saveDefaultTier],
  )

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-200">Default Trust Tier</h3>
      <p className="mb-3 text-xs text-gray-400">
        Fallback tier assigned when no rule matches a task.
      </p>
      <div className="flex gap-2">
        {TIERS.map((tier) => (
          <button
            key={tier}
            disabled={saving}
            onClick={() => handleChange(tier)}
            className={`rounded-md px-3 py-1.5 text-sm capitalize transition-all ${
              local === tier
                ? TIER_COLORS[tier] + ' font-semibold'
                : 'border border-gray-600 text-gray-400 hover:border-gray-400 hover:text-gray-200'
            } disabled:opacity-50`}
            data-tooltip-id="trust-tip"
            data-tooltip-content={TIER_DESCRIPTIONS[tier]}
          >
            {tier}
          </button>
        ))}
      </div>
      {saving && <p className="mt-2 text-xs text-gray-500">Saving…</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SafetyBoundsPanel
// ---------------------------------------------------------------------------

function SafetyBoundsPanel() {
  const bounds = useTrustStore((s) => s.safetyBounds)
  const saving = useTrustStore((s) => s.saving)
  const saveSafetyBounds = useTrustStore((s) => s.saveSafetyBounds)

  const [maxLines, setMaxLines] = useState('')
  const [maxCost, setMaxCost] = useState('')
  const [maxLoopbacks, setMaxLoopbacks] = useState('')
  const [patterns, setPatterns] = useState('')
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!bounds) return
    setMaxLines(bounds.max_auto_merge_lines != null ? String(bounds.max_auto_merge_lines) : '')
    setMaxCost(bounds.max_auto_merge_cost != null ? String(bounds.max_auto_merge_cost) : '')
    setMaxLoopbacks(bounds.max_loopbacks != null ? String(bounds.max_loopbacks) : '')
    setPatterns((bounds.mandatory_review_patterns ?? []).join('\n'))
    setDirty(false)
  }, [bounds])

  const handleSave = useCallback(async () => {
    await saveSafetyBounds({
      max_auto_merge_lines: maxLines ? parseInt(maxLines, 10) : null,
      max_auto_merge_cost: maxCost ? parseInt(maxCost, 10) : null,
      max_loopbacks: maxLoopbacks ? parseInt(maxLoopbacks, 10) : null,
      mandatory_review_patterns: patterns
        .split('\n')
        .map((p) => p.trim())
        .filter(Boolean),
    })
    setDirty(false)
  }, [saveSafetyBounds, maxLines, maxCost, maxLoopbacks, patterns])

  const mark = useCallback(() => setDirty(true), [])

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-1 text-sm font-semibold text-gray-200">Safety Bounds</h3>
      <p className="mb-4 text-xs text-gray-400">
        Hard limits that constrain automated actions regardless of trust tier.
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <label className="flex flex-col gap-1">
          <span
            className="text-xs text-gray-400"
            data-tooltip-id="trust-tip"
            data-tooltip-content="PRs with more changed lines than this limit require manual approval"
          >
            Max auto-merge lines
          </span>
          <input
            type="number"
            min={1}
            value={maxLines}
            onChange={(e) => { setMaxLines(e.target.value); mark() }}
            placeholder="unlimited"
            className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span
            className="text-xs text-gray-400"
            data-tooltip-id="trust-tip"
            data-tooltip-content="Tasks exceeding this cost (in cents) require manual approval"
          >
            Max auto-merge cost (¢)
          </span>
          <input
            type="number"
            min={0}
            value={maxCost}
            onChange={(e) => { setMaxCost(e.target.value); mark() }}
            placeholder="unlimited"
            className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span
            className="text-xs text-gray-400"
            data-tooltip-id="trust-tip"
            data-tooltip-content="Max QA→implement cycles before a task is escalated for human review"
          >
            Max loopbacks
          </span>
          <input
            type="number"
            min={0}
            value={maxLoopbacks}
            onChange={(e) => { setMaxLoopbacks(e.target.value); mark() }}
            placeholder="unlimited"
            className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </label>
      </div>

      <label className="mt-4 flex flex-col gap-1">
        <span
          className="text-xs text-gray-400"
          data-tooltip-id="trust-tip"
          data-tooltip-content="Files matching these glob patterns always require a human review step, regardless of tier"
        >
          Mandatory review patterns (one glob per line — files matching these always require human
          review)
        </span>
        <textarea
          rows={3}
          value={patterns}
          onChange={(e) => { setPatterns(e.target.value); mark() }}
          placeholder="e.g. src/auth/**&#10;migrations/**"
          className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
        />
      </label>

      {dirty && (
        <div className="mt-4 flex justify-end">
          <button
            disabled={saving}
            onClick={handleSave}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save bounds'}
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ConditionRow — one condition within the rule form
// ---------------------------------------------------------------------------

interface ConditionRowProps {
  condition: RuleCondition
  onChange: (updated: RuleCondition) => void
  onRemove: () => void
}

function ConditionRow({ condition, onChange, onRemove }: ConditionRowProps) {
  return (
    <div className="flex items-center gap-2">
      {/* Field */}
      <input
        list="trust-fields"
        value={condition.field}
        onChange={(e) => onChange({ ...condition, field: e.target.value })}
        placeholder="field"
        className="w-44 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
      />
      <datalist id="trust-fields">
        {KNOWN_FIELDS.map((f) => (
          <option key={f} value={f} />
        ))}
      </datalist>

      {/* Operator */}
      <select
        value={condition.op}
        onChange={(e) => onChange({ ...condition, op: e.target.value as ConditionOperator })}
        className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-100 focus:border-blue-500 focus:outline-none"
      >
        {OPERATORS.map((op) => (
          <option key={op} value={op}>
            {OPERATOR_LABELS[op]}
          </option>
        ))}
      </select>

      {/* Value */}
      <input
        value={String(condition.value)}
        onChange={(e) => onChange({ ...condition, value: e.target.value })}
        placeholder="value"
        className="flex-1 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
      />

      <button
        onClick={onRemove}
        className="rounded p-1 text-gray-500 hover:text-red-400"
        title="Remove condition"
      >
        ✕
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RuleBuilder — add / edit form
// ---------------------------------------------------------------------------

interface RuleBuilderProps {
  existingRule?: TrustTierRuleRead
  onSave: (rule: TrustTierRuleCreate, id?: string) => Promise<void>
  onCancel: () => void
  saving: boolean
}

function RuleBuilder({ existingRule, onSave, onCancel, saving }: RuleBuilderProps) {
  const [conditions, setConditions] = useState<RuleCondition[]>(
    existingRule?.conditions ?? [],
  )
  const [tier, setTier] = useState<AssignedTier>(existingRule?.assigned_tier ?? 'observe')
  const [priority, setPriority] = useState(String(existingRule?.priority ?? 100))
  const [active, setActive] = useState(existingRule?.active ?? true)
  const [description, setDescription] = useState(existingRule?.description ?? '')

  const addCondition = useCallback(() => {
    setConditions((prev) => [...prev, { field: '', op: 'equals', value: '' }])
  }, [])

  const updateCondition = useCallback((idx: number, updated: RuleCondition) => {
    setConditions((prev) => prev.map((c, i) => (i === idx ? updated : c)))
  }, [])

  const removeCondition = useCallback((idx: number) => {
    setConditions((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  const handleSubmit = useCallback(async () => {
    const rule: TrustTierRuleCreate = {
      priority: parseInt(priority, 10) || 100,
      conditions,
      assigned_tier: tier,
      active,
      description: description.trim() || null,
    }
    await onSave(rule, existingRule?.id)
  }, [priority, conditions, tier, active, description, onSave, existingRule])

  return (
    <div className="rounded-lg border border-violet-700/50 bg-gray-900 p-4">
      <h3 className="mb-4 text-sm font-semibold text-gray-200">
        {existingRule ? 'Edit Rule' : 'New Rule'}
      </h3>

      {/* Conditions */}
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400">
            Conditions (ALL must match)
          </span>
          <button
            onClick={addCondition}
            className="rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300 hover:bg-gray-600"
          >
            + Add condition
          </button>
        </div>
        {conditions.length === 0 && (
          <p className="text-xs text-gray-500">
            No conditions — rule matches every task (catch-all).
          </p>
        )}
        <div className="flex flex-col gap-2">
          {conditions.map((c, i) => (
            <ConditionRow
              key={i}
              condition={c}
              onChange={(updated) => updateCondition(i, updated)}
              onRemove={() => removeCondition(i)}
            />
          ))}
        </div>
      </div>

      {/* Tier */}
      <div className="mb-4">
        <span className="mb-2 block text-xs font-medium text-gray-400">Assign tier</span>
        <div className="flex gap-2">
          {TIERS.map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={`rounded-md px-3 py-1 text-sm capitalize ${
                tier === t
                  ? TIER_COLORS[t] + ' font-semibold'
                  : 'border border-gray-600 text-gray-400 hover:border-gray-400 hover:text-gray-200'
              }`}
              data-tooltip-id="trust-tip"
              data-tooltip-content={TIER_DESCRIPTIONS[t]}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Priority + active */}
      <div className="mb-4 flex items-center gap-4">
        <label className="flex flex-col gap-1">
          <span
            className="text-xs text-gray-400"
            data-tooltip-id="trust-tip"
            data-tooltip-content="Lower numbers are evaluated first; the first matching rule wins"
          >
            Priority (lower = evaluated first)
          </span>
          <input
            type="number"
            min={1}
            max={9999}
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-24 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="flex cursor-pointer items-center gap-2 pt-4">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
            className="accent-violet-500"
          />
          <span
            className="text-sm text-gray-300"
            data-tooltip-id="trust-tip"
            data-tooltip-content="Enable or disable this rule without deleting it"
          >
            Active
          </span>
        </label>
      </div>

      {/* Description */}
      <label className="mb-4 flex flex-col gap-1">
        <span className="text-xs text-gray-400">Description (optional)</span>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={500}
          placeholder="E.g. High-complexity tasks → observe"
          className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
        />
      </label>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          disabled={saving}
          className="rounded border border-gray-600 px-3 py-1.5 text-sm text-gray-400 hover:border-gray-400 hover:text-gray-200 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : existingRule ? 'Update rule' : 'Add rule'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RuleRow — one row in the rule list
// ---------------------------------------------------------------------------

function RuleRow({
  rule,
  onEdit,
  onDelete,
  onToggle,
}: {
  rule: TrustTierRuleRead
  onEdit: () => void
  onDelete: () => void
  onToggle: (active: boolean) => void
}) {
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-3 transition-opacity ${
        rule.active ? 'border-gray-700 bg-gray-900' : 'border-gray-800 bg-gray-950 opacity-60'
      }`}
    >
      {/* Active toggle */}
      <input
        type="checkbox"
        checked={rule.active}
        onChange={(e) => onToggle(e.target.checked)}
        className="mt-0.5 accent-violet-500"
        title={rule.active ? 'Disable rule' : 'Enable rule'}
      />

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-gray-500">#{rule.priority}</span>
          {tierBadge(rule.assigned_tier)}
          {rule.description && (
            <span className="text-xs text-gray-400 truncate">{rule.description}</span>
          )}
        </div>
        {rule.conditions.length > 0 ? (
          <div className="mt-1 flex flex-wrap gap-1">
            {rule.conditions.map((c, i) => (
              <span
                key={i}
                className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-300 font-mono"
              >
                {c.field} {OPERATOR_LABELS[c.op]} {String(c.value)}
              </span>
            ))}
          </div>
        ) : (
          <span className="mt-1 text-xs text-gray-600">catch-all</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-1">
        <button
          onClick={onEdit}
          className="rounded p-1 text-gray-500 hover:text-gray-200"
          title="Edit"
        >
          ✎
        </button>
        <button
          onClick={onDelete}
          className="rounded p-1 text-gray-500 hover:text-red-400"
          title="Delete"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TrustConfiguration — top-level settings panel
// ---------------------------------------------------------------------------

export function TrustConfiguration() {
  const { load, addRule, saveRule, removeRule, toggleRuleActive, openEditRule, closeRuleForm } =
    useTrustStore()
  const rules = useTrustStore((s) => s.rules)
  const loading = useTrustStore((s) => s.loading)
  const saving = useTrustStore((s) => s.saving)
  const error = useTrustStore((s) => s.error)
  const ruleFormOpen = useTrustStore((s) => s.ruleFormOpen)
  const editingRuleId = useTrustStore((s) => s.editingRuleId)
  const editingRule = useTrustStore((s) => selectRule(s, editingRuleId))
  const clearError = useTrustStore((s) => s.clearError)

  useEffect(() => {
    load()
  }, [load])

  const handleSaveRule = useCallback(
    async (rule: TrustTierRuleCreate, id?: string) => {
      if (id) {
        await saveRule(id, rule)
      } else {
        await addRule(rule)
      }
    },
    [addRule, saveRule],
  )

  return (
    <div className="mx-auto max-w-4xl px-6 py-6" data-component="TrustConfiguration">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-100">Trust Tier Configuration</h2>
          <p className="text-sm text-gray-400">
            Configure how tasks are assigned trust tiers — observe, suggest, or execute.
          </p>
        </div>
        {loading && <span className="text-xs text-gray-500">Loading…</span>}
      </div>

      {error && (
        <div className="mb-4 flex items-center justify-between rounded border border-red-700 bg-red-900/30 px-4 py-2 text-sm text-red-300">
          <span>{error}</span>
          <button onClick={clearError} className="ml-4 text-red-400 hover:text-red-200">
            ✕
          </button>
        </div>
      )}

      {/* Default tier */}
      <div className="mb-4" data-tour="trust-tier">
        <ActiveTierDisplay />
      </div>

      {/* Safety bounds */}
      <div className="mb-6">
        <SafetyBoundsPanel />
      </div>

      {/* Rule list */}
      <div className="mb-4 flex items-center justify-between" data-tour="trust-rules">
        <h3 className="text-sm font-semibold text-gray-200">
          Rules
          <span
            className="ml-2 text-xs font-normal text-gray-500"
            data-tooltip-id="trust-tip"
            data-tooltip-content="Rules are evaluated in ascending priority order; the first matching rule determines the tier"
          >
            (evaluated in priority order, first match wins)
          </span>
        </h3>
        {!ruleFormOpen && (
          <button
            onClick={() => openEditRule(null)}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            data-tooltip-id="trust-tip"
            data-tooltip-content="Create a conditional rule to assign trust tiers based on task properties"
          >
            + New rule
          </button>
        )}
      </div>

      {/* Rule form */}
      {ruleFormOpen && (
        <div className="mb-4">
          <RuleBuilder
            existingRule={editingRule}
            onSave={handleSaveRule}
            onCancel={closeRuleForm}
            saving={saving}
          />
        </div>
      )}

      {/* Rule rows — empty state */}
      {!loading && rules.length === 0 && !ruleFormOpen && (
        <EmptyState
          icon={<ShieldIcon />}
          heading="No trust rules yet"
          description="Add rules to automatically assign trust tiers (Observe / Suggest / Execute) to tasks based on complexity, risk flags, or repository. Without rules, all tasks use the default tier above."
          primaryAction={{ label: 'Add First Rule', onClick: () => openEditRule(null) }}
          secondaryAction={{ label: 'Learn about trust tiers', href: '/admin/ui/settings' }}
          data-testid="trust-rules-empty"
        />
      )}

      <div className="flex flex-col gap-2">
        {rules.map((rule) => (
          <RuleRow
            key={rule.id}
            rule={rule}
            onEdit={() => openEditRule(rule.id)}
            onDelete={() => removeRule(rule.id)}
            onToggle={(active) => toggleRuleActive(rule.id, active)}
          />
        ))}
      </div>

      {/* Epic 45.8: react-tooltip instance for all trust configuration hints */}
      <Tooltip id="trust-tip" place="top" className="z-50 max-w-xs text-xs" />
    </div>
  )
}

export default TrustConfiguration
