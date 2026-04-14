import { motion, AnimatePresence } from 'motion/react';
import { Loader2, Check, Download, Search, Scale, Brain, Clock } from 'lucide-react';

export interface ThinkingStep {
  id: string;
  text: string;
  status: 'active' | 'completed';
  type: 'status' | 'ingest';
  timestamp: number;
}

interface AgentThinkingProps {
  steps: ThinkingStep[];
  isThinking: boolean;
  duration?: number;
  onOpenActivity?: () => void;
}

function getStepIcon(step: ThinkingStep) {
  if (step.status === 'completed') return <Check className="w-3 h-3 text-green-500" />;
  if (step.type === 'ingest') return <Download className="w-3 h-3 text-blue-500 animate-bounce" />;
  const t = step.text.toLowerCase();
  if (t.includes('busca')) return <Search className="w-3 h-3 text-amber-500 animate-pulse" />;
  if (t.includes('vigencia')) return <Scale className="w-3 h-3 text-purple-500 animate-pulse" />;
  if (t.includes('genera')) return <Brain className="w-3 h-3 text-pink-500 animate-pulse" />;
  return <Loader2 className="w-3 h-3 text-muted-foreground animate-spin" />;
}

export default function AgentThinking({ steps, isThinking, duration, onOpenActivity }: AgentThinkingProps) {
  if (steps.length === 0 && !isThinking) return null;

  // Still loading but no steps yet — show minimal loader
  if (steps.length === 0 && isThinking) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="py-3 flex items-center gap-2"
      >
        <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
        <span className="text-xs text-muted-foreground">Analizando consulta...</span>
      </motion.div>
    );
  }

  // If done thinking, show collapsed summary
  if (!isThinking && duration !== undefined) {
    return (
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onClick={onOpenActivity}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors py-1 px-2 -ml-2 rounded-md hover:bg-muted/50"
      >
        <Clock className="w-3 h-3" />
        <span>Pensó durante {duration}s</span>
        <span className="text-[10px] ml-1">›</span>
      </motion.button>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="py-3 flex items-start gap-3"
    >
      {/* Avatar */}
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-foreground/10 flex items-center justify-center mt-0.5">
        <Brain className="w-3.5 h-3.5 text-foreground/60 animate-pulse" />
      </div>

      {/* Timeline */}
      <div className="flex-1 min-w-0 space-y-0.5">
        <AnimatePresence mode="popLayout">
          {steps.map((step) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -8, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              exit={{ opacity: 0.5 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-2 py-0.5"
            >
              <div className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                {getStepIcon(step)}
              </div>
              <span className={`text-xs truncate ${
                step.status === 'completed'
                  ? 'text-muted-foreground/60'
                  : step.type === 'ingest'
                    ? 'text-blue-600 dark:text-blue-400 font-medium'
                    : 'text-foreground/80'
              }`}>
                {step.type === 'ingest' ? `Descargando: ${step.text}` : step.text}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Active spinner for current step */}
        {isThinking && steps.length > 0 && steps[steps.length - 1].status === 'active' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.3, 0.7, 0.3] }}
            transition={{ repeat: Infinity, duration: 1.5 }}
            className="flex gap-1 pt-1 pl-6"
          >
            {[0, 1, 2].map((i) => (
              <div key={i} className="w-1 h-1 rounded-full bg-muted-foreground" />
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
