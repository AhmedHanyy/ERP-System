import { useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowLeft, Home } from 'lucide-react'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100 p-6">
      <div className="max-w-md w-full text-center space-y-8 animate-in fade-in duration-500">
        <div className="relative">
          <div className="w-24 h-24 rounded-3xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center mx-auto relative z-10 rotate-6">
            <AlertCircle className="w-12 h-12 text-blue-400 -rotate-6" />
          </div>
          <div className="absolute inset-0 bg-blue-500/10 blur-2xl rounded-full scale-75"></div>
        </div>

        <div className="space-y-3">
          <p className="text-[11px] font-black text-blue-500 uppercase tracking-[0.25em]">Error Code: 404</p>
          <h1 className="text-4xl font-black text-white tracking-tight">Resource Not Located</h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            The database registry does not contain the page or record you are requesting. It may have been relocated or restricted.
          </p>
        </div>

        <div className="flex gap-4 pt-4 justify-center">
          <button 
            onClick={() => navigate(-1)} 
            className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Go Back
          </button>
          <button 
            onClick={() => navigate('/dashboard')} 
            className="px-5 py-2.5 bg-blue-600 hover:opacity-90 text-white rounded-xl text-sm font-bold transition-all flex items-center gap-2 shadow-lg shadow-blue-500/15"
          >
            <Home className="w-4 h-4" /> Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}
