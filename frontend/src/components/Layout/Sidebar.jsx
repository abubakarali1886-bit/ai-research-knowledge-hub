import {
  LayoutGrid,
  FileText,
  Search,
  MessageSquareText,
  BookOpenText,
  Upload,
  Bookmark,
  Settings,
  ShieldCheck,
  Activity,
  Tags,
} from 'lucide-react'

const researchNavItems = [
  { label: 'Dashboard', icon: LayoutGrid, section: 'dashboard' },
  { label: 'Research Documents', icon: FileText, section: 'documents' },
  { label: 'Semantic Search', icon: Search, section: 'search' },
  { label: 'Ask AI', icon: MessageSquareText, section: 'chat' },
  { label: 'Research Summaries', icon: BookOpenText, section: 'summarize' },
]

const adminNavItems = [
  { label: 'Dashboard', icon: LayoutGrid, section: 'admin' },
  { label: 'Users', icon: ShieldCheck, section: 'adminUsers' },
  { label: 'Research Documents', icon: FileText, section: 'adminDocuments' },
  { label: 'Document Processing', icon: Activity, section: 'adminProcessing' },
  { label: 'Research Topics', icon: Tags, section: 'adminTopics' },
  { label: 'Semantic Search', icon: Search, section: 'search' },
  { label: 'Research Summaries', icon: BookOpenText, section: 'summarize' },
  { label: 'Upload Document', icon: Upload, section: 'upload' },
  { label: 'Activity / Audit Logs', icon: Activity, section: 'adminActivity' },
]

const footerItems = [
  { label: 'Upload Document', icon: Upload, section: 'upload' },
  { label: 'Saved Research', icon: Bookmark, section: 'saved' },
]

const Sidebar = ({ activePage, setActivePage, user, adminMode = false }) => {
  const isActive = (section) => activePage === section
  const role = String(user?.role || '').toLowerCase()
  const canManageDocuments = ['admin', 'researcher'].includes(role)
  const navItems = adminMode ? adminNavItems : researchNavItems

  return (
    <aside className={`sidebar-panel min-h-full flex flex-col border-r border-[#24201b] bg-[#0b0b0c] text-white ${adminMode ? 'admin-sidebar w-[126px]' : 'w-[143px]'}`}>
      <div className="border-b border-white/10 px-2 py-4 text-center">
        <div className="flex flex-col items-center gap-2">
          <img src="/bot-logo.svg" alt="Bank of Tanzania" className="h-[58px] w-[62px] object-contain drop-shadow-[0_0_14px_rgba(209,177,95,0.45)]" />
          <div className="text-[9px] font-bold uppercase leading-3 tracking-[0.12em] text-[#f5f0e7]">AI Research Knowledge Hub</div>
          <div className="text-[8px] font-medium text-[#d5b968]">Bank of Tanzania</div>
        </div>
      </div>

      <nav className="flex-1 px-2 py-4">
        <div className="space-y-1.5">
          {navItems.map(({ label, icon: Icon, section }) => (
              <button
                key={label}
                type="button"
                onClick={() => setActivePage(section)}
                className={`group flex w-full items-center gap-2 rounded-lg px-2 py-2.5 text-left transition-all duration-200 ${
                  isActive(section)
                    ? 'bg-[#d0ad4c] text-[#111111] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.15)]'
                    : 'text-[#f4eee6]/75 hover:bg-white/5 hover:text-white'
                }`}
              >
                <Icon size={15} className={isActive(section) ? 'text-[#111111]' : 'text-[#d9bf72]'} />
                <span className="text-[0.68rem] font-medium leading-3">{label}</span>
              </button>
            ))}
        </div>

        <div className="my-5 h-px bg-white/10" />

        <div className="space-y-1.5">
          {(adminMode ? [{ label: 'Settings', icon: Settings, section: 'settings' }] : footerItems.filter(({ section }) => section !== 'upload' || canManageDocuments)).map(({ label, icon: Icon, section }) => (
            <button
              key={label}
              type="button"
              onClick={() => setActivePage(section)}
              className={`group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition-all duration-200 ${
                isActive(section)
                  ? 'bg-[#d0ad4c] text-[#111111]'
                  : 'text-[#f4eee6]/75 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon size={18} className={isActive(section) ? 'text-[#111111]' : 'text-[#d9bf72]'} />
              <span className="text-[0.95rem] font-medium">{label}</span>
            </button>
          ))}
        </div>
      </nav>

      <div className="mt-auto border-t border-white/10 px-2 py-3">
        {!adminMode && <div className="space-y-1.5">
          <button
            type="button"
            onClick={() => setActivePage('settings')}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2.5 text-[#f4eee6]/75 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Settings size={15} className="text-[#d9bf72]" />
            <span className="text-[0.68rem] font-medium">Settings</span>
          </button>
        </div>}

        <div className="mt-3 flex items-start gap-2 rounded-lg border border-[#d2b15a]/30 bg-[#1b1b1c] px-2 py-2 text-left">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#d0ad4c]/12 text-[#d0ad4c]">
            <ShieldCheck size={13} />
          </div>
          <div>
            <div className="text-[0.55rem] font-semibold uppercase leading-3 tracking-[0.08em] text-[#e8c872]">Authorized</div>
            <div className="text-[0.52rem] leading-3 text-[#e8e1d7]/80">Research Environment</div>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
