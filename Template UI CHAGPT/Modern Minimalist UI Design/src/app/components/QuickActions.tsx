import { motion } from 'motion/react';
import { 
  Code, 
  FileText, 
  Image as ImageIcon, 
  Calculator, 
  Languages,
  Lightbulb 
} from 'lucide-react';
import { Button } from './ui/button';

interface QuickAction {
  icon: React.ElementType;
  label: string;
  prompt: string;
  color: string;
}

interface QuickActionsProps {
  onSelectAction?: (prompt: string) => void;
}

export function QuickActions({ onSelectAction }: QuickActionsProps) {
  const actions: QuickAction[] = [
    { 
      icon: Code, 
      label: 'Código', 
      prompt: 'Ayúdame a escribir código',
      color: 'text-blue-500' 
    },
    { 
      icon: FileText, 
      label: 'Escritura', 
      prompt: 'Ayúdame a redactar un documento',
      color: 'text-purple-500' 
    },
    { 
      icon: ImageIcon, 
      label: 'Imágenes', 
      prompt: 'Genera una imagen para mí',
      color: 'text-pink-500' 
    },
    { 
      icon: Calculator, 
      label: 'Análisis', 
      prompt: 'Ayúdame a analizar datos',
      color: 'text-green-500' 
    },
    { 
      icon: Languages, 
      label: 'Traducir', 
      prompt: 'Traduce este texto',
      color: 'text-orange-500' 
    },
    { 
      icon: Lightbulb, 
      label: 'Ideas', 
      prompt: 'Dame ideas creativas sobre',
      color: 'text-yellow-500' 
    },
  ];

  return (
    <div className="p-4 border-t border-sidebar-border space-y-3">
      <h3 className="text-xs font-medium text-muted-foreground px-2">
        ACCIONES RÁPIDAS
      </h3>
      
      <div className="grid grid-cols-3 gap-2">
        {actions.map((action, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05, duration: 0.2 }}
          >
            <Button
              variant="ghost"
              onClick={() => onSelectAction?.(action.prompt)}
              className="w-full h-auto flex flex-col items-center gap-2 p-3 hover:bg-sidebar-accent transition-colors"
            >
              <div className={`w-8 h-8 rounded-lg bg-sidebar-accent/50 flex items-center justify-center`}>
                <action.icon className={`w-4 h-4 ${action.color}`} />
              </div>
              <span className="text-xs text-sidebar-foreground font-medium">
                {action.label}
              </span>
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
