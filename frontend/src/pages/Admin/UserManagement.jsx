import { useState, useEffect } from 'react';
import { Users as UsersIcon, UserPlus, MoreVertical, Edit2, ShieldAlert, LogIn, Mail, X, Save } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function UserManagement() {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingUser, setEditingUser] = useState(null);

    const [newUserForm, setNewUserForm] = useState({
        username: '',
        email: '',
        role: 'Customer Service',
        password: ''
    });

    const [editUserForm, setEditUserForm] = useState({
        email: '',
        role: '',
        password: ''
    });

    const fetchUsers = async () => {
        try {
            const res = await axios.get('/api/admin/users');
            setUsers(res.data);
        } catch (err) {
            toast.error('Failed to load system users');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => { fetchUsers() }, []);

    const toggleUserStatus = async (userId, currentStatus) => {
        const newStatus = currentStatus === 'Active' ? 'Inactive' : 'Active';
        try {
            await axios.patch(`/api/admin/users/${userId}`, { status: newStatus });
            toast.success(`User marked as ${newStatus}`);
            fetchUsers();
        } catch {
            toast.error('Status update failed');
        }
    };

    const handleCreateUser = async (e) => {
        e.preventDefault();
        try {
            await axios.post('/api/admin/users', newUserForm);
            toast.success('User provisioned successfully');
            setShowCreateModal(false);
            setNewUserForm({ username: '', email: '', role: 'Customer Service', password: '' });
            fetchUsers();
        } catch (err) {
            toast.error(err.response?.data?.message || 'Failed to provision user');
        }
    };

    const handleEditClick = (user) => {
        setEditingUser(user);
        setEditUserForm({
            email: user.email,
            role: user.role,
            password: '' // default blank (don't update password unless typed)
        });
    };

    const handleUpdateUser = async (e) => {
        e.preventDefault();
        try {
            const payload = {
                email: editUserForm.email,
                role: editUserForm.role
            };
            if (editUserForm.password) {
                payload.password = editUserForm.password;
            }
            await axios.patch(`/api/admin/users/${editingUser.id}`, payload);
            toast.success('User updated successfully');
            setEditingUser(null);
            fetchUsers();
        } catch (err) {
            toast.error('Failed to update user');
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-black text-text-primary tracking-tight">User Governance</h1>
                    <p className="text-text-muted font-medium mt-1">Manage institutional access, roles and security statuses.</p>
                </div>
                <button onClick={() => setShowCreateModal(true)} className="btn-primary">
                    <UserPlus className="w-5 h-5" />
                    Provision New User
                </button>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard 
                    label="Total Personnel" 
                    value={users.length} 
                    icon={<UsersIcon className="w-6 h-6 text-blue-500" />} 
                />
                <StatCard 
                    label="Active Sessions" 
                    value={users.filter(u => u.status === 'Active').length} 
                    icon={<LogIn className="w-6 h-6 text-emerald-500" />} 
                />
                <StatCard 
                    label="Admin Tier" 
                    value={users.filter(u => u.role === 'Admin').length} 
                    icon={<ShieldAlert className="w-6 h-6 text-amber-500" />} 
                />
            </div>

            {/* Users Table */}
            <div className="glass-card overflow-hidden">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>Identity</th>
                            <th>Organizational Role</th>
                            <th>Status</th>
                            <th>Last Activity</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan="5" className="text-center py-20 text-text-muted">Analyzing registry...</td></tr>
                        ) : users.map(user => (
                            <tr key={user.id}>
                                <td>
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-blue-600/10 text-blue-600 flex items-center justify-center font-bold text-xs uppercase">
                                            {user.username.slice(0,2)}
                                        </div>
                                        <div>
                                            <p className="font-bold text-text-primary">{user.username}</p>
                                            <p className="text-xs text-text-muted flex items-center gap-1">
                                                <Mail className="w-3 h-3" />
                                                {user.email}
                                            </p>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <span className="badge-brand">{user.role}</span>
                                </td>
                                <td>
                                    <button 
                                        onClick={() => toggleUserStatus(user.id, user.status)}
                                        className={user.status === 'Active' ? 'badge-success' : 'badge-danger'}
                                    >
                                        {user.status}
                                    </button>
                                </td>
                                <td>
                                    <p className="text-xs font-bold text-text-secondary">
                                        {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never logged in'}
                                    </p>
                                </td>
                                <td>
                                    <div className="flex items-center gap-2">
                                        <button 
                                            onClick={() => handleEditClick(user)}
                                            className="p-2 text-text-muted hover:text-blue-500 transition-colors"
                                            title="Edit user profile"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* CREATE USER MODAL */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-primary/80 backdrop-blur-sm">
                    <div className="w-full max-w-md bg-bg-secondary border border-border shadow-2xl rounded-2xl animate-scale-in overflow-hidden">
                        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg-hover/20">
                            <h2 className="text-lg font-semibold flex items-center gap-2 text-text-primary">
                                <UserPlus className="w-5 h-5 text-brand-500" />
                                Provision User Account
                            </h2>
                            <button onClick={() => setShowCreateModal(false)} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                        <form onSubmit={handleCreateUser} className="p-6 space-y-4">
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">Username</label>
                                <input 
                                    type="text" required className="input" placeholder="e.g. jdoe"
                                    value={newUserForm.username}
                                    onChange={e => setNewUserForm({...newUserForm, username: e.target.value})}
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">Email Address</label>
                                <input 
                                    type="email" required className="input" placeholder="e.g. jdoe@smarterp.ai"
                                    value={newUserForm.email}
                                    onChange={e => setNewUserForm({...newUserForm, email: e.target.value})}
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">System Role</label>
                                <select 
                                    className="select"
                                    value={newUserForm.role}
                                    onChange={e => setNewUserForm({...newUserForm, role: e.target.value})}
                                >
                                    <option value="Admin">Admin</option>
                                    <option value="Operations Manager">Operations Manager</option>
                                    <option value="Procurement Officer">Procurement Officer</option>
                                    <option value="Analytics Manager">Analytics Manager</option>
                                    <option value="Customer Service">Customer Service</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">Password</label>
                                <input 
                                    type="password" required className="input" placeholder="Min 4 characters"
                                    value={newUserForm.password}
                                    onChange={e => setNewUserForm({...newUserForm, password: e.target.value})}
                                />
                            </div>
                            <div className="pt-4 flex gap-3">
                                <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" className="btn-primary flex-1">
                                    <Save className="w-4 h-4" /> Save User
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* EDIT USER MODAL */}
            {editingUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-primary/80 backdrop-blur-sm">
                    <div className="w-full max-w-md bg-bg-secondary border border-border shadow-2xl rounded-2xl animate-scale-in overflow-hidden">
                        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-bg-hover/20">
                            <h2 className="text-lg font-semibold flex items-center gap-2 text-text-primary">
                                <Edit2 className="w-4.5 h-4.5 text-brand-500" />
                                Edit Account: {editingUser.username}
                            </h2>
                            <button onClick={() => setEditingUser(null)} className="p-2 rounded-xl hover:bg-bg-hover transition-colors">
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                        <form onSubmit={handleUpdateUser} className="p-6 space-y-4">
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">Email Address</label>
                                <input 
                                    type="email" required className="input"
                                    value={editUserForm.email}
                                    onChange={e => setEditUserForm({...editUserForm, email: e.target.value})}
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">System Role</label>
                                <select 
                                    className="select"
                                    value={editUserForm.role}
                                    onChange={e => setEditUserForm({...editUserForm, role: e.target.value})}
                                >
                                    <option value="Admin">Admin</option>
                                    <option value="Operations Manager">Operations Manager</option>
                                    <option value="Procurement Officer">Procurement Officer</option>
                                    <option value="Analytics Manager">Analytics Manager</option>
                                    <option value="Customer Service">Customer Service</option>
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-xs font-bold text-text-muted uppercase">New Password (optional)</label>
                                <input 
                                    type="password" className="input" placeholder="Leave blank to keep current"
                                    value={editUserForm.password}
                                    onChange={e => setEditUserForm({...editUserForm, password: e.target.value})}
                                />
                            </div>
                            <div className="pt-4 flex gap-3">
                                <button type="button" onClick={() => setEditingUser(null)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" className="btn-primary flex-1">
                                    <Save className="w-4 h-4" /> Save Changes
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatCard({ label, value, icon }) {
    return (
        <div className="glass-card p-6 flex items-center justify-between">
            <div>
                <p className="text-[11px] font-black text-text-muted uppercase tracking-widest">{label}</p>
                <p className="text-3xl font-black text-text-primary mt-1">{value}</p>
            </div>
            <div className="w-12 h-12 bg-bg-body rounded-2xl flex items-center justify-center border border-border-main">
                {icon}
            </div>
        </div>
    );
}
