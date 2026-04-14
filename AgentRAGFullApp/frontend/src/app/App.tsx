import { useState, useEffect, useCallback, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { ChatArea } from './components/ChatArea';
import { MessageInput } from './components/MessageInput';
import { SettingsPanel } from './components/SettingsPanel';
import { KnowledgePanel } from './components/KnowledgePanel';
import ActivityPanel from './components/ActivityPanel';
import type { VigenciaItem } from './components/ActivityPanel';
import type { ThinkingStep } from './components/AgentThinking';
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

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: string[];
  thinkingSteps?: ThinkingStep[];
  thinkingDuration?: number;
  vigencia?: VigenciaItem[];
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isActivityOpen, setIsActivityOpen] = useState(false);
  const [activityMessageId, setActivityMessageId] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [streamAbort, setStreamAbort] = useState<(() => void) | null>(null);

  // Thinking state — live during streaming
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);

  // Responsive: open sidebar by default on desktop
  useEffect(() => {
    setIsSidebarOpen(window.innerWidth >= 768);
  }, []);

  useEffect(() => {
    if (darkMode) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }, [darkMode]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions);
    } catch (e) {
      console.warn('Could not load sessions:', e);
    }
  }, []);

  useEffect(() => { refreshSessions(); }, [refreshSessions]);

  // ─── Parse streaming protocol ───
  const handleSendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: crypto.randomUUID(), role: 'user', content, timestamp: fmtTime(),
      };
      const assistantId = crypto.randomUUID();
      const placeholder: Message = {
        id: assistantId, role: 'assistant', content: '', timestamp: fmtTime(),
        thinkingSteps: [], vigencia: [],
      };

      setMessages(prev => [...prev, userMessage, placeholder]);
      setIsLoading(true);
      setThinkingSteps([]);

      let aborted = false;
      setStreamAbort(() => () => { aborted = true; });

      // Close sidebar on mobile when sending
      if (window.innerWidth < 768) setIsSidebarOpen(false);

      try {
        let acc = '';
        let contentStarted = false;
        let stepCounter = 0;
        const collectedSteps: ThinkingStep[] = [];
        const collectedVigencia: VigenciaItem[] = [];
        const collectedSources: string[] = [];
        let duration: number | undefined;
        let buffer = '';

        for await (const rawChunk of sendChatStream({
          message: content, session_id: sessionId, stream: true,
        })) {
          if (aborted) break;

          // Buffer chunks — they may arrive split mid-line
          buffer += rawChunk;
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trimEnd();

            if (trimmed.startsWith('[STATUS] ')) {
              const text = trimmed.replace('[STATUS] ', '');
              // Mark previous active step as completed
              if (collectedSteps.length > 0) {
                collectedSteps[collectedSteps.length - 1].status = 'completed';
              }
              const step: ThinkingStep = {
                id: `s-${stepCounter++}`, text, status: 'active',
                type: 'status', timestamp: Date.now(),
              };
              collectedSteps.push(step);
              setThinkingSteps([...collectedSteps]);

            } else if (trimmed.startsWith('[INGEST] ')) {
              const normName = trimmed.replace('[INGEST] ', '');
              const step: ThinkingStep = {
                id: `i-${stepCounter++}`, text: normName, status: 'completed',
                type: 'ingest', timestamp: Date.now(),
              };
              collectedSteps.push(step);
              setThinkingSteps([...collectedSteps]);

            } else if (trimmed.startsWith('[CONTENT]')) {
              // First real content token — mark all steps completed
              contentStarted = true;
              collectedSteps.forEach(s => s.status = 'completed');
              setThinkingSteps([...collectedSteps]);
              const text = trimmed.replace('[CONTENT]', '');
              if (text) acc += text;

            } else if (trimmed.startsWith('[VIGENCIA] ')) {
              try {
                const json = trimmed.replace('[VIGENCIA] ', '');
                const v = JSON.parse(json) as VigenciaItem;
                collectedVigencia.push(v);
              } catch { /* ignore parse errors */ }

            } else if (trimmed.startsWith('[SOURCES] ')) {
              try {
                const json = trimmed.replace('[SOURCES] ', '');
                const arr = JSON.parse(json) as string[];
                collectedSources.push(...arr);
              } catch { /* ignore */ }

            } else if (trimmed.startsWith('[DURATION] ')) {
              duration = parseInt(trimmed.replace('[DURATION] ', ''), 10);

            } else if (contentStarted && trimmed) {
              // Regular LLM token
              acc += trimmed + '\n';
            }
          }

          // Update message content in real-time
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? {
              ...m, content: acc,
              thinkingSteps: [...collectedSteps],
              thinkingDuration: duration,
              vigencia: collectedVigencia.length > 0 ? [...collectedVigencia] : undefined,
              sources: collectedSources.length > 0 ? [...collectedSources] : undefined,
            } : m
          ));
        }

        // Process remaining buffer
        if (buffer.trim() && contentStarted) {
          acc += buffer;
        }

        // Final update
        collectedSteps.forEach(s => s.status = 'completed');
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? {
            ...m, content: acc.trim(),
            thinkingSteps: [...collectedSteps],
            thinkingDuration: duration,
            vigencia: collectedVigencia.length > 0 ? [...collectedVigencia] : undefined,
            sources: collectedSources.length > 0 ? [...collectedSources] : undefined,
          } : m
        ));
        setThinkingSteps([]);
        refreshSessions();

      } catch (err) {
        console.error('Chat error:', err);
        toast.error(`Error: ${(err as Error).message}`);
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, content: `Error: ${(err as Error).message}` } : m
        ));
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
    } catch { setSessionId(null); }
    setMessages([]);
    setThinkingSteps([]);
    toast.success('Nueva conversacion iniciada');
  }, []);

  const handleSelectSession = useCallback(async (id: string) => {
    try {
      setIsLoading(true);
      const data = await getSessionMessages(id);
      setSessionId(id);
      setMessages(data.messages.map(m => ({
        id: m.id, role: m.role, content: m.content,
        timestamp: m.timestamp ? fmtTime(new Date(m.timestamp)) : fmtTime(),
        sources: m.sources,
      })));
      if (window.innerWidth < 768) setIsSidebarOpen(false);
    } catch (e) {
      toast.error(`No se pudo cargar la sesion: ${(e as Error).message}`);
    } finally { setIsLoading(false); }
  }, []);

  const handleDeleteSession = useCallback(async (id: string) => {
    try {
      await deleteSession(id);
      toast.success('Conversacion eliminada');
      if (id === sessionId) { setMessages([]); setSessionId(null); }
      refreshSessions();
    } catch (e) { toast.error(`Error al eliminar: ${(e as Error).message}`); }
  }, [sessionId, refreshSessions]);

  const handleShare = () => {
    if (!sessionId) { toast.info('Inicia una conversacion primero'); return; }
    navigator.clipboard.writeText(`${window.location.origin}/?session=${sessionId}`);
    toast.success('Enlace copiado');
  };

  const handleStop = () => {
    if (streamAbort) streamAbort();
    setIsLoading(false);
    toast.info('Generacion detenida');
  };

  const handleOpenActivity = useCallback((messageId: string) => {
    setActivityMessageId(messageId);
    setIsActivityOpen(true);
  }, []);

  const toggleDarkMode = () => setDarkMode(v => !v);
  const toggleSidebar = () => setIsSidebarOpen(v => !v);

  // Get activity data for selected message
  const activityMessage = activityMessageId
    ? messages.find(m => m.id === activityMessageId) : null;

  return (
    <div className="h-screen h-dvh flex overflow-hidden bg-background">
      {/* Sidebar - overlay on mobile */}
      {isSidebarOpen && (
        <>
          <div className="fixed inset-0 bg-black/30 z-30 md:hidden" onClick={() => setIsSidebarOpen(false)} />
          <div className="fixed left-0 top-0 h-full z-40 md:relative md:z-auto">
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
          </div>
        </>
      )}

      {/* Main area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Navbar
          title={messages.length > 0 ? messages[0]?.content.slice(0, 50) + '...' : 'Nueva Conversacion'}
          onShare={handleShare}
          onSettings={() => setIsSettingsOpen(true)}
          onToggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
          onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        />

        <ChatArea
          messages={messages}
          isLoading={isLoading}
          thinkingSteps={thinkingSteps}
          onOpenActivity={handleOpenActivity}
        />

        <MessageInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          onStop={handleStop}
          isEmpty={messages.length === 0}
        />
      </div>

      {/* Panels */}
      {isSettingsOpen && (
        <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)}
                       darkMode={darkMode} onToggleDarkMode={toggleDarkMode} />
      )}
      {isKnowledgeOpen && (
        <KnowledgePanel isOpen={isKnowledgeOpen} onClose={() => setIsKnowledgeOpen(false)} />
      )}

      {/* Activity Panel - right sidebar */}
      <ActivityPanel
        isOpen={isActivityOpen}
        onClose={() => setIsActivityOpen(false)}
        steps={activityMessage?.thinkingSteps || []}
        duration={activityMessage?.thinkingDuration}
        vigencia={activityMessage?.vigencia}
        sources={activityMessage?.sources}
      />

      <Toaster position="top-center" />
    </div>
  );
}
