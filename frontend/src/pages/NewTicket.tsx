import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, type Channel, type TicketCreateRequest } from '../api/client'
import { PageHeader } from '../components'
import { saveTicket } from '../lib/history'

interface Example {
  title: string
  detail: string
  channel: Channel
  customerId: string
  rawText: string
}

const examples: Example[] = [
  { title: 'Clean low-value refund', detail: 'ORD-9002 · expected auto-resolution', channel: 'chat', customerId: 'CUST-DEMO-LOW', rawText: "Hi, I'd like a refund for my wireless mouse, order ORD-9002. It's within the return window and I just don't need it anymore." },
  { title: 'Over-threshold refund', detail: 'ORD-8842 · requires approval', channel: 'email', customerId: 'CUST-DEMO-HIGH', rawText: "Please process a refund for order ORD-8842. It arrived damaged and I'd like my money back." },
  { title: 'Angry sentiment', detail: 'ORD-5521 · requires approval', channel: 'chat', customerId: 'CUST-DEMO-ANGRY', rawText: 'This is absolutely ridiculous. My package for order ORD-5521 was supposed to arrive 5 days ago and nobody will tell me where it is. I am furious and want this fixed NOW.' },
  { title: 'Policy question', detail: 'Grounded policy response', channel: 'chat', customerId: 'CUST-DEMO-POLICY', rawText: 'What is your return window for a standard order, and do I need the original packaging?' },
]

function makeTicketId() { return `TCK-${Date.now()}` }

export default function NewTicket() {
  const navigate = useNavigate()
  const [ticketId, setTicketId] = useState(makeTicketId)
  const [channel, setChannel] = useState<Channel>('chat')
  const [customerId, setCustomerId] = useState('CUST-DEMO-001')
  const [rawText, setRawText] = useState('')
  const mutation = useMutation({
    mutationFn: api.createTicket,
    onSuccess: (ticket) => { saveTicket(ticket); navigate(`/tickets/${encodeURIComponent(ticket.thread_id)}`) },
  })
  const useExample = (example: Example) => { setTicketId(makeTicketId()); setChannel(example.channel); setCustomerId(example.customerId); setRawText(example.rawText) }
  const submit = (event: React.FormEvent<HTMLFormElement>) => { event.preventDefault(); mutation.mutate({ ticket_id: ticketId, channel, customer_id: customerId, raw_text: rawText } satisfies TicketCreateRequest) }
  return <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_330px]">
    <section><PageHeader eyebrow="New support request" title="Create a ticket"><p className="mt-3 max-w-2xl text-sm leading-6 text-ink/65">Submit a real request to the configured FastAPI service. The resulting ticket will be kept in this browser’s history.</p></PageHeader>
      <form onSubmit={submit} className="rounded-xl border border-navy/10 bg-white p-5 shadow-panel sm:p-7">
        <div className="grid gap-5 sm:grid-cols-2"><label className="block text-sm font-semibold text-navy">Ticket ID<div className="mt-2 flex gap-2"><input value={ticketId} readOnly className="field min-w-0 bg-slate-50 font-mono text-sm text-ink/70" /><button type="button" onClick={() => setTicketId(makeTicketId())} className="rounded-md border border-navy/25 px-3 text-sm font-semibold text-navy hover:bg-ice">Regenerate</button></div></label><label className="block text-sm font-semibold text-navy">Channel<select value={channel} onChange={(event) => setChannel(event.target.value as Channel)} className="field mt-2"><option value="chat">Chat</option><option value="email">Email</option></select></label></div>
        <label className="mt-5 block text-sm font-semibold text-navy">Customer ID<input required value={customerId} onChange={(event) => setCustomerId(event.target.value)} className="field mt-2" placeholder="CUST-001" /></label>
        <label className="mt-5 block text-sm font-semibold text-navy">Customer message<textarea required value={rawText} onChange={(event) => setRawText(event.target.value)} className="field mt-2 min-h-40 resize-y leading-6" placeholder="Describe the customer’s request…" /></label>
        {mutation.isError && <div role="alert" className="mt-5 rounded-lg border border-amber/50 bg-amber/10 p-4 text-sm leading-6 text-[#704709]"><strong className="block">Ticket could not be submitted</strong>{mutation.error.message}</div>}
        <div className="mt-6 flex items-center gap-4"><button disabled={mutation.isPending} className="rounded-md bg-navy px-5 py-3 text-sm font-bold text-white transition hover:bg-navy/90 disabled:cursor-wait disabled:opacity-70">{mutation.isPending ? 'Submitting ticket…' : 'Submit ticket'}</button><p className="text-xs leading-5 text-ink/55">This sends a POST request to <code>/tickets</code>.</p></div>
      </form>
    </section>
    <aside className="xl:pt-[88px]"><div className="rounded-xl border border-navy/10 bg-ice/35 p-5"><p className="text-xs font-bold uppercase tracking-[0.16em] text-navy/65">Demo scenarios</p><p className="mt-2 text-sm leading-5 text-ink/65">Each loads a tested backend scenario and gives it a new ticket ID.</p><div className="mt-4 space-y-2">{examples.map((example) => <button key={example.title} type="button" onClick={() => useExample(example)} className="w-full rounded-lg border border-navy/15 bg-white p-3 text-left transition hover:border-navy/35 hover:bg-[#f8fbff]"><span className="block text-sm font-semibold text-navy">{example.title}</span><span className="mt-1 block text-xs text-ink/60">{example.detail}</span></button>)}</div></div></aside>
  </div>
}
