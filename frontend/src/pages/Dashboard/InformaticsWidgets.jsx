import { TrendingUp, TrendingDown, Users, ShoppingCart, ArrowRight, Target, BrainCircuit } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function ForecastingWidget({ stats }) {
    const navigate = useNavigate();
    const slope = stats?.model_info?.slope || 0;
    const isUpward = slope >= 0;
    
    // Sum of 30-day forecast
    const totalForecast = stats?.forecast?.reduce((sum, item) => sum + (item.forecast || 0), 0) || 0;
    const r2 = stats?.model_info?.r2_score || 0;

    return (
        <div className="glass-card p-6 h-full flex flex-col justify-between">
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-widest flex items-center gap-2">
                        <Target className="w-4 h-4 text-blue-500" />
                        AI Growth Projection
                    </h3>
                    <span className="badge-brand">30D Forecast</span>
                </div>
                <div className="space-y-4">
                    {stats ? (
                        <div className={`flex items-end justify-between p-4 rounded-2xl border ${
                            isUpward 
                                ? 'bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-100 dark:border-emerald-800' 
                                : 'bg-amber-50/50 dark:bg-amber-900/10 border-amber-100 dark:border-amber-800'
                        }`}>
                            <div>
                                <p className={`text-[10px] font-black uppercase tracking-widest mb-1 ${
                                    isUpward ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
                                }`}>
                                    {isUpward ? 'Projected Revenue Trend Up' : 'Projected Trend Stable/Down'}
                                </p>
                                <p className={`text-2xl font-black ${
                                    isUpward ? 'text-emerald-700 dark:text-emerald-300' : 'text-amber-700 dark:text-amber-300'
                                }`}>
                                    EGP {totalForecast.toLocaleString(undefined, {maximumFractionDigits: 0})}
                                </p>
                                <p className="text-[9px] text-text-muted mt-1">R² confidence score: {r2}</p>
                            </div>
                            {isUpward ? (
                                <TrendingUp className="w-8 h-8 text-emerald-500 opacity-50" />
                            ) : (
                                <TrendingDown className="w-8 h-8 text-amber-500 opacity-50" />
                            )}
                        </div>
                    ) : (
                        <p className="text-xs text-text-muted italic py-4">No forecasting data available.</p>
                    )}
                </div>
            </div>
            <button 
                onClick={() => navigate('/analytics/forecast')}
                className="flex items-center gap-2 text-xs font-bold text-blue-600 hover:text-blue-500 transition-colors mt-6 pt-4 border-t border-border-main"
            >
                View detailed modeling <ArrowRight className="w-4 h-4" />
            </button>
        </div>
    );
}

export function SegmentationWidget({ data }) {
    const navigate = useNavigate();
    const segments = data?.segments || [];
    const totalCustomers = data?.model_info?.total_customers || 1;

    return (
        <div className="glass-card p-6 h-full flex flex-col justify-between">
            <div>
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-widest flex items-center gap-2">
                        <Users className="w-4 h-4 text-purple-500" />
                        Active Segments
                    </h3>
                    <BrainCircuit className="w-4 h-4 text-text-muted" />
                </div>
                <div className="space-y-3">
                    {segments.length > 0 ? (
                        segments.map(seg => {
                            const pct = Math.round((seg.count / totalCustomers) * 100);
                            // Fallback colors
                            const segmentColors = {
                                'Champion': 'bg-emerald-500',
                                'Loyal': 'bg-blue-500',
                                'At-Risk': 'bg-amber-500',
                                'Lost': 'bg-rose-500'
                            };
                            const barColor = segmentColors[seg.segment] || 'bg-slate-400';
                            
                            return (
                                <SegmentRow 
                                    key={seg.segment}
                                    label={seg.segment} 
                                    count={seg.count} 
                                    color={barColor} 
                                    pct={pct} 
                                />
                            );
                        })
                    ) : (
                        <p className="text-xs text-text-muted italic py-4">No segmentation details loaded.</p>
                    )}
                </div>
            </div>
            <button 
                onClick={() => navigate('/analytics')}
                className="flex items-center gap-2 text-xs font-bold text-blue-600 hover:text-blue-500 transition-colors mt-6 pt-4 border-t border-border-main"
            >
                Review RFM cohorts <ArrowRight className="w-4 h-4" />
            </button>
        </div>
    );
}

function SegmentRow({ label, count, color, pct }) {
    return (
        <div>
            <div className="flex justify-between text-[11px] font-bold mb-1">
                <span className="text-text-primary">{label}</span>
                <span className="text-text-muted">{count} pax ({pct}%)</span>
            </div>
            <div className="h-1.5 w-full bg-border-main rounded-full overflow-hidden">
                <div className={`${color} h-full rounded-full transition-all duration-1000`} style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
}

export function BasketAnalysisWidget({ bundles }) {
    const navigate = useNavigate();
    const topRule = bundles?.rules?.[0];

    return (
        <div className="glass-card p-6 h-full flex flex-col justify-between">
            <div>
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-widest flex items-center gap-2">
                        <ShoppingCart className="w-4 h-4 text-amber-500" />
                        Market Basket
                    </h3>
                    <span className="text-[10px] font-bold text-text-muted">LIFT ANALYTICS</span>
                </div>
                <div className="space-y-4">
                    {topRule ? (
                        <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-border-main">
                            <p className="text-[10px] font-black text-text-muted uppercase mb-2">High Confidence Bundle</p>
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-bold text-text-primary">{topRule.antecedents.join(', ')}</span>
                                <span className="text-text-muted font-mono">+</span>
                                <span className="text-xs font-bold text-text-primary">{topRule.consequents.join(', ')}</span>
                            </div>
                            <div className="mt-3 flex gap-4 border-t border-border-main pt-2">
                                <div>
                                    <p className="text-[9px] font-black text-text-muted uppercase">Confidence</p>
                                    <p className="text-xs font-black text-emerald-600">{Math.round(topRule.confidence * 100)}%</p>
                                </div>
                                <div>
                                    <p className="text-[9px] font-black text-text-muted uppercase">Lift Score</p>
                                    <p className="text-xs font-black text-blue-600">{topRule.lift.toFixed(1)}x</p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-border-main text-center">
                            <p className="text-xs text-text-muted italic py-4">No correlation rules found yet. Insufficient order history variance.</p>
                        </div>
                    )}
                </div>
            </div>
            <button 
                onClick={() => navigate('/analytics')}
                className="flex items-center gap-2 text-xs font-bold text-blue-600 hover:text-blue-500 transition-colors mt-6 pt-4 border-t border-border-main"
            >
                Analyze cross-sells <ArrowRight className="w-4 h-4" />
            </button>
        </div>
    );
}
