import React, { useState, useEffect, useRef } from 'react';
import { Chart } from 'chart.js/auto';

export default function RecommendationTab({
    selectedUser,
    chatMessages,
    setChatMessages,
    chatInput,
    setChatInput,
    onSendChatMessage,
    chatLoading,
    evolvingMemory,
    recommendedItems,
    onPersonalizeAction
}) {
    const [prefSubTab, setPrefSubTab] = useState('radar'); // 'radar' or 'faiss'
    const [reasoningOpen, setReasoningOpen] = useState({}); // { messageId: boolean }

    const radarCanvasRef = useRef(null);
    const barCanvasRef = useRef(null);
    const graphCanvasRef = useRef(null);

    const radarChartInstance = useRef(null);
    const barChartInstance = useRef(null);
    const graphAnimationFrameRef = useRef(null);

    const graphNodesRef = useRef([]);
    const graphLinksRef = useRef([]);

    // 1. Render Preference Radar Chart
    useEffect(() => {
        if (prefSubTab !== 'radar' || !radarCanvasRef.current) return;

        const user = selectedUser;
        const isCold = !user || user.reviews_count === 0;
        let movies = 50, food = 50, drinks = 50, books = 50, electronics = 50;

        if (user && !isCold && user.history) {
            user.history.forEach(rev => {
                const dom = rev.domain ? rev.domain.toLowerCase() : "electronics";
                const points = rev.rating * 15;
                if (dom.includes("movie")) movies = Math.min(100, movies + points - 15);
                else if (dom.includes("food")) food = Math.min(100, food + points - 15);
                else if (dom.includes("drink")) drinks = Math.min(100, drinks + points - 15);
                else if (dom.includes("book")) books = Math.min(100, books + points - 15);
                else electronics = Math.min(100, electronics + points - 15);
            });
        } else if (user && isCold && user.country === "NG") {
            movies = 85; food = 90; drinks = 80; books = 65; electronics = 40;
        }

        const chartData = [movies, food, drinks, books, electronics];

        if (radarChartInstance.current) {
            radarChartInstance.current.data.datasets[0].data = chartData;
            radarChartInstance.current.update();
        } else {
            const ctx = radarCanvasRef.current.getContext('2d');
            radarChartInstance.current = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: ['Movies', 'Food', 'Drinks', 'Books', 'Electronics'],
                    datasets: [{
                        label: 'Domain Affinity',
                        data: chartData,
                        backgroundColor: 'rgba(124, 77, 255, 0.15)',
                        borderColor: 'rgba(124, 77, 255, 0.85)',
                        pointBackgroundColor: '#00e5ff',
                        pointBorderColor: '#fff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            angleLines: { color: 'rgba(255, 255, 255, 0.08)' },
                            grid: { color: 'rgba(255, 255, 255, 0.08)' },
                            pointLabels: { color: '#9e95c7', font: { family: 'Outfit', size: 10 } },
                            ticks: { display: false },
                            min: 0,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        return () => {
            if (radarChartInstance.current) {
                radarChartInstance.current.destroy();
                radarChartInstance.current = null;
            }
        };
    }, [selectedUser, prefSubTab]);

    // 2. Render FAISS Dense Search Bar Chart
    useEffect(() => {
        if (prefSubTab !== 'faiss' || !barCanvasRef.current) return;

        const labels = [];
        const scores = [];

        if (recommendedItems && recommendedItems.length > 0) {
            recommendedItems.forEach(item => {
                labels.push(item.title);
                scores.push(item.similarity_score || item.search_score || 0.65);
            });
        } else {
            labels.push('Sample Item 1', 'Sample Item 2');
            scores.push(0.75, 0.68);
        }

        if (barChartInstance.current) {
            barChartInstance.current.data.labels = labels;
            barChartInstance.current.data.datasets[0].data = scores;
            barChartInstance.current.update();
        } else {
            const ctx = barCanvasRef.current.getContext('2d');
            barChartInstance.current = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Dense Match (FAISS)',
                        data: scores,
                        backgroundColor: 'rgba(0, 229, 255, 0.45)',
                        borderColor: '#00e5ff',
                        borderWidth: 1.5,
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            beginAtZero: true,
                            min: 0,
                            max: 1,
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#9e95c7', size: 9 }
                        },
                        y: {
                            grid: { display: false },
                            ticks: {
                                color: '#f3f0ff',
                                font: { family: 'Outfit', size: 8 }
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        return () => {
            if (barChartInstance.current) {
                barChartInstance.current.destroy();
                barChartInstance.current = null;
            }
        };
    }, [recommendedItems, prefSubTab]);

    // 3. 2D Interactive Recommender Physics Graph
    useEffect(() => {
        const canvas = graphCanvasRef.current;
        if (!canvas) return;
        const gCtx = canvas.getContext('2d');

        const resize = () => {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight || 250;
            initializeGraph();
        };

        resize();
        window.addEventListener('resize', resize);

        function initializeGraph() {
            if (!canvas) return;
            const w = canvas.width;
            const h = canvas.height;
            const user = selectedUser;

            const nodes = [];
            const links = [];

            // Central User Node
            const centerNode = {
                id: 'user',
                label: user ? user.name.split(' ')[0] : 'User',
                type: 'user',
                x: w / 2,
                y: h / 2,
                targetX: w / 2,
                targetY: h / 2,
                radius: 20,
                color: '#8c5dff'
            };
            nodes.push(centerNode);

            // Demographic Twins (CF Neighbors)
            const twins = [
                { name: 'Ngozi', sim: 0.94 },
                { name: 'Chidi', sim: 0.89 }
            ];

            twins.forEach((twin, idx) => {
                const angle = (idx * Math.PI) - (Math.PI / 4);
                const dist = 75;
                const twinNode = {
                    id: `twin_${idx}`,
                    label: `${twin.name} (${twin.sim})`,
                    type: 'twin',
                    x: (w / 2) + Math.cos(angle) * dist + (Math.random() - 0.5) * 10,
                    y: (h / 2) + Math.sin(angle) * dist + (Math.random() - 0.5) * 10,
                    targetX: (w / 2) + Math.cos(angle) * dist,
                    targetY: (h / 2) + Math.sin(angle) * dist,
                    radius: 12,
                    color: '#00e5ff'
                };
                nodes.push(twinNode);
                links.push({ source: centerNode, target: twinNode, type: 'cf' });
            });

            // Items Nodes
            if (recommendedItems && recommendedItems.length > 0) {
                recommendedItems.forEach((item, idx) => {
                    const angle = (idx * (2 * Math.PI / recommendedItems.length)) + Math.PI / 2;
                    const dist = 90;
                    const itemNode = {
                        id: `item_${item.id}`,
                        label: item.title.split(' ')[0],
                        type: 'item',
                        x: (w / 2) + Math.cos(angle) * dist + (Math.random() - 0.5) * 15,
                        y: (h / 2) + Math.sin(angle) * dist + (Math.random() - 0.5) * 15,
                        targetX: (w / 2) + Math.cos(angle) * dist,
                        targetY: (h / 2) + Math.sin(angle) * dist,
                        radius: 15,
                        color: '#ffb300'
                    };
                    nodes.push(itemNode);
                    links.push({ source: centerNode, target: itemNode, type: 'rec' });
                });
            } else {
                // Initial catalog domain seeds
                const domains = ['Food', 'Movies', 'Drinks', 'Books'];
                domains.forEach((dom, idx) => {
                    const angle = (idx * (2 * Math.PI / domains.length));
                    const dist = 85;
                    const domNode = {
                        id: `dom_${idx}`,
                        label: dom,
                        type: 'dom',
                        x: (w / 2) + Math.cos(angle) * dist,
                        y: (h / 2) + Math.sin(angle) * dist,
                        targetX: (w / 2) + Math.cos(angle) * dist,
                        targetY: (h / 2) + Math.sin(angle) * dist,
                        radius: 11,
                        color: 'rgba(124, 77, 255, 0.45)'
                    };
                    nodes.push(domNode);
                    links.push({ source: centerNode, target: domNode, type: 'seed' });
                });
            }

            graphNodesRef.current = nodes;
            graphLinksRef.current = links;
        }

        initializeGraph();

        function animate() {
            if (!canvas || !gCtx) return;
            gCtx.clearRect(0, 0, canvas.width, canvas.height);

            const nodes = graphNodesRef.current;
            const links = graphLinksRef.current;

            // Draw link edges
            links.forEach(link => {
                // Find node references in local nodes array
                const srcNode = nodes.find(n => n.id === link.source.id);
                const trgNode = nodes.find(n => n.id === link.target.id);
                if (!srcNode || !trgNode) return;

                gCtx.beginPath();
                gCtx.moveTo(srcNode.x, srcNode.y);
                gCtx.lineTo(trgNode.x, trgNode.y);

                if (link.type === 'cf') {
                    gCtx.strokeStyle = 'rgba(0, 229, 255, 0.25)';
                    gCtx.setLineDash([4, 4]);
                } else if (link.type === 'rec') {
                    gCtx.strokeStyle = 'rgba(255, 179, 0, 0.45)';
                    gCtx.setLineDash([]);
                } else {
                    gCtx.strokeStyle = 'rgba(124, 77, 255, 0.25)';
                    gCtx.setLineDash([]);
                }

                gCtx.lineWidth = 1.5;
                gCtx.stroke();
                gCtx.setLineDash([]);
            });

            // Update node physics
            nodes.forEach(node => {
                node.x += (node.targetX - node.x) * 0.08;
                node.y += (node.targetY - node.y) * 0.08;

                // Add soft floating effect
                if (node.id !== 'user') {
                    const time = Date.now() * 0.002;
                    const offset = (node.id.charCodeAt(node.id.length - 1) || 0) * 10;
                    node.x += Math.sin(time + offset) * 0.15;
                    node.y += Math.cos(time + offset) * 0.15;
                }

                // Draw node
                gCtx.beginPath();
                gCtx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
                gCtx.fillStyle = node.color;
                gCtx.shadowColor = node.color;
                gCtx.shadowBlur = 8;
                gCtx.fill();
                gCtx.shadowBlur = 0;

                // Label text
                gCtx.font = 'bold 9px Outfit';
                gCtx.fillStyle = '#fff';
                gCtx.textAlign = 'center';
                gCtx.fillText(node.label, node.x, node.y + node.radius + 12);
            });

            graphAnimationFrameRef.current = requestAnimationFrame(animate);
        }

        animate();

        return () => {
            window.removeEventListener('resize', resize);
            if (graphAnimationFrameRef.current) {
                cancelAnimationFrame(graphAnimationFrameRef.current);
            }
        };
    }, [selectedUser, recommendedItems]);

    const toggleReasoning = (msgId) => {
        setReasoningOpen(prev => ({
            ...prev,
            [msgId]: !prev[msgId]
        }));
    };

    // Auto-scroll chat console
    const chatConsoleRef = useRef(null);
    useEffect(() => {
        if (chatConsoleRef.current) {
            chatConsoleRef.current.scrollTop = chatConsoleRef.current.scrollHeight;
        }
    }, [chatMessages, chatLoading]);

    return (
        <div id="recommendation-tab" className="tab-content active" style={{ display: 'block' }}>
            <div className="grid-1-2" style={{ height: '100%' }}>
                {/* Side: active profile preference analysis */}
                <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '520px' }}>
                    <div>
                        <h3 className="section-title">
                            <i className="fa-solid fa-address-card"></i>
                            Recommender Dashboard
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div style={{ background: 'rgba(124, 77, 255, 0.05)', padding: '14px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                                <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-cyan)', display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Active User Context</span>
                                    {selectedUser && (
                                        <span className={`badge ${selectedUser.reviews_count === 0 ? 'badge-habit-critical' : 'badge-rating'}`}>
                                            {selectedUser.reviews_count === 0 ? "Cold-Start" : "Active"}
                                        </span>
                                    )}
                                </h4>
                                <p style={{ fontSize: '13px', fontWeight: 700, marginTop: '8px' }}>
                                    {selectedUser ? selectedUser.name : 'None Selected'}
                                </p>
                                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                                    {selectedUser ? `${selectedUser.rating_habit.toUpperCase()} persona | Country: ${selectedUser.country}` : 'Select a user to analyze preferences'}
                                </p>
                            </div>

                            {/* Segmented tabs */}
                            <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '8px', marginTop: '2px', gap: '16px' }}>
                                <span 
                                    onClick={() => setPrefSubTab('radar')}
                                    style={{ 
                                        fontSize: '12px', 
                                        fontWeight: 700, 
                                        color: prefSubTab === 'radar' ? 'var(--accent-cyan)' : 'var(--text-muted)', 
                                        cursor: 'pointer', 
                                        borderBottom: prefSubTab === 'radar' ? '2px solid var(--accent-cyan)' : 'none',
                                        paddingBottom: '4px', 
                                        transition: 'all 0.3s' 
                                    }}
                                >
                                    Preference Profile
                                </span>
                                <span 
                                    onClick={() => setPrefSubTab('faiss')}
                                    style={{ 
                                        fontSize: '12px', 
                                        fontWeight: 700, 
                                        color: prefSubTab === 'faiss' ? 'var(--accent-cyan)' : 'var(--text-muted)', 
                                        cursor: 'pointer', 
                                        borderBottom: prefSubTab === 'faiss' ? '2px solid var(--accent-cyan)' : 'none',
                                        paddingBottom: '4px', 
                                        transition: 'all 0.3s' 
                                    }}
                                >
                                    Search Vectors
                                </span>
                            </div>

                            {/* Domain Radar Pane */}
                            <div style={{ display: prefSubTab === 'radar' ? 'block' : 'none', position: 'relative', height: '180px', width: '100%' }}>
                                <canvas ref={radarCanvasRef}></canvas>
                            </div>

                            {/* FAISS Dense Pane */}
                            <div style={{ display: prefSubTab === 'faiss' ? 'block' : 'none', position: 'relative', height: '180px', width: '100%' }}>
                                <canvas ref={barCanvasRef}></canvas>
                            </div>
                        </div>
                    </div>

                    {/* Interactive Recommender Graph */}
                    <div className="graph-box-container" style={{ height: '200px' }}>
                        <canvas ref={graphCanvasRef}></canvas>
                        <div className="graph-legend">
                            <div className="legend-item">
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#8c5dff', display: 'inline-block' }}></span>
                                User
                            </div>
                            <div className="legend-item">
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00e5ff', display: 'inline-block' }}></span>
                                Twin (CF)
                            </div>
                            <div className="legend-item">
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ffb300', display: 'inline-block' }}></span>
                                Item
                            </div>
                        </div>
                    </div>

                    {/* Dynamic In-Session Memory Block */}
                    <div style={{ marginTop: '14px', padding: '14px', borderRadius: '12px', background: 'rgba(0, 229, 255, 0.02)', border: '1px dashed rgba(0, 229, 255, 0.25)', fontSize: '12px' }}>
                        <h5 style={{ fontWeight: 800, color: 'var(--accent-cyan)', fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <i className="fa-solid fa-microchip"></i>
                            Evolving Session Memory
                        </h5>
                        {evolvingMemory ? (
                            <div style={{ color: 'var(--text-muted)', lineHeight: '1.4' }}>
                                <div style={{ marginBottom: '6px' }}>
                                    <strong>Likes: </strong>
                                    {evolvingMemory.liked_categories.length > 0 ? (
                                        evolvingMemory.liked_categories.map(c => (
                                            <span key={c} style={{ display: 'inline-block', padding: '2px 6px', background: 'rgba(0,230,118,0.1)', border: '1px solid rgba(0,230,118,0.25)', borderRadius: '4px', marginRight: '4px', fontWeight: 700, color: '#00e676', fontSize: '10px', textTransform: 'uppercase' }}>
                                                {c}
                                            </span>
                                        ))
                                    ) : (
                                        <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>None</span>
                                    )}
                                </div>
                                <div style={{ marginBottom: '6px' }}>
                                    <strong>Dislikes: </strong>
                                    {evolvingMemory.disliked_traits.length > 0 ? (
                                        evolvingMemory.disliked_traits.map(t => (
                                            <span key={t} style={{ display: 'inline-block', padding: '2px 6px', background: 'rgba(255,23,68,0.1)', border: '1px solid rgba(255,23,68,0.25)', borderRadius: '4px', marginRight: '4px', fontWeight: 700, color: '#ff1744', fontSize: '10px', textTransform: 'uppercase' }}>
                                                {t}
                                            </span>
                                        ))
                                    ) : (
                                        <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>None</span>
                                    )}
                                </div>
                                <div>
                                    <strong>Budget Preference: </strong>
                                    <span style={{ display: 'inline-block', padding: '2px 6px', background: 'rgba(0,229,255,0.1)', border: '1px solid rgba(0,229,255,0.25)', borderRadius: '4px', fontWeight: 700, color: '#00e5ff', fontSize: '10px', textTransform: 'uppercase' }}>
                                        {evolvingMemory.budget}
                                    </span>
                                </div>
                            </div>
                        ) : (
                            <div style={{ color: 'var(--text-muted)', lineHeight: '1.4' }}>
                                No active conversation profile. In-session preferences will be dynamically extracted in real time.
                            </div>
                        )}
                    </div>
                </div>

                {/* Main pane: Conversational Reasoning Engine Console */}
                <div className="chat-container">
                    <div className="chat-console" ref={chatConsoleRef}>
                        {chatMessages.map((msg, index) => {
                            const isUser = msg.role === 'user';
                            return (
                                <div key={index} className={`chat-msg ${isUser ? 'user' : 'assistant'}`}>
                                    {/* Reasoning block for assistant replies */}
                                    {!isUser && msg.reasoning && (
                                        <>
                                            <div className="agent-reasoning-toggle" onClick={() => toggleReasoning(index)}>
                                                <i className="fa-solid fa-terminal"></i>
                                                Agent Reasoning Chain (CoT)
                                                <i className={`fa-solid ${reasoningOpen[index] ? 'fa-chevron-up' : 'fa-chevron-down'}`} style={{ marginLeft: '6px' }}></i>
                                            </div>
                                            {reasoningOpen[index] && (
                                                <div className="agent-reasoning-console">
                                                    {msg.reasoning}
                                                </div>
                                            )}
                                        </>
                                    )}

                                    {/* Standard bubble text */}
                                    <div className="chat-bubble" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br>') }} />

                                    {/* Recommended items block */}
                                    {!isUser && msg.items && msg.items.length > 0 && (
                                        <div className="recommender-item-container">
                                            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                                                <span>Recommender Reranking Score Details</span>
                                                <span style={{ color: 'var(--accent-purple)' }}>
                                                    <i className="fa-solid fa-ranking-star"></i> Multi-Stage Blending
                                                </span>
                                            </div>

                                            {msg.items.map((item) => {
                                                const sim = item.similarity_score || 0.65;
                                                const cf = item.cf_score || 0.0;
                                                const gr = item.graph_score || 0.0;
                                                const ce = item.cross_encoder_score || 0.0;
                                                const final = item.search_score || 0.88;

                                                return (
                                                    <div key={item.id} style={{ marginTop: '8px', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                                        <div className="rec-item-header">
                                                            <span className="rec-item-title">{item.title}</span>
                                                            <div className="feedback-actions">
                                                                <button 
                                                                    className="btn-feedback like-btn" 
                                                                    onClick={(e) => onPersonalizeAction(item.id, 'like', e.currentTarget)} 
                                                                    title="Upvote product to learn preference"
                                                                >
                                                                    <i className="fa-solid fa-thumbs-up"></i>
                                                                </button>
                                                                <button 
                                                                    className="btn-feedback dislike-btn" 
                                                                    onClick={(e) => onPersonalizeAction(item.id, 'dislike', e.currentTarget)} 
                                                                    title="Downvote product to blacklist traits"
                                                                >
                                                                    <i className="fa-solid fa-thumbs-down"></i>
                                                                </button>
                                                            </div>
                                                        </div>
                                                        <div className="rerank-console">
                                                            <div className="rerank-row">
                                                                <span>FAISS Dense Similarity Match</span>
                                                                <span style={{ textAlign: 'right', fontWeight: 700 }}>{sim.toFixed(4)}</span>
                                                            </div>
                                                            <div className="rerank-progress-container" style={{ marginBottom: '8px' }}>
                                                                <div className="rerank-progress-bar" style={{ width: `${sim * 100}%` }}></div>
                                                            </div>

                                                            <div className="rerank-row">
                                                                <span>User Collaborative Filtering</span>
                                                                <span style={{ textAlign: 'right', fontWeight: 700, color: 'var(--accent-cyan)' }}>{cf.toFixed(4)}</span>
                                                            </div>
                                                            <div className="rerank-progress-container" style={{ marginBottom: '8px' }}>
                                                                <div className="rerank-progress-bar" style={{ width: `${cf * 100}%`, background: 'var(--accent-cyan)' }}></div>
                                                            </div>

                                                            <div className="rerank-row">
                                                                <span>Graph Co-occurrence Network</span>
                                                                <span style={{ textAlign: 'right', fontWeight: 700, color: 'var(--accent-green)' }}>{gr.toFixed(4)}</span>
                                                            </div>
                                                            <div className="rerank-progress-container" style={{ marginBottom: '8px' }}>
                                                                <div className="rerank-progress-bar" style={{ width: `${gr * 100}%`, background: 'var(--accent-green)' }}></div>
                                                            </div>

                                                            <div className="rerank-row">
                                                                <span>Cross-Encoder Lexical Overlap</span>
                                                                <span style={{ textAlign: 'right', fontWeight: 700, color: 'var(--accent-purple)' }}>{ce.toFixed(4)}</span>
                                                            </div>
                                                            <div className="rerank-progress-container" style={{ marginBottom: '8px' }}>
                                                                <div className="rerank-progress-bar" style={{ width: `${Math.min(100, ce * 100)}%`, background: 'var(--accent-purple)' }}></div>
                                                            </div>

                                                            <div className="rerank-row" style={{ marginTop: '6px', fontWeight: 700, color: '#fff' }}>
                                                                <span>Final Blended Score</span>
                                                                <span style={{ textAlign: 'right', color: '#ffb300' }}>{final.toFixed(4)}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}

                        {chatLoading && (
                            <div className="chat-msg assistant">
                                <div className="chat-bubble" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    <div className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></div>
                                    Reasoning...
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Chat Input Bar */}
                    <div className="chat-input-bar">
                        <input 
                            type="text" 
                            placeholder="Type a message (e.g. 'Recommend a Nollywood movie or street food')..."
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) => { if(e.key === 'Enter') onSendChatMessage(); }}
                            disabled={chatLoading}
                        />
                        <button onClick={onSendChatMessage} disabled={chatLoading}>
                            <i className="fa-solid fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
