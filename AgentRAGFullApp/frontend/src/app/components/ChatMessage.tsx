import { User, Copy, ThumbsUp, ThumbsDown, RotateCcw, Circle, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { motion } from 'motion/react';
import { useState } from 'react';
import type { Message } from '../App';

interface ChatMessageProps {
  message: Message;
  onOpenActivity?: (messageId: string) => void;
}

export default function ChatMessage({ message, onOpenActivity }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const { role, content, thinkingSteps, thinkingDuration, vigencia } = message;

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = role === 'user';
  const hasActivity = !isUser && thinkingSteps && thinkingSteps.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="group py-3 sm:py-4 border-b border-border/20 last:border-0"
    >
      <div className="flex gap-2 sm:gap-3 items-start">
        {/* Avatar */}
        <div className={`flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 rounded-full flex items-center justify-center mt-0.5
          ${isUser ? 'bg-muted text-foreground' : 'bg-foreground text-background'}`}>
          {isUser
            ? <User className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
            : <Circle className="w-3 h-3 sm:w-3.5 sm:h-3.5 fill-current" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* "Pensó durante Xs" — clickable link to activity panel */}
          {hasActivity && thinkingDuration !== undefined && (
            <button
              onClick={() => onOpenActivity?.(message.id)}
              className="flex items-center gap-1.5 text-[11px] sm:text-xs text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted/50 px-1.5 py-0.5 -ml-1.5"
            >
              <Clock className="w-3 h-3" />
              <span>Penso durante {thinkingDuration}s</span>
              <span className="text-[10px]">&rsaquo;</span>
            </button>
          )}

          {/* Vigencia badges inline */}
          {vigencia && vigencia.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {vigencia.map((v, i) => (
                <span key={i} className={`inline-flex items-center gap-1 text-[10px] sm:text-[11px] font-medium px-1.5 py-0.5 rounded
                  ${v.estado === 'VIGENTE' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' :
                    v.estado === 'DEROGADA' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                    'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'}`}>
                  {v.estado === 'VIGENTE' ? '✅' : v.estado === 'DEROGADA' ? '❌' : '⚠️'}
                  {v.tipo} {v.numero}/{v.anio}
                </span>
              ))}
            </div>
          )}

          {/* Message text — clean prose rendering */}
          {content && (
            <div className="text-[13px] sm:text-sm text-foreground/90 leading-relaxed space-y-3">
              {content.split(/\n/).map((line, i) => {
                const trimmed = line.trim();
                if (!trimmed || trimmed === '---') return null;

                // Clean emojis
                const clean = trimmed.replace(/📌|⚖️|🔍|📋|⚠️|📘/g, '').trim();
                if (!clean) return null;

                // ### Header or ## Header -> bold subtitle with line
                if (/^#{1,3}\s/.test(clean)) {
                  const title = clean.replace(/^#{1,3}\s*/, '').replace(/\*\*/g, '');
                  return (
                    <div key={i} className="mt-4 mb-1 first:mt-0">
                      <div className="border-t border-border/30 pt-3" />
                      <h3 className="text-sm sm:text-base font-semibold text-foreground">{title}</h3>
                    </div>
                  );
                }

                // **Bold line** -> subtitle
                const boldMatch = clean.match(/^\*\*(.+?)\*\*$/);
                if (boldMatch) {
                  return (
                    <h4 key={i} className="text-[13px] sm:text-sm font-semibold text-foreground mt-4 mb-0.5">
                      {boldMatch[1]}
                    </h4>
                  );
                }

                // Numbered item: 1. xxx
                const numMatch = clean.match(/^(\d+)\.\s+(.+)/);
                if (numMatch) {
                  return (
                    <div key={i} className="flex gap-2 ml-1">
                      <span className="text-muted-foreground font-medium flex-shrink-0 w-5 text-right">{numMatch[1]}.</span>
                      <span className="break-words">{numMatch[2].replace(/\*\*(.*?)\*\*/g, '$1')}</span>
                    </div>
                  );
                }

                // Regular paragraph — strip remaining markdown
                const text = clean.replace(/\*\*(.*?)\*\*/g, '$1').replace(/^#{1,3}\s*/, '');
                return <p key={i} className="break-words">{text}</p>;
              })}
            </div>
          )}

          {/* Actions */}
          {!isUser && content && (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button variant="ghost" size="icon" onClick={handleCopy} className="h-6 w-6 rounded-md" title={copied ? 'Copiado!' : 'Copiar'}>
                <Copy className="w-3 h-3" />
              </Button>
              <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md"><ThumbsUp className="w-3 h-3" /></Button>
              <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md"><ThumbsDown className="w-3 h-3" /></Button>
              <Button variant="ghost" size="icon" className="h-6 w-6 rounded-md"><RotateCcw className="w-3 h-3" /></Button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// Keep named export for backward compat
export { ChatMessage };
