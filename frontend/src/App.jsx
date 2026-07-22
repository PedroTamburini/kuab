import { useState, useEffect, useRef } from 'react';
import { fetchModels, chatStream } from './services/api';
import './index.css';

function App() {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadModels = async () => {
    try {
      const data = await fetchModels();
      setModels(data);
      if (data.length > 0) {
        setSelectedModel(data[0].name);
      }
    } catch (err) {
      setError("Failed to load models. Is backend running?");
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !selectedModel || isLoading) return;

    const userMsg = { role: 'user', content: input.trim() };
    const newHistory = [...messages, userMsg];
    
    setMessages(newHistory);
    setInput('');
    setIsLoading(true);
    setError(null);

    let aiResponse = "";
    
    // Add placeholder for AI message
    setMessages([...newHistory, { role: 'assistant', content: '' }]);

    await chatStream(
      selectedModel,
      newHistory,
      (chunk) => {
        aiResponse += chunk;
        setMessages([...newHistory, { role: 'assistant', content: aiResponse }]);
      },
      (err) => {
        setError(err);
        setIsLoading(false);
      },
      () => {
        setIsLoading(false);
      }
    );
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Kuab</h1>
        <div className="model-selector">
          <label htmlFor="model">Model: </label>
          <select 
            id="model" 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={models.length === 0}
          >
            {models.length === 0 ? (
              <option value="">No models available</option>
            ) : (
              models.map(m => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))
            )}
          </select>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main className="chat-container">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Welcome to Kuab! Select a model and start chatting.</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              <div className="message-content">
                {msg.content}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <footer className="input-area">
        <form onSubmit={handleSend}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading || !selectedModel}
          />
          <button type="submit" disabled={isLoading || !selectedModel || !input.trim()}>
            {isLoading ? '...' : 'Send'}
          </button>
        </form>
      </footer>
    </div>
  );
}

export default App;
