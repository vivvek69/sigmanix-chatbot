import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './ChatbotComponent.css';

const ChatbotComponent = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [menuOptions, setMenuOptions] = useState([]);
  const chatEndRef = useRef(null);

  const API_URL = process.env.REACT_APP_CHATBOT_URL || 'http://localhost:5001';

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    initializeChatbot();
  }, []);

  const initializeChatbot = async () => {
    try {
      setIsLoading(true);
      const response = await axios.post(`${API_URL}/chat`, { menu_selected: 'menu' });
      setMessages([{ type: 'bot', content: response.data.reply }]);
      if (response.data.options) setMenuOptions(response.data.options);
    } catch (error) {
      console.error('Error:', error);
      setMessages([{ type: 'bot', content: 'Error connecting to chatbot.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (message = null) => {
    const messageToSend = message || inputValue.trim();
    if (!messageToSend) return;

    setMessages(prev => [...prev, { type: 'user', content: messageToSend }]);
    setInputValue('');
    setMenuOptions([]);

    try {
      setIsLoading(true);
      const response = await axios.post(`${API_URL}/chat`, { message: messageToSend });
      setMessages(prev => [...prev, { type: 'bot', content: response.data.reply }]);
      if (response.data.options) setMenuOptions(response.data.options);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { type: 'bot', content: 'Error connecting.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMenuClick = async (menuValue) => {
    try {
      setIsLoading(true);
      setMenuOptions([]);
      const response = await axios.post(`${API_URL}/chat`, { menu_selected: menuValue });
      setMessages(prev => [...prev, { type: 'bot', content: response.data.reply }]);
      if (response.data.options) setMenuOptions(response.data.options);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { type: 'bot', content: 'Error.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h1>Sigmanix Tech Chatbot</h1>
      </div>
      <div className="chatbot-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.type}-message`}>
            <p>{msg.content}</p>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      {menuOptions.length > 0 && (
        <div className="menu-options">
          {menuOptions.map((option, index) => (
            <button key={index} className="menu-option-btn" onClick={() => handleMenuClick(option.value)} disabled={isLoading}>
              {option.label}
            </button>
          ))}
        </div>
      )}
      <div className="input-area">
        <input type="text" value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyPress={handleKeyPress} placeholder="Ask..." disabled={isLoading} className="message-input" />
        <button onClick={() => sendMessage()} disabled={isLoading || !inputValue.trim()} className="send-btn">
          {→}
        </button>
      </div>
    </div>
  );
};

export default ChatbotComponent;