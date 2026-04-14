import { useState, useEffect, useCallback, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { ChatArea } from './components/ChatArea';
import { MessageInput } from './components/MessageInput';
import { SettingsPanel } from './components/SettingsPanel';
import { KnowledgePanel } from './components/KnowledgePanel';
import ActivityPanel from './components/ActivityPanel';
import SessionStats from './components/SessionStats';
import type { VigenciaItem, SourceRef } from './components/ActivityPanel';
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
  sourceRefs?: SourceRef[];
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
  const [caseState, setCaseState] = useState<Record<string, unknown> | null>(null);

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
        let sc = 0;
        const steps: ThinkingStep[] = [];
        const vig: VigenciaItem[] = [];
        const srcs: string[] = [];
        const refs: SourceRef[] = [];
        const juris: Record<string, unknown>[] = [];
        let dur: number | undefined;
        let buf = '';

        for await (const chunk of sendChatStream({
          message: content, session_id: sessionId, stream: true,
        })) {
          if (aborted) break;
          buf += chunk;

          // Split NDJSON lines
          const lines = buf.split('\n');
          buf = lines.pop() || '';

          for (const line of lines) {
            const t = line.trim();
            if (!t) continue;

            // Try JSON parse (NDJSON protocol)
            try {
              const evt = JSON.parse(t);
              switch (evt.type) {
                case 'status':
                  if (steps.length > 0) steps[steps.length - 1].status = 'completed';
                  steps.push({ id: `s-${sc++}`, text: evt.text, status: 'active', type: 'status', timestamp: Date.now() });
                  setThinkingSteps([...steps]);
                  break;
                case 'ingest':
                  steps.push({ id: `i-${sc++}`, text: evt.norm, status: 'completed', type: 'ingest', timestamp: Date.now() });
                  setThinkingSteps([...steps]);
                  break;
                case 'token':
                  acc += evt.text;
                  break;
                case 'vigencia':
                  vig.push(evt.data);
                  break;
                case 'jurisprudencia':
                  juris.push(evt.data);
                  break;
                case 'sources':
                  srcs.push(...evt.data);
                  break;
                case 'sourcerefs':
                  refs.push(...evt.data);
                  break;
                case 'casestate':
                  setCaseState(evt.data);
                  break;
                case 'done':
                  dur = evt.duration;
                  steps.forEach(s => s.status = 'completed');
                  setThinkingSteps([...steps]);
                  break;
              }
              continue;
            } catch {
              // Not JSON — treat as plain text (chitchat fallback)
              acc += t;
            }
          }

          // Update UI
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? {
              ...m, content: acc,
              thinkingSteps: [...steps],
              thinkingDuration: dur,
              vigencia: vig.length > 0 ? [...vig] : undefined,
              sources: srcs.length > 0 ? [...srcs] : undefined,
              sourceRefs: refs.length > 0 ? [...refs] : undefined,
            } : m
          ));
        }

        // Process remaining buffer
        if (buf.trim()) {
          try {
            const evt = JSON.parse(buf.trim());
            if (evt.type === 'token') acc += evt.text;
            else if (evt.type === 'done') dur = evt.duration;
          } catch {
            acc += buf.trim();
          }
        }

        // Final update
        steps.forEach(s => s.status = 'completed');
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? {
            ...m, content: acc.trim(),
            thinkingSteps: [...steps],
            thinkingDuration: dur,
            vigencia: vig.length > 0 ? [...vig] : undefined,
            sources: srcs.length > 0 ? [...srcs] : undefined,
            sourceRefs: refs.length > 0 ? [...refs] : undefined,
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
    <div className="h-screen flex overflow-hidden bg-background">
      {/* Sidebar — fixed overlay, never disrupts flex layout */}
      {isSidebarOpen && (
        <>
          <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setIsSidebarOpen(false)} />
          <div className="fixed left-0 top-0 h-full z-50">
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

      {/* Main area — always full width, never affected by sidebar */}
      <div className="flex-1 flex flex-col overflow-hidden w-full">
        <Navbar
          title={messages.length > 0 ? messages[0]?.content.slice(0, 50) + '...' : 'Nueva Conversacion'}
          onShare={handleShare}
          onSettings={() => setIsSettingsOpen(true)}
          onToggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
          onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        />

        <SessionStats caseState={caseState} />

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
          sessionId={sessionId}
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
        sourceRefs={activityMessage?.sourceRefs}
      />

      <Toaster position="top-center" />
    </div>
  );
}
