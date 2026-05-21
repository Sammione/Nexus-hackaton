import React from 'react';

const PRODUCTS = [
    {
        id: 'food_3',
        title: 'Glover Court Suya',
        desc: 'Spicy, authentic smoke-kissed Nigerian Suya seasoned with Yaji.',
        domain: 'Food'
    },
    {
        id: 'mov_1',
        title: 'A Tribe Called Judah',
        desc: 'A hilarious and gripping Nollywood drama block-buster.',
        domain: 'Movies'
    },
    {
        id: 'amzn_2',
        title: 'Amazon Echo Device',
        desc: 'Smart voice assistant powered by Amazon Alexa.',
        domain: 'Electronics'
    },
    {
        id: 'drink_2',
        title: 'Fresh Palm Wine',
        desc: 'Sweet, bubbly, naturally tapped cultural drink served cold.',
        domain: 'Drinks'
    }
];

export default function SimulatorTab({
    selectedUser,
    selectedProduct,
    setSelectedProduct,
    nigerianFlavor,
    setNigerianFlavor,
    simulationResult,
    simulationLoading,
    onRunSimulation
}) {
    const history = selectedUser?.history || [];

    return (
        <div id="simulator-tab" className="tab-content active" style={{ display: 'block' }}>
            <div className="grid-1-2">
                {/* Left pane: Input triggers */}
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '520px' }}>
                    <div>
                        <h3 className="section-title">
                            <i className="fa-solid fa-sliders"></i>
                            Simulation Parameters
                        </h3>

                        <div style={{ marginBottom: '20px' }}>
                            <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '8px' }}>
                                Selected Persona:
                            </h4>
                            <div id="selected-user-summary" style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                                {selectedUser ? (
                                    <>
                                        <p style={{ fontSize: '13px', fontWeight: 700 }}>{selectedUser.name}</p>
                                        <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                                            Origin: {selectedUser.country || 'Unknown'} | Rating Habit: {selectedUser.rating_habit} ({selectedUser.avg_rating} avg)
                                        </p>
                                    </>
                                ) : (
                                    <>
                                        <p style={{ fontSize: '13px', fontWeight: 700 }}>No User Selected</p>
                                        <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                                            Select a user from the sidebar
                                        </p>
                                    </>
                                )}
                            </div>
                        </div>

                        <div className="product-selector">
                            <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                                Target Item to Review:
                            </h4>

                            {PRODUCTS.map(p => (
                                <div 
                                    key={p.id}
                                    className={`product-option ${selectedProduct === p.id ? 'selected' : ''}`}
                                    onClick={() => setSelectedProduct(p.id)}
                                >
                                    <div className="prod-info">
                                        <h4>{p.title}</h4>
                                        <p>{p.desc}</p>
                                    </div>
                                    <span className="domain-tag">{p.domain}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div>
                        <div className="control-bar">
                            <div 
                                className={`toggle-container ${nigerianFlavor ? 'active' : ''}`} 
                                onClick={() => setNigerianFlavor(!nigerianFlavor)}
                            >
                                <div className="toggle-switch"></div>
                                <div className="toggle-label">
                                    <span>Naija Flavor Mode</span>
                                    <span className="toggle-desc">Inject local slang & context</span>
                                </div>
                            </div>

                            <button className="btn-action" onClick={onRunSimulation} disabled={simulationLoading}>
                                {simulationLoading ? (
                                    <>
                                        <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', borderTopColor: '#fff', marginRight: '6px' }}></div>
                                        Simulating...
                                    </>
                                ) : (
                                    <>
                                        <i className="fa-solid fa-play"></i>
                                        Simulate Review
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right pane: Simulation Output & Few-Shot History */}
                <div className="grid-2">
                    {/* Few Shot User History */}
                    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                        <h3 className="section-title">
                            <i className="fa-solid fa-clock-rotate-left"></i>
                            User Historical Reviews
                        </h3>
                        <div style={{ flex: 1, overflowY: 'auto', maxHeight: '480px' }}>
                            {!selectedUser ? (
                                <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', paddingTop: '40px' }}>
                                    Select a user profile to view history
                                </p>
                            ) : history.length === 0 ? (
                                <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', paddingTop: '40px' }}>
                                    No historical purchases found. Operating in Cold-Start mode o.
                                </p>
                            ) : (
                                history.slice(0, 4).map((rev, index) => {
                                    const stars = '★'.repeat(rev.rating) + '☆'.repeat(5 - rev.rating);
                                    return (
                                        <div key={index} className="history-review-card">
                                            <h5>
                                                <span>{rev.product_title}</span>
                                                <span style={{ color: '#ffb300' }}>{stars}</span>
                                            </h5>
                                            <p style={{ fontWeight: 700, fontSize: '11px', marginTop: '4px', color: 'var(--text-main)' }}>
                                                {rev.title}
                                            </p>
                                            <p>"{rev.text}"</p>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </div>

                    {/* Live Simulation Output Box */}
                    <div className="glass-card simulator-result-box" style={{ height: '100%' }}>
                        <h3 className="section-title">
                            <i className="fa-solid fa-wand-magic-sparkles"></i>
                            Simulated Agent Output
                        </h3>
                        <div className="simulation-output" style={{ height: 'calc(100% - 60px)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                            {simulationLoading ? (
                                <div className="spinner"></div>
                            ) : simulationResult ? (
                                <div className="sim-review-card" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                                    <div>
                                        <div className="sim-review-header">
                                            <span className="stars-container">
                                                {'★'.repeat(simulationResult.rating) + '☆'.repeat(5 - simulationResult.rating)}
                                            </span>
                                            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>
                                                {new Date().toISOString().split('T')[0]}
                                            </span>
                                        </div>
                                        <h4 className="sim-review-title">{simulationResult.title}</h4>
                                        <div className="sim-review-body" style={{ overflowY: 'auto', maxHeight: '180px' }}>
                                            "{simulationResult.text}"
                                        </div>
                                    </div>
                                    <div style={{ marginTop: '20px', position: 'relative', height: '24px' }}>
                                        {simulationResult.is_simulated_by_llm ? (
                                            <span className="sim-indicator">
                                                <i className="fa-solid fa-robot"></i> LLM Simulated
                                            </span>
                                        ) : (
                                            <span className="sim-indicator" style={{ background: 'rgba(124,77,255,0.1)', color: 'var(--accent-purple)' }}>
                                                <i className="fa-solid fa-microchip"></i> Rule-Engine
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                <div className="output-empty">
                                    <i className="fa-solid fa-robot"></i>
                                    <p>Click "Simulate Review" to generate behavioral rating and critique copy.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
