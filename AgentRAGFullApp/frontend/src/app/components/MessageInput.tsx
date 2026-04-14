import { ArrowUp, Square } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { motion } from 'motion/react';
import { useState, useRef, useEffect } from 'react';

interface MessageInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  onStop?: () => void;
  isEmpty?: boolean;
}

export function MessageInput({ onSend, isLoading, onStop, isEmpty }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [message]);

  const SendButton = (
    <Button
      onClick={isLoading ? onStop : handleSend}
      disabled={!isLoading && !message.trim()}
      size="icon"
      className="h-9 w-9 rounded-full flex-shrink-0 bg-foreground hover:bg-foreground/90 disabled:opacity-20"
    >
      {isLoading ? (
        <Square className="w-3.5 h-3.5 text-background fill-current" />
      ) : (
        <ArrowUp className="w-4 h-4 text-background" />
      )}
    </Button>
  );

  if (isEmpty) {
    return (
      <div className="flex-1 flex items-center justify-center px-3 sm:px-4 pb-10 sm:pb-20">
        <div className="w-full max-w-2xl">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-xl sm:text-3xl md:text-4xl font-normal text-center mb-4 sm:mb-8 text-foreground"
          >
            ¿En qué puedo ayudarte?
          </motion.h1>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="relative"
          >
            <div className="flex items-end gap-2 bg-background border border-border/60 rounded-3xl p-2 shadow-sm focus-within:shadow-md transition-all">
              <Textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Escribe un mensaje..."
                className="flex-1 min-h-[52px] max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 px-3 text-sm"
                rows={1}
                disabled={isLoading}
              />
              {SendButton}
            </div>
          </motion.div>

          <p className="text-[10px] text-muted-foreground text-center mt-4">
            Las respuestas se basan en tu base de conocimiento. Verifica información crítica.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-border/40 bg-background/95 backdrop-blur-sm safe-area-bottom">
      <div className="max-w-3xl mx-auto px-3 sm:px-4 py-2 sm:py-3">
        <div className="relative">
          <div className="flex items-end gap-2 bg-background border border-border/60 rounded-3xl p-2 focus-within:shadow-sm transition-all">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un mensaje..."
              className="flex-1 min-h-[40px] max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 px-2 text-sm"
              rows={1}
              disabled={isLoading}
            />
            {SendButton}
          </div>
        </div>

        <p className="text-[10px] text-muted-foreground text-center mt-2">
          Las respuestas se basan en tu base de conocimiento. Verifica información crítica.
        </p>
      </div>
    </div>
  );
}
