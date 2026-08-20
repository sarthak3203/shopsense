import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { PageHeader, Skeleton, TicketHistoryList } from '../components'
import { getHistory } from '../lib/history'

const stages = ['Triage', 'Policy & action', 'Escalation review', 'Human approval']

export default function Overview() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30_000 })
  const tickets = getHistory()
  return <>
    <div className="grid gap-8 lg:grid-cols-[1.35fr_0.65fr] lg:items-end">
      <PageHeader eyebrow="ShopSense support operations" title="Every refund decision, made accountable."><p className="mt-4 max-w-2xl text-base leading-7 text-ink/70">ShopSense routes incoming support tickets through triage, grounded policy review, order action, and escalation controls. Tickets that need judgment pause for a human decision before any sensitive action is taken.</p></PageHeader>
      <HealthCard isLoading={health.isLoading} healthy={health.data?.status === 'ok'} error={health.isError} />
    </div>
    <section className="mb-10 rounded-2xl bg-navy px-6 py-7 text-white shadow-panel sm:px-8"><div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-ice">Ticket workflow</p><div className="mt-4 flex flex-wrap items-center gap-y-3">{stages.map((stage, index) => <div key={stage} className="flex items-center"><span className="rounded-full border border-ice/35 px-3 py-1.5 text-sm font-medium">{stage}</span>{index < stages.length - 1 && <span className="mx-2 h-px w-6 bg-ice/40" />}</div>)}</div></div><Link to="/new" className="inline-flex shrink-0 items-center justify-center rounded-md bg-white px-5 py-3 text-sm font-bold text-navy transition hover:bg-ice">Create a ticket <span className="ml-2 text-lg leading-none">→</span></Link></div></section>
    <section><div className="mb-4 flex items-end justify-between"><div><h2 className="font-display text-2xl text-navy">Recent ticket history</h2><p className="mt-1 text-sm text-ink/65">Stored only in this browser — the API has no ticket list endpoint.</p></div>{tickets.length > 5 && <Link to="/tickets" className="text-sm font-semibold text-navy underline-offset-4 hover:underline">View all history</Link>}</div><TicketHistoryList tickets={tickets} limit={5} /></section>
  </>
}

function HealthCard({ isLoading, healthy, error }: { isLoading: boolean; healthy: boolean; error: boolean }) {
  return <div className="rounded-xl border border-navy/10 bg-white p-5 shadow-panel"><p className="text-xs font-bold uppercase tracking-[0.16em] text-navy/60">API status</p>{isLoading ? <div className="mt-4"><Skeleton className="h-5 w-32" /><Skeleton className="mt-3 h-4 w-52" /></div> : <><div className="mt-3 flex items-center gap-2 font-semibold text-navy"><span className={`h-2.5 w-2.5 rounded-full ${healthy ? 'bg-success' : 'bg-amber'}`} />{healthy ? 'Service healthy' : 'Service unavailable'}</div><p className="mt-2 text-sm leading-5 text-ink/60">{healthy ? 'GET /health is responding normally.' : error ? 'Could not reach the configured FastAPI service.' : 'The service returned an unexpected health response.'}</p></>}</div>
}
