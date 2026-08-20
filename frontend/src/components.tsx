import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { TicketHistoryItem } from './lib/history'

export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return <div className="mb-8"><p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-navy/65">{eyebrow}</p><h1 className="font-display text-4xl leading-tight text-navy sm:text-5xl">{title}</h1>{children}</div>
}

export function StatusBadge({ status, finalStatus }: { status: 'completed' | 'paused_for_approval'; finalStatus?: string | null }) {
  const paused = status === 'paused_for_approval'
  const label = paused ? 'Needs human approval' : finalStatus ? finalStatus.replaceAll('_', ' ') : 'Completed'
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold capitalize ${paused ? 'bg-amber/20 text-[#80520e]' : 'bg-success/12 text-success'}`}><span className={`h-1.5 w-1.5 rounded-full ${paused ? 'bg-amber' : 'bg-success'}`} />{label}</span>
}

export function TicketHistoryList({ tickets, limit }: { tickets: TicketHistoryItem[]; limit?: number }) {
  const visible = limit ? tickets.slice(0, limit) : tickets
  if (!visible.length) return <EmptyHistory />
  return <div className="overflow-hidden rounded-xl border border-navy/10 bg-white shadow-panel">
    {visible.map((ticket) => <Link key={ticket.threadId} to={`/tickets/${encodeURIComponent(ticket.threadId)}`} className="group flex items-center justify-between gap-4 border-b border-navy/10 px-5 py-4 last:border-0 transition hover:bg-ice/30">
      <div className="min-w-0"><p className="font-mono text-sm font-semibold text-navy">{ticket.threadId}</p><p className="mt-1 truncate text-sm text-ink/65">{ticket.issueType?.replaceAll('_', ' ') ?? 'Ticket submitted'} <span className="mx-1 text-navy/30">·</span> {formatDate(ticket.createdAt)}</p></div>
      <StatusBadge status={ticket.status} finalStatus={ticket.finalStatus} />
    </Link>)}
  </div>
}

export function EmptyHistory() {
  return <div className="rounded-xl border border-dashed border-navy/25 bg-white px-6 py-12 text-center"><svg aria-hidden="true" viewBox="0 0 24 24" className="mx-auto mb-4 h-8 w-8 fill-none stroke-navy/40" strokeWidth="1.5"><path d="M4 6h16v13H4zM8 3h8v3M8 11h8M8 15h5" strokeLinecap="round" strokeLinejoin="round" /></svg><h2 className="font-display text-xl text-navy">No tickets in this browser yet</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-ink/65">Create a ticket to begin a walkthrough. This list is kept locally in your browser.</p><Link to="/new" className="mt-5 inline-block rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white transition hover:bg-navy/90">Create a ticket</Link></div>
}

export function Skeleton({ className = '' }: { className?: string }) { return <div className={`animate-pulse rounded bg-navy/10 ${className}`} /> }
export function formatMoney(value: number | null | undefined) { return value === null || value === undefined ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value) }
export function formatDate(value: string) { return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
