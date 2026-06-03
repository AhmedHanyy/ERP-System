import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Shield, ArrowRight, Lock, User as UserIcon } from 'lucide-react';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    
    const { user, login, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    // Auto-redirect already logged-in users
    useEffect(() => {
        if (user) {
            navigate('/dashboard');
        }
    }, [user, navigate]);

    // Demo Mode Logic
    useEffect(() => {
        const isDemo = import.meta.env.VITE_DEMO_MODE === 'true';
        if (isDemo && !location.state?.auto) {
            // Force logout on every fresh visit to login page in demo mode
            logout();
        }
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);
        
        try {
            await login(username, password, rememberMe);
            const destination = location.state?.from?.pathname || '/dashboard';
            navigate(destination);
        } catch (err) {
            setError('Account verification failed. Please check credentials.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen bg-bg-body">
            {/* Left Panel: Branding & Marketing (Desktop Only) */}
            <div className="hidden lg:flex w-1/2 bg-slate-900 dark:bg-black relative overflow-hidden flex-col justify-between p-12">
                <div className="absolute inset-0 opacity-20 pointer-events-none">
                    <div className="absolute top-[-10%] right-[-10%] w-[60%] h-[60%] bg-blue-500 rounded-full blur-[120px]" />
                    <div className="absolute bottom-[-10%] left-[-10%] w-[60%] h-[60%] bg-indigo-600 rounded-full blur-[120px]" />
                </div>
                
                <div className="relative z-10">
                    <div className="flex items-center gap-3 text-white mb-12">
                        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                            <Layout className="w-6 h-6" />
                        </div>
                        <span className="text-xl font-black tracking-tighter">Smart<span className="text-blue-500">ERP</span></span>
                    </div>
                    
                    <h1 className="text-5xl font-black text-white leading-tight mb-6">
                        The Next Generation of <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">Decision Intelligence.</span>
                    </h1>
                    <p className="text-slate-400 text-lg max-w-md leading-relaxed">
                        An integrated ecosystem powered by advanced informatics, predictive forecasting, and behavioral analytics.
                    </p>
                </div>

                <div className="relative z-10 flex items-center gap-8 text-slate-500 text-xs font-bold uppercase tracking-widest">
                    <span>Precision Data</span>
                    <div className="w-1 h-1 bg-slate-700 rounded-full" />
                    <span>Secure Access</span>
                    <div className="w-1 h-1 bg-slate-700 rounded-full" />
                    <span>Enterprise Ready</span>
                </div>
            </div>

            {/* Right Panel: Login Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-bg-body">
                <div className="w-full max-w-md">
                    <div className="mb-10 lg:hidden text-center">
                        <Layout className="w-12 h-12 text-blue-600 mx-auto mb-4" />
                        <h1 className="text-2xl font-black tracking-tighter text-text-primary">Smart<span className="text-blue-500">ERP</span></h1>
                    </div>

                    <div className="mb-10">
                        <h2 className="text-3xl font-black text-text-primary tracking-tight mb-2">Welcome Back</h2>
                        <p className="text-text-muted font-medium">Please enter your specialized credentials below.</p>
                    </div>
                    
                    {error && (
                        <div className="flex items-center gap-3 p-4 mb-8 bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-800 text-rose-600 dark:text-rose-400 rounded-2xl animate-shake">
                            <Shield className="w-5 h-5 shrink-0" />
                            <p className="text-sm font-bold">{error}</p>
                        </div>
                    )}
                    
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-[11px] font-black text-text-muted uppercase tracking-widest">System Identity</label>
                            <div className="relative group">
                                <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted group-focus-within:text-blue-500 transition-colors" />
                                <input 
                                    type="text" 
                                    required
                                    placeholder="Username"
                                    className="w-full bg-slate-50 dark:bg-slate-900 border border-border-main focus:border-blue-500 rounded-2xl pl-12 pr-4 py-4 text-sm font-medium text-text-primary outline-none transition-all"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[11px] font-black text-text-muted uppercase tracking-widest">Passphrase</label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted group-focus-within:text-blue-500 transition-colors" />
                                <input 
                                    type="password" 
                                    required
                                    placeholder="Password"
                                    className="w-full bg-slate-50 dark:bg-slate-900 border border-border-main focus:border-blue-500 rounded-2xl pl-12 pr-4 py-4 text-sm font-medium text-text-primary outline-none transition-all"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between py-2">
                            <label className="flex items-center gap-3 cursor-pointer group">
                                <div className={`w-5 h-5 rounded-md border-2 transition-all flex items-center justify-center ${rememberMe ? 'bg-blue-600 border-blue-600' : 'border-slate-300 dark:border-slate-700 bg-transparent'}`}>
                                    {rememberMe && <div className="w-2 h-2 bg-white rounded-full" />}
                                </div>
                                <input 
                                    type="checkbox" 
                                    className="hidden"
                                    checked={rememberMe}
                                    onChange={e => setRememberMe(e.target.checked)}
                                />
                                <span className="text-xs font-bold text-text-secondary group-hover:text-text-primary transition-colors">Remember this session</span>
                            </label>
                            <button type="button" className="text-xs font-bold text-blue-600 hover:text-blue-500">System Support?</button>
                        </div>

                        <button 
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-4 bg-slate-900 dark:bg-blue-600 text-white font-black rounded-2xl shadow-xl hover:shadow-blue-500/20 active:scale-[0.98] transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                        >
                            {isLoading ? 'Decrypting...' : (
                                <>
                                    Enter Ecosystem
                                    <ArrowRight className="w-5 h-5" />
                                </>
                            )}
                        </button>
                    </form>
                    
                    <div className="mt-12 pt-8 border-t border-border-main">
                        <div className="flex flex-wrap justify-center gap-3">
                            <DemoBadge label="Admin" user="admin" />
                            <DemoBadge label="Procurement" user="proc" />
                            <DemoBadge label="Operations" user="ops" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function DemoBadge({ label, user }) {
    return (
        <div className="px-3 py-2 bg-slate-100 dark:bg-slate-800 rounded-xl flex flex-col items-center gap-1 border border-border-main min-w-[100px]">
            <span className="text-[9px] font-black text-text-muted uppercase">{label}</span>
            <span className="text-[10px] font-mono font-bold text-text-primary">{user} / {user}</span>
        </div>
    );
}
