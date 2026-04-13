import { User, Copy, ThumbsUp, ThumbsDown, RotateCcw, Circle } from 'lucide-react';
import { Button } from './ui/button';
import { motion } from 'motion/react';
import { useState } from 'react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="group py-5 border-b border-border/20 last:border-0"
    >
      <div className="flex gap-3 items-start">
        {/* Avatar */}
        <div
          className={`
            flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center
            ${isUser
              ? 'bg-muted text-foreground'
              : 'bg-foreground text-background'
            }
          `}
        >
          {isUser ? (
            <User className="w-3.5 h-3.5" />
          ) : (
            <Circle className="w-3.5 h-3.5 fill-current" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          <div className="prose prose-sm max-w-none">
            <p className="text-[13px] text-foreground/90 leading-relaxed whitespace-pre-wrap">
              {content}
            </p>
          </div>

          {/* Actions (only for assistant messages) */}
          {!isUser && (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCopy}
                className="h-6 w-6 rounded-md"
              >
                <Copy className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 rounded-md"
              >
                <ThumbsUp className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 rounded-md"
              >
                <ThumbsDown className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 rounded-md"
              >
                <RotateCcw className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}