import { useState } from 'react'
import { PageHeader, TicketHistoryList } from '../components'
import { clearHistory, getHistory } from '../lib/history'

export default function History() {
  const [tickets, setTickets] = useState(getHistory)
  const clear = () => { clearHistory(); setTickets([]) }
  return <><div className="flex flex-wrap items-end justify-between gap-4"><PageHeader eyebrow="Browser-local records" title="Ticket history"><p className="mt-3 max-w-2xl text-sm leading-6 text-ink/65">These references are saved in localStorage so you can revisit tickets without a backend list endpoint.</p></PageHeader>{tickets.length > 0 && <button onClick={clear} className="mb-8 rounded-md border border-navy/25 bg-white px-3.5 py-2 text-sm font-semibold text-navy transition hover:bg-ice">Clear browser history</button>}</div><TicketHistoryList tickets={tickets} /></>
}
