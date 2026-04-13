import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { ChatArea } from './components/ChatArea';
import { MessageInput } from './components/MessageInput';
import { SettingsPanel } from './components/SettingsPanel';
import { KnowledgePanel } from './components/KnowledgePanel';
import { Toaster } from './components/ui/sonner';
import { toast } from 'sonner';
import {
  sendChatStream,
  resetSession,
  listSessions,
  getSessionMessages,
  deleteSession,
  type SessionItem,
} from '../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: string[];
}

function fmtTime(d: Date = new Date()): string {
  return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

export default function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [streamAbort, setStreamAbort] = useState<(() => void) | null>(null);

  // Apply dark mode
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions);
    } catch (e) {
      console.warn('Could not load sessions:', e);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: fmtTime(),
      };

      const assistantId = crypto.randomUUID();
      const placeholder: Message = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: fmtTime(),
      };

      setMessages((prev) => [...prev, userMessage, placeholder]);
      setIsLoading(true);

      let aborted = false;
      setStreamAbort(() => () => {
        aborted = true;
      });

      try {
        let acc = '';
        for await (const chunk of sendChatStream({
          message: content,
          session_id: sessionId,
          stream: true,
        })) {
          if (aborted) break;
          acc += chunk;
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: acc } : m))
          );
        }
        refreshSessions();
      } catch (err) {
        console.error('Chat error:', err);
        toast.error(`Error: ${(err as Error).message}`);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `⚠️ Error: ${(err as Error).message}` }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        setStreamAbort(null);
      }
    },
    [sessionId, refreshSessions]
  );

  const handleNewChat = useCallback(async () => {
    try {
      const result = await resetSession();
      setSessionId(result.new_session_id);
    } catch {
      setSessionId(null);
    }
    setMessages([]);
    toast.success('Nueva conversación iniciada');
  }, []);

  const handleSelectSession = useCallback(async (id: string) => {
    try {
      setIsLoading(true);
      const data = await getSessionMessages(id);
      setSessionId(id);
      setMessages(
        data.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp ? fmtTime(new Date(m.timestamp)) : fmtTime(),
          sources: m.sources,
        }))
      );
    } catch (e) {
      toast.error(`No se pudo cargar la sesión: ${(e as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleDeleteSession = useCallback(
    async (id: string) => {
      try {
        await deleteSession(id);
        toast.success('Conversación eliminada');
        if (id === sessionId) {
          setMessages([]);
          setSessionId(null);
        }
        refreshSessions();
      } catch (e) {
        toast.error(`Error al eliminar: ${(e as Error).message}`);
      }
    },
    [sessionId, refreshSessions]
  );

  const handleShare = () => {
    if (!sessionId) {
      toast.info('Inicia una conversación primero');
      return;
    }
    navigator.clipboard.writeText(`${window.location.origin}/?session=${sessionId}`);
    toast.success('Enlace copiado al portapapeles');
  };

  const handleStop = () => {
    if (streamAbort) streamAbort();
    setIsLoading(false);
    toast.info('Generación detenida');
  };

  const toggleDarkMode = () => setDarkMode((v) => !v);
  const toggleSidebar = () => setIsSidebarOpen((v) => !v);

  return (
    <div className="h-screen flex overflow-hidden bg-background">
      {isSidebarOpen && (
        <Sidebar
          onNewChat={handleNewChat}
          darkMode={darkMode}
          onToggleDarkMode={toggleDarkMode}
          onClose={() => setIsSidebarOpen(false)}
          sessions={sessions}
          activeSessionId={sessionId}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        />
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar
          title={
            messages.length > 0
              ? messages[0]?.content.slice(0, 50) + '...'
              : 'Nueva Conversación'
          }
          onShare={handleShare}
          onSettings={() => setIsSettingsOpen(true)}
          onToggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
          onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        />

        <ChatArea messages={messages} isLoading={isLoading} />

        <MessageInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          onStop={handleStop}
          isEmpty={messages.length === 0}
        />
      </div>

      {isSettingsOpen && (
        <SettingsPanel
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          darkMode={darkMode}
          onToggleDarkMode={toggleDarkMode}
        />
      )}

      {isKnowledgeOpen && (
        <KnowledgePanel
          isOpen={isKnowledgeOpen}
          onClose={() => setIsKnowledgeOpen(false)}
        />
      )}

      <Toaster position="top-center" />
    </div>
  );
}
