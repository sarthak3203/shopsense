import { NavLink, Route, Routes } from 'react-router-dom'
import Overview from './pages/Overview'
import NewTicket from './pages/NewTicket'
import TicketDetail from './pages/TicketDetail'
import History from './pages/History'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${isActive ? 'bg-white/15 text-white' : 'text-ice/80 hover:bg-white/10 hover:text-white'}`

export default function App() {
  return (
    <div className="min-h-screen bg-[#f6f9ff] text-ink">
      <header className="border-b border-navy/20 bg-navy text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <NavLink to="/" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-ice text-navy"><LogoMark /></span>
            <span><span className="block font-display text-xl leading-none">ShopSense</span><span className="mt-1 block text-[10px] font-semibold uppercase tracking-[0.16em] text-ice/80">Operations Console</span></span>
          </NavLink>
          <nav className="flex items-center gap-1" aria-label="Primary navigation">
            <NavLink to="/" end className={navClass}>Overview</NavLink>
            <NavLink to="/tickets" className={navClass}>History</NavLink>
            <NavLink to="/new" className="ml-1 rounded-md bg-white px-3 py-2 text-sm font-semibold text-navy transition hover:bg-ice">New ticket</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/new" element={<NewTicket />} />
          <Route path="/tickets" element={<History />} />
          <Route path="/tickets/:id" element={<TicketDetail />} />
        </Routes>
      </main>
    </div>
  )
}

function LogoMark() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="2"><path d="M5 7h14M7 7l1 11h8l1-11M10 11v3M14 11v3M9 4h6" strokeLinecap="round" strokeLinejoin="round" /></svg>
}
