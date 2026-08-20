import type { TicketResponse } from '../api/client'

const STORAGE_KEY = 'shopsense.ticket-history.v1'

export interface TicketHistoryItem {
  threadId: string
  status: TicketResponse['status']
  finalStatus: TicketResponse['final_status']
  issueType: string | null
  createdAt: string
}

export function getHistory(): TicketHistoryItem[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(value) ? value.filter(isHistoryItem) : []
  } catch {
    return []
  }
}

function isHistoryItem(value: unknown): value is TicketHistoryItem {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return typeof record.threadId === 'string' &&
    (record.status === 'completed' || record.status === 'paused_for_approval') &&
    typeof record.createdAt === 'string'
}

export function saveTicket(ticket: TicketResponse): TicketHistoryItem[] {
  const current = getHistory()
  const existing = current.find((item) => item.threadId === ticket.thread_id)
  const item: TicketHistoryItem = {
    threadId: ticket.thread_id,
    status: ticket.status,
    finalStatus: ticket.final_status,
    issueType: ticket.issue_type,
    createdAt: existing?.createdAt ?? new Date().toISOString(),
  }
  const next = [item, ...current.filter((entry) => entry.threadId !== ticket.thread_id)].slice(0, 100)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return next
}

export function clearHistory(): void {
  localStorage.removeItem(STORAGE_KEY)
}
