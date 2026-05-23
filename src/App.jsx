import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import SimulatorTab from './components/SimulatorTab';
import RecommendationTab from './components/RecommendationTab';
import ScienceTab from './components/ScienceTab';

export default function App() {
    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState(null);
    const [selectedProduct, setSelectedProduct] = useState('food_3');
    const [nigerianFlavor, setNigerianFlavor] = useState(true);
    const [activeTab, setActiveTab] = useState('simulator-tab');

    // Chat state
    const [chatHistory, setChatHistory] = useState([]);
    const [chatMessages, setChatMessages] = useState([
        {
            role: 'assistant',
            content: 'Hello o! I am **NaijaAgentX**, your reasoning recommendation companion. Pick a profile on the left and ask me for recommendations tailored to their taste, abeg!'
        }
    ]);
    const [chatInput, setChatInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);

    // Simulation state
    const [simulationResult, setSimulationResult] = useState(null);
    const [simulationLoading, setSimulationLoading] = useState(false);

    // Science/Evaluation state
    const [ablationData, setAblationData] = useState(null);
    const [humanEvalData, setHumanEvalData] = useState(null);

    // Dashboard dynamic preference loop states
    const [evolvingMemory, setEvolvingMemory] = useState(null);
    const [recommendedItems, setRecommendedItems] = useState([]);
    const [itemPreferences, setItemPreferences] = useState({}); // { [itemId]: 'like' | 'dislike' }

    // Roster loading state
    const [rosterLoading, setRosterLoading] = useState(true);

    // Toast state
    const [toasts, setToasts] = useState([]);

    const showToast = (message, icon = 'fa-circle-info') => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message, icon }]);
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 3000);
    };

    // Load initial configurations
    useEffect(() => {
        // Fetch Users
        fetch('/api/users')
            .then(res => res.json())
            .then(data => {
                setUsers(data);
                setRosterLoading(false);
                if (data.length > 0) {
                    handleSelectUser(data[0].user_id, data);
                }
            })
            .catch(err => {
                console.error("Error fetching users:", err);
                setRosterLoading(false);
            });

        // Fetch Ablation Studies
        fetch('/api/ablation')
            .then(res => res.json())
            .then(data => setAblationData(data))
            .catch(err => console.error("Error fetching ablation studies:", err));

        // Fetch Human Evaluation
        fetch('/api/human_eval')
            .then(res => res.json())
            .then(data => {
                if (data.status !== "missing") {
                    setHumanEvalData(data);
                }
            })
            .catch(err => console.error("Error fetching human studies:", err));
    }, []);

    const handleSelectUser = (userId, customUsersList = null) => {
        const roster = customUsersList || users;
        const user = roster.find(u => u.user_id === userId);
        if (!user) return;

        setSelectedUser(user);

        // Reset conversation and session memory
        setChatHistory([]);
        setChatMessages([
            {
                role: 'assistant',
                content: `Hello o! I am **NaijaAgentX**, your reasoning recommendation companion. Pick a profile on the left and ask me for recommendations tailored to **${user.name.split(' ')[0]}'s** taste, abeg!`
            }
        ]);
        setEvolvingMemory(null);
        setRecommendedItems([]);
        setItemPreferences({});
        setSimulationResult(null);
    };

    const runSimulation = () => {
        if (!selectedUser) {
            alert("Abeg select a user from the sidebar first!");
            return;
        }

        setSimulationLoading(true);
        setSimulationResult(null);

        fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: selectedUser.user_id,
                product_id: selectedProduct,
                use_nigerian_flavor: nigerianFlavor
            })
        })
            .then(res => res.json())
            .then(data => {
                setSimulationLoading(false);
                setSimulationResult(data);
                showToast("Simulation generated successfully!", "fa-circle-check");
            })
            .catch(err => {
                console.error(err);
                setSimulationLoading(false);
                alert("Wahala dey! Simulation failed.");
            });
    };

    const sendChatMessage = () => {
        const query = chatInput.trim();
        if (!query) return;

        if (!selectedUser) {
            alert("Select a user from the sidebar to represent conversation context!");
            return;
        }

        // Append user bubble
        setChatMessages(prev => [...prev, { role: 'user', content: query }]);
        setChatLoading(true);
        setChatInput('');

        fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: selectedUser.user_id,
                message: query,
                chat_history: chatHistory
            })
        })
            .then(async res => {
                if (!res.ok) {
                    const errBody = await res.json().catch(() => ({}));
                    throw new Error(errBody.detail || `Server error ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                setChatLoading(false);

                // Append assistant bubble
                setChatMessages(prev => [
                    ...prev,
                    {
                        role: 'assistant',
                        content: data.response,
                        reasoning: data.reasoning,
                        items: data.recommended_items
                    }
                ]);

                // Update dynamic memory
                if (data.user_memory) {
                    setEvolvingMemory(data.user_memory);
                }

                // Update charts/graph seeds
                if (data.recommended_items) {
                    setRecommendedItems(data.recommended_items);
                }

                // Record chat history
                setChatHistory(prev => [
                    ...prev,
                    { role: 'user', content: query },
                    { role: 'assistant', content: data.response }
                ]);
            })
            .catch(err => {
                console.error("Recommendation error:", err);
                setChatLoading(false);
                // Show error as an in-chat bubble instead of a disruptive alert
                setChatMessages(prev => [
                    ...prev,
                    {
                        role: 'assistant',
                        content: `⚠️ Wahala dey! The recommendation engine hit an error: *${err.message || 'Network failure'}*. Abeg try again or check the server logs.`
                    }
                ]);
            });
    };

    const handlePersonalizeAction = (productId, action, buttonEl) => {
        if (!selectedUser) return;

        // Toggle state
        const currentPreference = itemPreferences[productId];
        if (currentPreference === action) return; // already selected

        setItemPreferences(prev => ({
            ...prev,
            [productId]: action
        }));

        if (action === 'like') {
            showToast("Dynamic Learning: Positive preference locked in!", "fa-circle-check");
        } else {
            showToast("Dynamic Learning: Reranking weights adjusted!", "fa-triangle-exclamation");
        }

        fetch('/api/personalize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: selectedUser.user_id,
                product_id: productId,
                action: action
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === "success") {
                    setEvolvingMemory(data.user_memory);
                }
            })
            .catch(err => console.error("Personalization loop error:", err));
    };

    return (
        <div className="app-container">
            {/* SIDEBAR */}
            <Sidebar 
                users={users}
                selectedUser={selectedUser}
                onSelectUser={handleSelectUser}
                loading={rosterLoading}
            />

            {/* MAIN PANEL */}
            <div className="main-content">
                {/* HEADER NAV MENU */}
                <div className="nav-header">
                    <div className="tab-menu">
                        <button 
                            className={`tab-btn ${activeTab === 'simulator-tab' ? 'active' : ''}`}
                            onClick={() => setActiveTab('simulator-tab')}
                        >
                            <i className="fa-solid fa-user-gear"></i>
                            Task A: User Simulator
                        </button>
                        <button 
                            className={`tab-btn ${activeTab === 'recommendation-tab' ? 'active' : ''}`}
                            onClick={() => setActiveTab('recommendation-tab')}
                        >
                            <i className="fa-solid fa-wand-magic-sparkles"></i>
                            Task B: Advanced Recommender
                        </button>
                        <button 
                            className={`tab-btn ${activeTab === 'science-tab' ? 'active' : ''}`}
                            onClick={() => setActiveTab('science-tab')}
                        >
                            <i className="fa-solid fa-flask"></i>
                            Scientific Evaluation
                        </button>
                    </div>

                    <div className="flavor-badge">
                        <i className="fa-solid fa-circle-check"></i>
                        Nigerian Cultural Layer Enabled
                    </div>
                </div>

                {/* WORKSPACE PANEL */}
                <div className="workspace-panel">
                    {activeTab === 'simulator-tab' && (
                        <SimulatorTab 
                            selectedUser={selectedUser}
                            selectedProduct={selectedProduct}
                            setSelectedProduct={setSelectedProduct}
                            nigerianFlavor={nigerianFlavor}
                            setNigerianFlavor={setNigerianFlavor}
                            simulationResult={simulationResult}
                            simulationLoading={simulationLoading}
                            onRunSimulation={runSimulation}
                        />
                    )}

                    {activeTab === 'recommendation-tab' && (
                        <RecommendationTab 
                            selectedUser={selectedUser}
                            chatMessages={chatMessages}
                            setChatMessages={setChatMessages}
                            chatInput={chatInput}
                            setChatInput={setChatInput}
                            onSendChatMessage={sendChatMessage}
                            chatLoading={chatLoading}
                            evolvingMemory={evolvingMemory}
                            recommendedItems={recommendedItems}
                            onPersonalizeAction={handlePersonalizeAction}
                        />
                    )}

                    {activeTab === 'science-tab' && (
                        <ScienceTab 
                            ablationData={ablationData}
                            humanEvalData={humanEvalData}
                        />
                    )}
                </div>
            </div>

            {/* TOAST ALERT NOTIFICATION CONTAINER */}
            <div className="toast-container">
                {toasts.map(toast => (
                    <div key={toast.id} className="toast">
                        <i className={`fa-solid ${toast.icon}`}></i>
                        <span>{toast.message}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
