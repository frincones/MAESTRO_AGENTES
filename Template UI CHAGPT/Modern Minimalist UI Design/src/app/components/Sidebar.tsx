import { Search, Plus, X, MessageSquare, Clock, Archive, Moon, Sun } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { useState } from 'react';
import { motion } from 'motion/react';

interface ChatItem {
  id: string;
  title: string;
  timestamp: string;
  isPinned?: boolean;
}

interface SidebarProps {
  onNewChat?: () => void;
  darkMode?: boolean;
  onToggleDarkMode?: () => void;
  onClose?: () => void;
  showStats?: boolean;
}

export function Sidebar({ onNewChat, darkMode, onToggleDarkMode, onClose, showStats = false }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeChat, setActiveChat] = useState<string>('1');

  // Mock chat data
  const chatHistory: ChatItem[] = [
    { id: '1', title: 'Comparación de modelos IA', timestamp: 'Hoy', isPinned: true },
    { id: '2', title: 'Estrategia de producto', timestamp: 'Hoy', isPinned: true },
    { id: '3', title: 'Code review', timestamp: 'Ayer' },
    { id: '4', title: 'Analytics dashboard', timestamp: 'Ayer' },
    { id: '5', title: 'Investigación UX', timestamp: '3d' },
    { id: '6', title: 'Optimización database', timestamp: '3d' },
    { id: '7', title: 'Documentación API', timestamp: '1sem' },
  ];

  const filteredChats = chatHistory.filter(chat =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pinnedChats = filteredChats.filter(chat => chat.isPinned);
  const recentChats = filteredChats.filter(chat => !chat.isPinned);

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/20 z-40 md:hidden"
      />

      {/* Sidebar */}
      <motion.aside
        initial={{ x: -300 }}
        animate={{ x: 0 }}
        exit={{ x: -300 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed md:relative w-60 h-screen bg-sidebar border-r border-sidebar-border flex flex-col z-50"
      >
        {/* Header */}
        <div className="p-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={onToggleDarkMode}
              >
                {darkMode ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 md:hidden"
                onClick={onClose}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <Button
            onClick={onNewChat}
            className="w-full bg-foreground hover:bg-foreground/90 text-background text-xs h-8"
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Nueva conversación
          </Button>

          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Buscar..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 bg-sidebar-accent border-sidebar-border h-8 text-xs"
            />
          </div>
        </div>

        {/* Chat List */}
        <ScrollArea className="flex-1 px-2">
          <div className="space-y-4 py-2">
            {/* Pinned Chats */}
            {pinnedChats.length > 0 && (
              <div className="space-y-0.5">
                <h3 className="px-2 text-[10px] font-medium text-muted-foreground mb-1">
                  FIJADOS
                </h3>
                {pinnedChats.map((chat) => (
                  <ChatItemComponent
                    key={chat.id}
                    chat={chat}
                    isActive={activeChat === chat.id}
                    onClick={() => setActiveChat(chat.id)}
                  />
                ))}
              </div>
            )}

            {pinnedChats.length > 0 && recentChats.length > 0 && (
              <Separator className="bg-sidebar-border" />
            )}

            {/* Recent Chats */}
            {recentChats.length > 0 && (
              <div className="space-y-0.5">
                <h3 className="px-2 text-[10px] font-medium text-muted-foreground mb-1">
                  RECIENTES
                </h3>
                {recentChats.map((chat) => (
                  <ChatItemComponent
                    key={chat.id}
                    chat={chat}
                    isActive={activeChat === chat.id}
                    onClick={() => setActiveChat(chat.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="p-2 border-t border-sidebar-border">
          <Button
            variant="ghost"
            className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent h-8 text-xs"
          >
            <Archive className="w-3.5 h-3.5 mr-2" />
            Archivados
          </Button>
        </div>
      </motion.aside>
    </>
  );
}

interface ChatItemProps {
  chat: ChatItem;
  isActive: boolean;
  onClick: () => void;
}

function ChatItemComponent({ chat, isActive, onClick }: ChatItemProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      onClick={onClick}
      className={`
        w-full px-2 py-2 rounded-md text-left transition-all duration-200
        ${isActive
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
        }
      `}
    >
      <div className="flex items-start gap-2">
        <MessageSquare className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${isActive ? 'text-foreground' : 'text-muted-foreground'}`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-normal truncate">{chat.title}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />
            {chat.timestamp}
          </p>
        </div>
      </div>
    </motion.button>
  );
}