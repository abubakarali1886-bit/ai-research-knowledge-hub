import { Menu, Search, LogOut } from 'lucide-react'
import TanzaniaStripe from './TanzaniaStripe'

const Header = ({ onMenuClick, user, searchQuery, setSearchQuery, onSearch, onLogout, onProfileClick, compact = false }) => {
  const displayName = user?.full_name || user?.username || 'Not signed in'
  const displayRole = user?.role || 'Guest'
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('') || '?'

  return (
    <>
      <header className={`header-shell border-b border-[#d5c15b] bg-[#e8e7e1]/95 px-4 backdrop-blur-sm sm:px-6 ${compact ? 'admin-header-compact' : ''}`}>
        <div className={`relative mx-auto flex max-w-[1480px] flex-col items-center ${compact ? 'gap-0.5 py-1' : 'py-3'}`}>
          <button
            type="button"
            onClick={onMenuClick}
            className={`absolute left-0 inline-flex items-center justify-center rounded-lg border border-[#e6d7b5] bg-white/40 text-[#1b1b1b] transition-colors hover:border-[#d2b15a] hover:text-[#0b0b0c] ${compact ? 'top-1.5 h-8 w-8' : 'top-3 h-10 w-10'}`}
            aria-label="Toggle menu"
          >
            <Menu size={19} />
          </button>

          <div className="flex flex-col items-center gap-0.5 text-center">
            <img src="/bot-logo.svg" alt="Bank of Tanzania" className={`${compact ? 'h-5 w-7' : 'h-12 w-14'} object-contain drop-shadow-[0_0_12px_rgba(209,177,95,0.45)]`} />
            <div className={`${compact ? 'text-[0.55rem]' : 'text-sm'} font-bold uppercase tracking-[0.04em] text-[#151515]`}>AI Research Knowledge Hub</div>
            <div className={`${compact ? 'text-[0.42rem]' : 'text-[0.68rem]'} font-medium text-[#6a531d]`}>Bank of Tanzania</div>
          </div>

        </div>
      </header>
      <TanzaniaStripe />
      <div className={`header-search-row border-b border-[#e5dcc5] bg-[#f9f4e9]/90 px-4 sm:px-6 ${compact ? 'py-1' : 'py-3'}`}>
        <div className="mx-auto flex max-w-[1480px] items-center gap-4">
          <form onSubmit={onSearch} className="relative min-w-0 flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6d6258]" size={17} />
            <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} type="text" placeholder="Search for research, documents, topics..." className={`w-full rounded-xl border border-[#e4d7b9] bg-white/60 pl-10 pr-11 text-sm text-[#1f1d1b] placeholder:text-[#7a7063] outline-none transition-all focus:border-[#d2b15a] focus:bg-white ${compact ? 'py-1' : 'py-2.5'}`} />
            <button type="submit" aria-label="Search" className={`absolute right-2 top-1/2 flex -translate-y-1/2 items-center justify-center rounded-md border border-[#e8d9a5] bg-[#f7eed4] text-[#1d1d1d] shadow-sm transition-colors hover:border-[#d2b15a] hover:bg-[#f0dfab] ${compact ? 'h-7 w-7' : 'h-8 w-8'}`}>
              <Search size={15} />
            </button>
          </form>
          <div className="flex shrink-0 items-center gap-2 border-l border-[#e0d4b7] pl-3">
            <button type="button" onClick={onProfileClick} className="flex min-w-0 items-center gap-2 rounded-lg p-1 text-left hover:bg-white/40" title="Open profile">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#111111] text-xs font-black text-[#f0d890] ring-2 ring-[#f0d890]/20">{initials}</div>
              <div className="hidden min-w-0 leading-tight sm:block"><div className="truncate text-[0.68rem] font-semibold text-[#151515]">{displayName}</div><div className="text-[0.58rem] capitalize text-[#5c564f]">{displayRole}</div></div>
            </button>
            <button type="button" onClick={onLogout} aria-label="Log out" title="Log out" className="rounded-md p-2 text-[#5c6463] hover:bg-white/50"><LogOut size={16} /></button>
          </div>
        </div>
      </div>
    </>
  )
}

export default Header