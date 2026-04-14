import { motion } from 'motion/react';
import { X, Clock, Check, Download, Search, Scale, Brain, ExternalLink, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { useState } from 'react';
import type { ThinkingStep } from './AgentThinking';

export interface VigenciaItem {
  tipo: string;
  numero?: number;
  anio?: number;
  estado: string;
  titulo?: string;
  derogada_por?: string;
}

interface ActivityPanelProps {
  isOpen: boolean;
  onClose: () => void;
  steps: ThinkingStep[];
  duration?: number;
  vigencia?: VigenciaItem[];
  sources?: string[];
}

function getStepIcon(step: ThinkingStep) {
  if (step.type === 'ingest') return <Download className="w-3.5 h-3.5 text-blue-500" />;
  const t = step.text.toLowerCase();
  if (t.includes('busca') || t.includes('consult')) return <Search className="w-3.5 h-3.5 text-amber-500" />;
  if (t.includes('vigencia')) return <Scale className="w-3.5 h-3.5 text-purple-500" />;
  if (t.includes('genera')) return <Brain className="w-3.5 h-3.5 text-pink-500" />;
  return <Check className="w-3.5 h-3.5 text-green-500" />;
}

export default function ActivityPanel({ isOpen, onClose, steps, duration, vigencia, sources }: ActivityPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['steps', 'vigencia']));

  if (!isOpen) return null;

  const toggle = (key: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const ingestSteps = steps.filter(s => s.type === 'ingest');
  const statusSteps = steps.filter(s => s.type === 'status');

  return (
    <>
      {/* Backdrop mobile */}
      <div className="fixed inset-0 bg-black/20 z-40 md:hidden" onClick={onClose} />

      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        className="fixed right-0 top-0 h-full w-full max-w-sm bg-background border-l border-border z-50 flex flex-col shadow-xl
                   md:w-80 md:max-w-none"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-semibold">Actividad</span>
            {duration !== undefined && (
              <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{duration}s</span>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0">
            <X className="w-4 h-4" />
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-4 space-y-4">

            {/* Thinking Steps */}
            <div>
              <button onClick={() => toggle('steps')} className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 hover:text-foreground transition-colors">
                {expandedSections.has('steps') ? <ChevronDown className="w-3 h-3"/> : <ChevronRight className="w-3 h-3"/>}
                Pensamiento ({statusSteps.length} pasos)
              </button>
              {expandedSections.has('steps') && (
                <div className="space-y-1 ml-1">
                  {statusSteps.map((step) => (
                    <div key={step.id} className="flex items-start gap-2 py-1">
                      <div className="mt-0.5 flex-shrink-0">{getStepIcon(step)}</div>
                      <span className="text-xs text-foreground/80 leading-relaxed">{step.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Downloads */}
            {ingestSteps.length > 0 && (
              <div>
                <button onClick={() => toggle('ingest')} className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 hover:text-foreground transition-colors">
                  {expandedSections.has('ingest') ? <ChevronDown className="w-3 h-3"/> : <ChevronRight className="w-3 h-3"/>}
                  Normativa descargada ({ingestSteps.length})
                </button>
                {expandedSections.has('ingest') && (
                  <div className="space-y-1 ml-1">
                    {ingestSteps.map((step) => (
                      <div key={step.id} className="flex items-center gap-2 py-1">
                        <Download className="w-3 h-3 text-blue-500 flex-shrink-0" />
                        <span className="text-xs text-blue-600 dark:text-blue-400">{step.text}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Vigencia */}
            {vigencia && vigencia.length > 0 && (
              <div>
                <button onClick={() => toggle('vigencia')} className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 hover:text-foreground transition-colors">
                  {expandedSections.has('vigencia') ? <ChevronDown className="w-3 h-3"/> : <ChevronRight className="w-3 h-3"/>}
                  Vigencia verificada ({vigencia.length})
                </button>
                {expandedSections.has('vigencia') && (
                  <div className="space-y-1.5 ml-1">
                    {vigencia.map((v, i) => (
                      <div key={i} className={`flex items-start gap-2 py-1 px-2 rounded text-xs ${
                        v.estado === 'VIGENTE' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400' :
                        v.estado === 'DEROGADA' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400' :
                        'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400'
                      }`}>
                        <span className="flex-shrink-0 mt-0.5">
                          {v.estado === 'VIGENTE' ? '✅' : v.estado === 'DEROGADA' ? '❌' : '⚠️'}
                        </span>
                        <div className="min-w-0">
                          <div className="font-medium">{v.tipo} {v.numero} de {v.anio}</div>
                          {v.estado === 'DEROGADA' && v.derogada_por && (
                            <div className="text-[10px] opacity-80">Derogada por {v.derogada_por}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Sources */}
            {sources && sources.length > 0 && (
              <div>
                <button onClick={() => toggle('sources')} className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 hover:text-foreground transition-colors">
                  {expandedSections.has('sources') ? <ChevronDown className="w-3 h-3"/> : <ChevronRight className="w-3 h-3"/>}
                  Fuentes consultadas ({sources.length})
                </button>
                {expandedSections.has('sources') && (
                  <div className="space-y-1 ml-1">
                    {sources.map((s, i) => (
                      <div key={i} className="flex items-center gap-2 py-0.5">
                        <ExternalLink className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                        <span className="text-xs text-foreground/70 truncate">{s}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Download sources */}
            {sources && sources.length > 0 && (
              <div>
                <button onClick={() => toggle('download')} className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 hover:text-foreground transition-colors">
                  {expandedSections.has('download') ? <ChevronDown className="w-3 h-3"/> : <ChevronRight className="w-3 h-3"/>}
                  Descargar documentos
                </button>
                {expandedSections.has('download') && (
                  <div className="space-y-1.5 ml-1">
                    <p className="text-[10px] text-muted-foreground mb-2">
                      Descargue los documentos usados para validacion manual:
                    </p>
                    {sources.filter(s => !s.includes('datos_gov')).map((s, i) => {
                      // Build download URL based on source name
                      const isFromFP = s.includes('funcion_publica') || s.includes('Ministerio');
                      const isFromSenado = s.includes('Codigo') || s.includes('Ley_');
                      const downloadUrl = isFromFP
                        ? `https://www.funcionpublica.gov.co/eva/gestornormativo/`
                        : isFromSenado
                          ? `http://www.secretariasenado.gov.co/senado/basedoc/`
                          : '#';
                      return (
                        <a
                          key={i}
                          href={downloadUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 py-1 px-2 rounded text-xs bg-muted/50 hover:bg-muted transition-colors"
                        >
                          <Download className="w-3 h-3 text-blue-500 flex-shrink-0" />
                          <span className="truncate text-foreground/70">{s}</span>
                          <ExternalLink className="w-2.5 h-2.5 text-muted-foreground ml-auto flex-shrink-0" />
                        </a>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Duration */}
            {duration !== undefined && (
              <div className="pt-2 border-t border-border">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Penso durante {duration}s</span>
                  <span className="text-green-500 ml-auto">Listo</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </motion.div>
    </>
  );
}
