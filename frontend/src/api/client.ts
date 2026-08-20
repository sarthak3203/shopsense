/// <reference types="vite/client" />

export type Channel = 'chat' | 'email'
export type TicketStatus = 'completed' | 'paused_for_approval'
export type TicketFinalStatus = 'auto_resolved' | 'human_approved' | 'human_rejected'
export type InterruptPayload = Record<string, unknown>

export interface PolicyAnswer {
  query: string
  answer: string
  sources: string[]
  grounded: boolean
  unsupported_claims: string[]
}

export interface HealthResponse {
  status: string
}

export interface TicketCreateRequest {
  ticket_id: string
  channel: Channel
  customer_id: string
  raw_text: string
}

export interface TicketResumeRequest {
  approved: boolean
  note: string
}

export interface TicketResponse {
  thread_id: string
  status: TicketStatus
  requires_human: boolean
  interrupt_payload: InterruptPayload | null
  final_status: TicketFinalStatus | null
  resolution_notes: string | null
  escalation_reason: string | null
  refund_amount: number | null
  proposed_action: string | null
  issue_type: string | null
  sentiment: string | null
  urgency: string | null
  suspected_prompt_injection: boolean | null
  policy_answer: PolicyAnswer | null
  order_id: string | null
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, `Could not reach the ShopSense API at ${baseUrl}. Check that FastAPI is running.`)
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = isDetailResponse(body) ? body.detail : `Request failed (${response.status})`
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}

function isDetailResponse(value: unknown): value is { detail: string } {
  return typeof value === 'object' && value !== null && 'detail' in value && typeof value.detail === 'string'
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  createTicket: (ticket: TicketCreateRequest) => request<TicketResponse>('/tickets', { method: 'POST', body: JSON.stringify(ticket) }),
  getTicket: (threadId: string) => request<TicketResponse>(`/tickets/${encodeURIComponent(threadId)}`),
  resumeTicket: (threadId: string, payload: TicketResumeRequest) => request<TicketResponse>(`/tickets/${encodeURIComponent(threadId)}/resume`, { method: 'POST', body: JSON.stringify(payload) }),
}
