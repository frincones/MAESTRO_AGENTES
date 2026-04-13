import { ScrollArea } from './ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { motion } from 'motion/react';
import { Circle } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface ChatAreaProps {
  messages: Message[];
  isLoading?: boolean;
}

export function ChatArea({ messages, isLoading }: ChatAreaProps) {
  // Empty state is now handled by MessageInput component
  if (messages.length === 0) {
    return null;
  }

  return (
    <ScrollArea className="flex-1">
      <div className="max-w-3xl mx-auto px-4 py-4">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            role={message.role}
            content={message.content}
            timestamp={message.timestamp}
          />
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="py-5 flex items-start gap-3"
          >
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-foreground flex items-center justify-center">
              <Circle className="w-3.5 h-3.5 text-background fill-current" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{
                      repeat: Infinity,
                      duration: 1.5,
                      delay: i * 0.2,
                    }}
                    className="w-1.5 h-1.5 rounded-full bg-muted-foreground"
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </ScrollArea>
  );
}