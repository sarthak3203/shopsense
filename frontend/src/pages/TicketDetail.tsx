import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ApiError, api, type InterruptPayload, type PolicyAnswer, type TicketResponse } from '../api/client'
import { formatMoney, PageHeader, Skeleton, StatusBadge } from '../components'
import { saveTicket } from '../lib/history'

export default function TicketDetail() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const ticket = useQuery({ queryKey: ['ticket', id], queryFn: () => api.getTicket(id), enabled: Boolean(id), refetchInterval: (query) => query.state.data?.status === 'paused_for_approval' ? 12_000 : false })
  const resume = useMutation({
    mutationFn: ({ approved, note }: { approved: boolean; note: string }) => api.resumeTicket(id, { approved, note }),
    onSuccess: (result) => { saveTicket(result); queryClient.setQueryData(['ticket', id], result) },
  })

  if (ticket.isLoading) return <TicketSkeleton />
  if (ticket.isError) return <TicketError error={ticket.error} />
  if (!ticket.data) return null
  const data = ticket.data

  return <>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <PageHeader eyebrow="Ticket record" title={data.thread_id}><p className="mt-3 text-sm text-ink/65">The latest workflow state from the backend.</p></PageHeader>
      <div className="flex flex-wrap items-center justify-end gap-3">
        {data.suspected_prompt_injection && <span className="inline-flex items-center gap-1.5 rounded-full bg-amber/20 px-2.5 py-1 text-xs font-bold text-[#80520e]"><span className="h-1.5 w-1.5 rounded-full bg-amber" />Prompt-injection flag</span>}
        <StatusBadge status={data.status} finalStatus={data.final_status} />
        <button onClick={() => ticket.refetch()} disabled={ticket.isFetching} className="rounded-md border border-navy/25 bg-white px-3.5 py-2 text-sm font-semibold text-navy transition hover:bg-ice disabled:opacity-60">{ticket.isFetching ? 'Refreshing…' : 'Refresh'}</button>
      </div>
    </div>
    {data.status === 'paused_for_approval'
      ? <ApprovalPanel payload={data.interrupt_payload} ticket={data} pending={resume.isPending} error={resume.error} onDecide={(approved, note) => resume.mutate({ approved, note })} />
      : <CompletedPanel ticket={data} />}
  </>
}

function ApprovalPanel({ payload, ticket, pending, error, onDecide }: { payload: InterruptPayload | null; ticket: TicketResponse; pending: boolean; error: Error | null; onDecide: (approved: boolean, note: string) => void }) {
  const [showReject, setShowReject] = useState(false)
  const [note, setNote] = useState('')
  const values = { issue_type: ticket.issue_type, sentiment: ticket.sentiment, urgency: ticket.urgency, proposed_action: ticket.proposed_action, refund_amount: ticket.refund_amount, escalation_reason: ticket.escalation_reason, ...payload }
  const submitReject = () => { if (note.trim()) onDecide(false, note.trim()) }

  return <div className="rounded-2xl border border-amber/60 bg-[#fffaf0] p-5 shadow-panel sm:p-7">
    <div className="flex items-start gap-4"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-amber/25 text-xl font-bold text-[#80520e]">!</span><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[#80520e]">Decision required</p><h2 className="mt-1 font-display text-3xl text-navy">This ticket is paused for human approval.</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-ink/70">Review the workflow’s proposed action and escalation context. The action will not continue until you make a decision.</p></div></div>
    <dl className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><DecisionValue label="Issue type" value={asText(values.issue_type)} /><DecisionValue label="Sentiment" value={asText(values.sentiment)} /><DecisionValue label="Urgency" value={asText(values.urgency)} /><DecisionValue label="Proposed action" value={asText(values.proposed_action)} /><DecisionValue label="Refund amount" value={asMoney(values.refund_amount)} /><DecisionValue label="Escalation reason" value={asText(values.escalation_reason)} wide /></dl>
    {ticket.policy_answer && <div className="mt-6"><PolicyAnswerCard policyAnswer={ticket.policy_answer} /></div>}
    {payload && <PayloadDetails payload={payload} />}
    {error && <ApiAlert error={error} />}
    <div className="mt-7 border-t border-amber/35 pt-5">{showReject ? <div className="max-w-xl"><label className="text-sm font-semibold text-navy">Rejection note <span className="font-normal text-ink/55">(required)</span><textarea autoFocus value={note} onChange={(event) => setNote(event.target.value)} className="field mt-2 min-h-24" placeholder="Explain why the request should not proceed…" /></label><div className="mt-3 flex gap-3"><button disabled={!note.trim() || pending} onClick={submitReject} className="rounded-md bg-navy px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">{pending ? 'Recording decision…' : 'Confirm rejection'}</button><button disabled={pending} onClick={() => setShowReject(false)} className="rounded-md border border-navy/25 bg-white px-4 py-2.5 text-sm font-semibold text-navy">Cancel</button></div></div> : <div className="flex flex-wrap gap-3"><button disabled={pending} onClick={() => onDecide(true, '')} className="rounded-md bg-success px-5 py-3 text-sm font-bold text-white transition hover:bg-success/90 disabled:opacity-60">{pending ? 'Recording decision…' : 'Approve action'}</button><button disabled={pending} onClick={() => setShowReject(true)} className="rounded-md border border-[#a86d13] bg-white px-5 py-3 text-sm font-bold text-[#80520e] transition hover:bg-amber/10 disabled:opacity-60">Reject action</button></div>}</div>
  </div>
}

function CompletedPanel({ ticket }: { ticket: TicketResponse }) {
  return <div className="space-y-6">
    <section className="rounded-xl border border-success/25 bg-white p-6 shadow-panel"><p className="text-xs font-bold uppercase tracking-[0.16em] text-success">Workflow complete</p><div className="mt-2 flex flex-wrap items-center gap-3"><h2 className="font-display text-3xl text-navy">{ticket.final_status?.replaceAll('_', ' ') ?? 'Completed'}</h2><StatusBadge status={ticket.status} finalStatus={ticket.final_status} /></div><p className="mt-4 max-w-3xl rounded-lg bg-[#f2faf6] p-4 text-sm leading-6 text-ink/75">{ticket.resolution_notes ?? 'The workflow completed without additional resolution notes.'}</p></section>
    {ticket.policy_answer && <PolicyAnswerCard policyAnswer={ticket.policy_answer} />}
    <section className="rounded-xl border border-navy/10 bg-white p-6 shadow-panel"><h2 className="font-display text-2xl text-navy">Workflow record</h2><dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><DetailValue label="Issue type" value={ticket.issue_type} /><DetailValue label="Sentiment" value={ticket.sentiment} /><DetailValue label="Urgency" value={ticket.urgency} /><DetailValue label="Order ID" value={ticket.order_id} /><DetailValue label="Proposed action" value={ticket.proposed_action} /><DetailValue label="Refund amount" value={formatMoney(ticket.refund_amount)} /><DetailValue label="Escalation reason" value={ticket.escalation_reason} /></dl></section>
  </div>
}

function PolicyAnswerCard({ policyAnswer }: { policyAnswer: PolicyAnswer }) {
  return <section className="rounded-xl border border-navy/10 bg-white p-6 shadow-panel"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-navy/60">Grounded policy response</p><h2 className="mt-1 font-display text-2xl text-navy">Policy answer</h2></div><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${policyAnswer.grounded ? 'bg-success/12 text-success' : 'bg-amber/20 text-[#80520e]'}`}><span className={`h-1.5 w-1.5 rounded-full ${policyAnswer.grounded ? 'bg-success' : 'bg-amber'}`} />{policyAnswer.grounded ? 'Grounded in policy' : 'Not fully grounded'}</span></div><p className="mt-5 max-w-4xl whitespace-pre-wrap text-base leading-7 text-ink/85">{policyAnswer.answer}</p>{policyAnswer.sources.length > 0 && <div className="mt-5 flex flex-wrap gap-2">{policyAnswer.sources.map((source) => <span key={source} className="rounded-full bg-ice/55 px-2.5 py-1 font-mono text-xs font-semibold text-navy">{source}</span>)}</div>}{policyAnswer.unsupported_claims.length > 0 && <div role="alert" className="mt-5 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm leading-6 text-[#704709]"><strong className="block">Unsupported claims flagged</strong><ul className="mt-1 list-disc pl-5">{policyAnswer.unsupported_claims.map((claim) => <li key={claim}>{claim}</li>)}</ul></div>}</section>
}

function TicketError({ error }: { error: Error }) { const missing = error instanceof ApiError && error.status === 404; return <div className="mx-auto max-w-xl rounded-xl border border-navy/15 bg-white p-8 text-center shadow-panel"><h1 className="font-display text-3xl text-navy">{missing ? 'No such ticket' : 'Ticket could not be loaded'}</h1><p className="mt-3 text-sm leading-6 text-ink/65">{missing ? 'This thread ID is not known by the backend. It may be mistyped or from a different API instance.' : error.message}</p><Link to="/new" className="mt-6 inline-block rounded-md bg-navy px-4 py-2.5 text-sm font-bold text-white">Create a ticket</Link></div> }
function TicketSkeleton() { return <><Skeleton className="h-3 w-24" /><Skeleton className="mt-4 h-12 w-64" /><div className="mt-8 rounded-xl border border-navy/10 bg-white p-6"><Skeleton className="h-5 w-40" /><div className="mt-6 grid gap-3 sm:grid-cols-2"><Skeleton className="h-24" /><Skeleton className="h-24" /><Skeleton className="h-24" /><Skeleton className="h-24" /></div></div></> }
function DecisionValue({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) { return <div className={`rounded-lg border border-amber/30 bg-white/80 p-4 ${wide ? 'lg:col-span-2' : ''}`}><dt className="text-xs font-bold uppercase tracking-[0.12em] text-navy/55">{label}</dt><dd className="mt-1 break-words text-sm font-semibold text-navy">{value}</dd></div> }
function DetailValue({ label, value }: { label: string; value: string | null }) { return <div className="rounded-lg bg-[#f6f9ff] p-4"><dt className="text-xs font-bold uppercase tracking-[0.12em] text-navy/55">{label}</dt><dd className="mt-1 break-words text-sm font-semibold capitalize text-navy">{value?.replaceAll('_', ' ') ?? '—'}</dd></div> }
function PayloadDetails({ payload }: { payload: InterruptPayload }) { const extras = Object.entries(payload).filter(([key]) => !['issue_type', 'sentiment', 'urgency', 'suspected_prompt_injection', 'proposed_action', 'refund_amount', 'escalation_reason', 'policy_answer'].includes(key)); if (!extras.length) return null; return <details className="mt-5 text-sm"><summary className="cursor-pointer font-semibold text-navy">Additional interrupt data</summary><div className="mt-3 rounded-lg bg-white p-4"><dl className="space-y-2">{extras.map(([key, value]) => <div key={key} className="flex gap-3"><dt className="min-w-32 font-medium text-ink/60">{key.replaceAll('_', ' ')}</dt><dd className="break-all text-navy">{stringify(value)}</dd></div>)}</dl></div></details> }
function ApiAlert({ error }: { error: Error }) { const conflict = error instanceof ApiError && error.status === 409; return <div role="alert" className="mt-5 rounded-lg border border-amber/50 bg-white p-4 text-sm leading-6 text-[#704709]"><strong className="block">{conflict ? 'This ticket is no longer paused' : 'Decision could not be recorded'}</strong>{conflict ? 'Another reviewer may have already resolved it. Refresh this ticket to see the current state.' : error.message}</div> }
function asText(value: unknown) { return typeof value === 'string' && value ? value.replaceAll('_', ' ') : '—' }
function asMoney(value: unknown) { return typeof value === 'number' ? formatMoney(value) : '—' }
function stringify(value: unknown) { return typeof value === 'string' ? value : JSON.stringify(value) }
