import { useState, useEffect } from 'react';
import { analyticsApi } from '@/services/api';
import { Activity, User, Clock, Table } from 'lucide-react';
import { PageLoader, ErrorState, EmptyState } from '@/components/shared/States';
import { format } from 'date-fns';

export default function AuditLogs() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = async () => {
        try {
            setLoading(true);
            const data = await analyticsApi.getAuditLogs();
            setLogs(data);
        } catch { setError('Failed to fetch system audit logs'); }
        finally { setLoading(false); }
    };

    useEffect(() => { load(); }, []);

    if (loading) return <PageLoader />;
    if (error) return <ErrorState message={error} onRetry={load} />;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="page-header">
                <h2 className="page-title text-slate-900">System Activity Ledger</h2>
                <p className="page-subtitle">Immutable audit trail of all administrative and operational actions.</p>
            </div>

            <div className="glass-card shadow-sm border-border overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-bg-hover border-b border-border">
                        <tr>
                            <th className="px-6 py-4 text-[10px] font-bold text-text-muted uppercase tracking-widest">Timestamp</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-text-muted uppercase tracking-widest">User</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-text-muted uppercase tracking-widest">Action</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-text-muted uppercase tracking-widest">Object</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-text-muted uppercase tracking-widest">New State</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {logs.map(log => (
                            <tr key={log.id} className="hover:bg-bg-hover transition-colors">
                                <td className="px-6 py-4 text-xs font-mono text-slate-400">
                                    <div className="flex items-center gap-2">
                                        <Clock className="w-3 h-3" />
                                        {format(new Date(log.timestamp), 'MMM d, HH:mm:ss')}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2 text-sm font-bold text-slate-700">
                                        <User className="w-3.5 h-3.5 text-blue-500" />
                                        {log.user}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="px-2.5 py-1 text-[10px] font-bold bg-slate-100 text-slate-600 rounded-lg uppercase tracking-tight">
                                        {log.action}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-xs text-slate-500">
                                    <div className="flex items-center gap-2">
                                        <Table className="w-3.5 h-3.5 text-slate-300" />
                                        {log.target}
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-xs font-mono text-blue-600 max-w-xs truncate">
                                    {log.new_value || '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {logs.length === 0 && <EmptyState title="No system logs recorded" icon={Activity} />}
            </div>
        </div>
    );
}
