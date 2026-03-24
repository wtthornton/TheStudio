/**
 * CommentThread — Epic 56.4
 *
 * Inline comment thread bound to an artifact ID (e.g., task ID).
 * Comments are persisted in localStorage under `thestudio_comments_{artifactId}`.
 */

import { useState, useEffect, useCallback } from 'react'

export interface Comment {
  id: string
  author: string
  text: string
  timestamp: string // ISO 8601
}

export interface CommentThreadProps {
  artifactId: string
  /** Current user name — used as author for new comments. */
  currentUser?: string
}

function storageKey(artifactId: string): string {
  return `thestudio_comments_${artifactId}`
}

function loadComments(artifactId: string): Comment[] {
  try {
    const raw = localStorage.getItem(storageKey(artifactId))
    if (raw) {
      const parsed = JSON.parse(raw) as Comment[]
      if (Array.isArray(parsed)) return parsed
    }
  } catch {
    /* ignore */
  }
  return []
}

function persistComments(artifactId: string, comments: Comment[]): void {
  localStorage.setItem(storageKey(artifactId), JSON.stringify(comments))
}

export function CommentThread({ artifactId, currentUser = 'You' }: CommentThreadProps) {
  const [comments, setComments] = useState<Comment[]>([])
  const [newText, setNewText] = useState('')

  // Load comments on mount or when artifactId changes
  useEffect(() => {
    setComments(loadComments(artifactId))
  }, [artifactId])

  const handleSubmit = useCallback(() => {
    const trimmed = newText.trim()
    if (!trimmed) return

    const comment: Comment = {
      id: `cmt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      author: currentUser,
      text: trimmed,
      timestamp: new Date().toISOString(),
    }

    const updated = [...comments, comment]
    setComments(updated)
    persistComments(artifactId, updated)
    setNewText('')
  }, [newText, comments, artifactId, currentUser])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit],
  )

  return (
    <section
      className="rounded-lg border border-gray-800 bg-gray-900 p-4"
      data-testid="comment-thread"
      aria-label={`Comments for ${artifactId}`}
    >
      <h3 className="mb-3 text-sm font-semibold text-gray-100">Comments</h3>

      {comments.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-500" data-testid="comment-empty">
          No comments yet
        </p>
      ) : (
        <ul className="mb-4 space-y-3" data-testid="comment-list">
          {comments.map((c) => (
            <li
              key={c.id}
              className="rounded border border-gray-800 bg-gray-950 px-3 py-2"
              data-testid={`comment-${c.id}`}
            >
              <div className="mb-1 flex items-center gap-2 text-xs text-gray-500">
                <span className="font-medium text-gray-300" data-testid="comment-author">
                  {c.author}
                </span>
                <time dateTime={c.timestamp} data-testid="comment-time">
                  {new Date(c.timestamp).toLocaleString()}
                </time>
              </div>
              <p className="text-sm text-gray-200" data-testid="comment-text">
                {c.text}
              </p>
            </li>
          ))}
        </ul>
      )}

      {/* Add comment input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a comment..."
          className="flex-1 rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid="comment-input"
          aria-label="Add a comment"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!newText.trim()}
          className="rounded bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          data-testid="comment-submit"
        >
          Submit
        </button>
      </div>
    </section>
  )
}
