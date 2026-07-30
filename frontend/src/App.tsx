import React, { useState, useRef, useEffect } from 'react';

type Message = {
  id: string;
  sender: 'user' | 'bot';
  text: string;
};

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'bot',
      text: 'Welkom! Ik ben de BERTje PII Redaction bot. Upload een bestand of typ een medische tekst om PII te verwijderen.'
    }
  ]);
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const addMessage = (sender: 'user' | 'bot', text: string) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), sender, text }]);
  };

  const handleSendText = async () => {
    if (!input.trim()) return;
    
    const userText = input;
    addMessage('user', userText);
    setInput('');
    setIsLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userText })
      });
      
      const data = await response.json();
      addMessage('bot', data.redacted_text || 'Er is een fout opgetreden.');
    } catch (err) {
      addMessage('bot', 'Netwerkfout bij het verbinden met de backend.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    addMessage('user', `Uploading file: ${file.name}...`);
    setIsLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      addMessage('bot', `File Processed: ${data.filename}\n\nResult:\n${data.redacted_content}`);
    } catch (err) {
      addMessage('bot', 'Fout bij het verwerken van het bestand. Wordt dit formaat ondersteund?');
    } finally {
      setIsLoading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  return (
    <div className="app-container" onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
      {isDragging && (
        <div className="drag-overlay">
          <p>Laat bestand hier los...</p>
        </div>
      )}
      
      <div className="header">
        <h1>BERTje PII Shield</h1>
        <div style={{ color: 'var(--accent)', fontSize: '0.875rem' }}>
          {isLoading ? 'Verwerken...' : 'Klaar'}
        </div>
      </div>
      
      <div className="chat-container">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-area">
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={onFileInputChange} 
          accept=".txt,.pdf,.png,.jpg,.jpeg,.csv,.json"
        />
        <button 
          className="file-upload-btn" 
          onClick={() => fileInputRef.current?.click()}
          title="Upload Bestand (PDF, TXT, IMG, CSV, JSON)"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
        </button>
        <input 
          type="text" 
          className="text-input" 
          placeholder="Typ medische tekst hier..." 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendText()}
          disabled={isLoading}
        />
        <button className="btn" onClick={handleSendText} disabled={isLoading}>
          Zend
        </button>
      </div>
    </div>
  );
}

export default App;
