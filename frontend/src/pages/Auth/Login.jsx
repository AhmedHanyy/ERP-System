import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Login() {
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('admin');
    const [error, setError] = useState(null);
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await login(username, password);
            const destination = location.state?.from?.pathname || '/dashboard';
            navigate(destination);
        } catch (err) {
            setError('Invalid credentials');
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-50">
            <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-xl border border-slate-100">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-slate-800 mb-2">SmartERP</h1>
                    <p className="text-slate-500">Corporate Decision Support System</p>
                </div>
                
                {error && <div className="p-4 mb-6 text-sm text-red-600 bg-red-50 rounded-lg">{error}</div>}
                
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Username</label>
                        <input 
                            type="text" 
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Password</label>
                        <input 
                            type="password" 
                            className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                        />
                    </div>
                    <button 
                        type="submit"
                        className="w-full py-4 bg-slate-900 text-white font-semibold rounded-xl hover:bg-slate-800 active:scale-[0.98] transition-all"
                    >
                        Login to Ecosystem
                    </button>
                </form>
                
                <div className="mt-8 pt-8 border-t border-slate-100 text-center">
                    <p className="text-xs text-slate-400 uppercase tracking-widest px-4">Demo Credentials</p>
                    <div className="flex justify-center gap-4 mt-4 text-xs font-mono text-slate-500">
                        <span>admin / admin</span>
                        <span>proc / proc</span>
                        <span>ops / ops</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
