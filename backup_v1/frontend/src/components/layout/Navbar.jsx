import { Bell, Settings, Search } from 'lucide-react'

export default function Navbar() {
  return (
    <header className="h-16 bg-white border-b border-border px-6 flex items-center justify-between shrink-0">
      {/* Search Bar */}
      <div className="relative flex-1 max-w-lg">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          type="text"
          placeholder="Search orders, products..."
          className="w-full bg-[#F8FAFC] border-none rounded-full pl-11 pr-4 py-2 text-sm focus:ring-1 focus:ring-brand-400/20 outline-none placeholder:text-text-muted"
        />
      </div>

      {/* Right Icons */}
      <div className="flex items-center gap-5">
        <button className="relative p-2 text-text-muted hover:bg-bg-hover rounded-xl transition-all">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-accent-rose rounded-full border-2 border-white"></span>
        </button>
        <button className="p-2 text-text-muted hover:bg-bg-hover rounded-xl transition-all">
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </header>
  )
}
