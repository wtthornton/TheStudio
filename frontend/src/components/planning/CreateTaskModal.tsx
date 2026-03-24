/** CreateTaskModal — modal for manually creating a task from the Backlog Board (Epic 36, 36.19).
 *
 * Epic 41 (Story 41.7): Added repo dropdown to associate tasks with a registered repo.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { createManualTask, fetchAdminRepos } from '../../lib/api'
import type { AdminRepoItem } from '../../lib/api'

interface CreateTaskModalProps {
  open: boolean
  onClose: () => void
  /** Called after successful creation so the board can refresh. */
  onCreated: () => void
}

const CATEGORY_OPTIONS = ['feature', 'bug', 'chore', 'docs', 'refactor', 'test', 'security', 'performance']
const PRIORITY_OPTIONS = ['high', 'medium', 'low']

export default function CreateTaskModal({ open, onClose, onCreated }: CreateTaskModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState('')
  const [criteria, setCriteria] = useState<string[]>([''])
  const [skipTriage, setSkipTriage] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedRepo, setSelectedRepo] = useState<string>('')
  const [availableRepos, setAvailableRepos] = useState<AdminRepoItem[]>([])

  const titleRef = useRef<HTMLInputElement>(null)

  const reset = useCallback(() => {
    setTitle('')
    setDescription('')
    setCategory('')
    setPriority('')
    setCriteria([''])
    setSkipTriage(false)
    setSaving(false)
    setError(null)
    setSelectedRepo('')
  }, [])

  // Load available repos on first open
  useEffect(() => {
    fetchAdminRepos().then((data) => {
      setAvailableRepos(data.repos)
    }).catch(() => {
      // Silently fail — repo selector will just be hidden
    })
  }, [])

  // Reset + focus when modal opens
  useEffect(() => {
    if (open) {
      reset()
      requestAnimationFrame(() => {
        titleRef.current?.focus()
      })
    }
  }, [open, reset])

  // Escape key closes modal
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, saving, onClose])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget && !saving) {
        onClose()
      }
    },
    [saving, onClose],
  )

  // Acceptance criteria list helpers
  const updateCriterion = (index: number, value: string) => {
    setCriteria((prev) => prev.map((c, i) => (i === index ? value : c)))
  }

  const addCriterion = () => {
    setCriteria((prev) => [...prev, ''])
  }

  const removeCriterion = (index: number) => {
    setCriteria((prev) => {
      const next = prev.filter((_, i) => i !== index)
      return next.length === 0 ? [''] : next
    })
  }

  const isValid = title.trim().length > 0 && description.trim().length > 0

  const handleSubmit = useCallback(async () => {
    if (!isValid || saving) return
    setSaving(true)
    setError(null)
    try {
      const filteredCriteria = criteria.map((c) => c.trim()).filter(Boolean)
      await createManualTask({
        title: title.trim(),
        description: description.trim(),
        category: category || null,
        priority: priority || null,
        acceptance_criteria: filteredCriteria.length > 0 ? filteredCriteria : null,
        skip_triage: skipTriage,
        repo: selectedRepo || null,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task')
      setSaving(false)
    }
  }, [title, description, category, priority, criteria, skipTriage, selectedRepo, saving, isValid, onCreated, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
      data-testid="create-task-backdrop"
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-task-modal-title"
        className="w-full max-w-xl rounded-lg border border-gray-700 bg-gray-900 p-6 shadow-xl max-h-[90vh] overflow-y-auto"
      >
        <h3 id="create-task-modal-title" className="mb-1 text-sm font-semibold text-gray-100">
          Create Task
        </h3>
        <p className="mb-5 text-xs text-gray-400">
          Manually create a task. It will enter the Triage queue unless "Skip Triage" is checked.
        </p>

        {/* Title */}
        <div className="mb-4">
          <label className="mb-1 block text-xs font-medium text-gray-300">
            Title <span className="text-red-400">*</span>
          </label>
          <input
            ref={titleRef}
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Add retry logic to the webhook handler"
            disabled={saving}
            maxLength={500}
            className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
            data-testid="create-task-title"
          />
        </div>

        {/* Description (Markdown) */}
        <div className="mb-4">
          <label className="mb-1 block text-xs font-medium text-gray-300">
            Description (Markdown) <span className="text-red-400">*</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the task in detail. Markdown is supported."
            rows={5}
            disabled={saving}
            className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50 font-mono"
            data-testid="create-task-description"
          />
        </div>

        {/* Category + Priority row */}
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-300">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={saving}
              className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none disabled:opacity-50"
              data-testid="create-task-category"
            >
              <option value="">— none —</option>
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-300">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              disabled={saving}
              className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none disabled:opacity-50"
              data-testid="create-task-priority"
            >
              <option value="">— none —</option>
              {PRIORITY_OPTIONS.map((p) => (
                <option key={p} value={p} className={p === 'high' ? 'text-red-400' : p === 'low' ? 'text-gray-400' : ''}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Repo selector (Epic 41, Story 41.7) — only shown when 2+ repos are registered */}
        {availableRepos.length >= 2 && (
          <div className="mb-4">
            <label className="mb-1 block text-xs font-medium text-gray-300">Repository</label>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              disabled={saving}
              className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none disabled:opacity-50"
              data-testid="create-task-repo"
            >
              <option value="">— manual (no repo) —</option>
              {availableRepos.map((r) => {
                const fullName = `${r.owner}/${r.repo}`
                return (
                  <option key={r.id} value={fullName}>
                    {fullName}
                  </option>
                )
              })}
            </select>
          </div>
        )}

        {/* Acceptance Criteria list */}
        <div className="mb-4">
          <label className="mb-1 block text-xs font-medium text-gray-300">Acceptance Criteria</label>
          <div className="flex flex-col gap-2">
            {criteria.map((c, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  type="text"
                  value={c}
                  onChange={(e) => updateCriterion(i, e.target.value)}
                  placeholder={`Criterion ${i + 1}`}
                  disabled={saving}
                  className="flex-1 rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                  data-testid={`create-task-criterion-${i}`}
                />
                <button
                  type="button"
                  onClick={() => removeCriterion(i)}
                  disabled={saving || criteria.length === 1}
                  className="rounded p-1 text-gray-500 hover:text-red-400 disabled:opacity-30"
                  aria-label="Remove criterion"
                  data-testid={`remove-criterion-${i}`}
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addCriterion}
              disabled={saving}
              className="self-start rounded border border-gray-700 px-2 py-1 text-xs text-gray-400 hover:text-gray-200 hover:border-gray-600 disabled:opacity-50 transition-colors"
              data-testid="add-criterion"
            >
              + Add criterion
            </button>
          </div>
        </div>

        {/* Skip Triage checkbox */}
        <div className="mb-5">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={skipTriage}
              onChange={(e) => setSkipTriage(e.target.checked)}
              disabled={saving}
              className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500"
              data-testid="create-task-skip-triage"
            />
            <span className="text-xs text-gray-300">
              Skip Triage — start pipeline immediately
            </span>
          </label>
          {skipTriage && (
            <p className="mt-1 ml-5 text-xs text-amber-400">
              ⚠ The workflow will start as soon as the task is created.
            </p>
          )}
        </div>

        {/* Error */}
        {error && (
          <p
            className="mb-4 rounded border border-red-800 bg-red-950 px-3 py-2 text-xs text-red-300"
            role="alert"
          >
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            data-testid="create-task-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => { void handleSubmit() }}
            disabled={!isValid || saving}
            className="rounded bg-blue-700 px-4 py-1.5 text-xs font-medium text-blue-100 hover:bg-blue-600 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
            data-testid="create-task-submit"
          >
            {saving ? 'Creating…' : skipTriage ? 'Create & Start' : 'Create Task'}
          </button>
        </div>
      </div>
    </div>
  )
}
