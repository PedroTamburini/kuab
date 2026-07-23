import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { fetchModels, chatStream, transcribeAudio, transcribeYoutube } from './services/api';
import './index.css';
import KuabLogo from './assets/logo-kuab.svg';
import { SendHorizontal, Square, Mic, Hourglass, Plus, Video, Send } from 'lucide-react';

function App() {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

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

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setIsTranscribing(true);
        try {
          const transcribedText = await transcribeAudio(audioBlob);
          setInput((prev) => (prev ? prev + ' ' + transcribedText : transcribedText));
        } catch (err) {
          setError("Transcription failed.");
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      setError("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  const handleYoutubeTranscribe = async (e) => {
    e.preventDefault();
    if (!youtubeUrl.trim() || isLoading) return;

    setShowTools(false);
    setIsTranscribing(true);
    setError(null);
    
    try {
        const transcribedText = await transcribeYoutube(youtubeUrl);
        const summaryPrompt = `Por favor, explique e resuma a transcrição de vídeo a seguir.\n\nTranscrição Original:\n${transcribedText}`;
        
        const userMsg = { 
            role: 'user', 
            content: summaryPrompt,
            isAttachment: true,
            attachmentName: "transcricao_video.txt"
        };
        const newHistory = [...messages, userMsg];
        
        setMessages(newHistory);
        setYoutubeUrl('');
        setIsLoading(true);

        let aiResponse = "";
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
            setIsTranscribing(false);
          },
          () => {
            setIsLoading(false);
            setIsTranscribing(false);
          }
        );
    } catch (err) {
        setError("Failed to transcribe YouTube video.");
        setIsTranscribing(false);
    }
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
				<img className="logo" src={KuabLogo} alt="Kuab Logo" />
			</header>

			{error && <div className="error-banner">{error}</div>}

			<main className="chat-container">
				<div className="messages">
					{messages.length === 0 && (
						<div className="empty-state">
							<p className="text-large">
								Kuab-no mĩ nokoa roakaki! Westíchta awe kavẽatso
								ikĩ vana txitátso
							</p>
							<p className="text-small">
								Bem-vindo ao Kuab! Selecione um modelo e comece
								a conversar.
							</p>
						</div>
					)}
					{messages.map((msg, idx) => (
						<div
							key={idx}
							className={`message-wrapper ${msg.role}`}
						>
							<div className="message-content">{msg.content}</div>
						</div>
					))}
					<div ref={messagesEndRef} />
				</div>
			</main>
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
                {msg.isAttachment ? (
                  <div className="attachment-ui">
                    <span className="attachment-icon">📎</span>
                    <span className="attachment-name">{msg.attachmentName}</span>
                  </div>
                ) : (
                  msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </main>

			{showTools && (
				<div className="youtube-section">
					<form
						onSubmit={handleYoutubeTranscribe}
						className="youtube-form"
					>
						<input
							type="url"
							placeholder="Cole um link do YouTube aqui..."
							value={youtubeUrl}
							onChange={(e) => setYoutubeUrl(e.target.value)}
							disabled={isTranscribing || isLoading}
							required
						/>
						<button
							type="submit"
							disabled={isTranscribing || isLoading}
						>
							<SendHorizontal />
						</button>
					</form>
				</div>
			)}
			<footer className="input-footer">
				<div className="input-area">
					<div className="model-selector">
						<select
							id="model"
							value={selectedModel}
							onChange={(e) => setSelectedModel(e.target.value)}
							disabled={models.length === 0}
						>
							{models.length === 0 ? (
								<option value="">Selecione um modelo</option>
							) : (
								models.map((m) => (
									<option key={m.name} value={m.name}>
										{m.name}
									</option>
								))
							)}
						</select>
					</div>
					<form onSubmit={handleSend}>
						<button
							type="button"
							className="plus-button"
							onClick={() => setShowTools(!showTools)}
							disabled={isTranscribing || isLoading}
							title="Link do YouTube"
						>
							<div>
								<Video />
							</div>
						</button>
						<button
							type="button"
							className={`mic-button ${isRecording ? "recording" : ""}`}
							onClick={
								isRecording ? stopRecording : startRecording
							}
							disabled={isTranscribing || isLoading}
							title="Gravar Áudio"
						>
							{isTranscribing ? (
								<div>
									<Hourglass />
								</div>
							) : (
								<div>
									<Mic />
								</div>
							)}
						</button>
						<button
							type="submit"
							disabled={
								isLoading || !selectedModel || !input.trim()
							}
						>
							{isLoading ? (
								<div>
									<Square />
								</div>
							) : (
								<div>
									<SendHorizontal />
								</div>
							)}
						</button>
					</form>
				</div>
			</footer>
		</div>
  );
}

export default App;
