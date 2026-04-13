import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { ChatArea } from './components/ChatArea';
import { MessageInput } from './components/MessageInput';
import { SettingsPanel } from './components/SettingsPanel';
import { Toaster } from './components/ui/sonner';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export default function App() {
  const [darkMode, setDarkMode] = useState(false); // Light mode by default
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Apply dark mode
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const handleSendMessage = (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        '¡Excelente pregunta! Déjame ayudarte con eso. La inteligencia artificial es un campo fascinante que combina ciencias de la computación, matemáticas y filosofía para crear sistemas que pueden aprender y razonar.',
        'Entiendo perfectamente. Para resolver este problema, podemos abordar el análisis desde múltiples perspectivas. Primero, consideremos los datos disponibles y cómo podemos extraer insights valiosos.',
        'Esa es una consulta muy interesante. Basándome en mi conocimiento, puedo ofrecerte una explicación detallada y práctica que te ayudará a comprender mejor el concepto.',
        'Me parece genial que estés explorando este tema. Te propongo que trabajemos juntos paso a paso para encontrar la mejor solución posible a tu consulta.',
      ];

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const handleNewChat = () => {
    setMessages([]);
    toast.success('Nueva conversación iniciada');
  };

  const handleShare = () => {
    toast.success('Enlace copiado al portapapeles');
  };

  const handleSettings = () => {
    setIsSettingsOpen(true);
  };

  const handleStop = () => {
    setIsLoading(false);
    toast.info('Generación detenida');
  };

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      {/* Sidebar - toggleable */}
      {isSidebarOpen && (
        <Sidebar
          onNewChat={handleNewChat}
          darkMode={darkMode}
          onToggleDarkMode={toggleDarkMode}
          onClose={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Navbar */}
        <Navbar
          title={messages.length > 0 ? messages[0]?.content.slice(0, 50) + '...' : 'Nueva Conversación'}
          onShare={handleShare}
          onSettings={handleSettings}
          onToggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
        />

        {/* Chat Area */}
        <ChatArea messages={messages} isLoading={isLoading} />

        {/* Message Input */}
        <MessageInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          onStop={handleStop}
          isEmpty={messages.length === 0}
        />
      </div>

      {/* Settings Panel */}
      {isSettingsOpen && (
        <SettingsPanel
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          darkMode={darkMode}
          onToggleDarkMode={toggleDarkMode}
        />
      )}

      {/* Toast Notifications */}
      <Toaster position="top-center" />
    </div>
  );
}