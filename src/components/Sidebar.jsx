import React, { useState } from 'react';

export default function Sidebar({ users, selectedUser, onSelectUser, loading }) {
    const [searchQuery, setSearchQuery] = useState('');

    const filteredUsers = users.filter(u => 
        u.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
        u.user_id.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <div className="sidebar-logo">
                    <i className="fa-solid fa-network-wired"></i>
                    NaijaAgentX
                </div>
                <div className="sidebar-subtitle">DSN x BCT LLM Agent Platform</div>
            </div>

            <div className="user-search">
                <i className="fa-solid fa-magnifying-glass"></i>
                <input 
                    type="text" 
                    placeholder="Search user personas..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            <div className="user-list">
                {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
                        <div className="spinner"></div>
                    </div>
                ) : filteredUsers.length === 0 ? (
                    <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', paddingTop: '20px' }}>
                        No personas found
                    </p>
                ) : (
                    filteredUsers.map((u) => {
                        const habitClass = u.rating_habit === 'critical' ? 'badge-habit-critical' : 'badge-habit-balanced';
                        const isActive = selectedUser && selectedUser.user_id === u.user_id;
                        
                        return (
                            <div 
                                key={u.user_id}
                                className={`user-card ${isActive ? 'active' : ''}`}
                                onClick={() => onSelectUser(u.user_id)}
                            >
                                <div className="user-card-title">
                                    <span>{u.name}</span>
                                    <span style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                                        {u.reviews_count} rev
                                    </span>
                                </div>
                                <div className="user-meta-badges">
                                    <span className="badge badge-rating">
                                        <i className="fa-solid fa-star"></i> {u.avg_rating}
                                    </span>
                                    <span className={`badge ${habitClass}`}>{u.rating_habit}</span>
                                    <span className="badge badge-country">{u.country || 'NG'}</span>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
