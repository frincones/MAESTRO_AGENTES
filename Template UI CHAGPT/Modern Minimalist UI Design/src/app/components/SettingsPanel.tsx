import { motion } from 'motion/react';
import { X, User, Bell, Palette, Shield, Zap, Globe } from 'lucide-react';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Separator } from './ui/separator';
import { ScrollArea } from './ui/scroll-area';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  darkMode?: boolean;
  onToggleDarkMode?: () => void;
}

export function SettingsPanel({ isOpen, onClose, darkMode, onToggleDarkMode }: SettingsPanelProps) {
  if (!isOpen) return null;

  const settings = [
    {
      category: 'Cuenta',
      icon: User,
      items: [
        { label: 'Perfil público', enabled: true },
        { label: 'Mostrar actividad', enabled: false },
        { label: 'Permitir indexación', enabled: true },
      ]
    },
    {
      category: 'Notificaciones',
      icon: Bell,
      items: [
        { label: 'Notificaciones push', enabled: true },
        { label: 'Notificaciones por email', enabled: false },
        { label: 'Sonidos', enabled: true },
      ]
    },
    {
      category: 'Interfaz',
      icon: Palette,
      items: [
        { label: 'Modo compacto', enabled: false },
        { label: 'Animaciones', enabled: true },
        { label: 'Barra lateral colapsable', enabled: true },
      ]
    },
    {
      category: 'Privacidad',
      icon: Shield,
      items: [
        { label: 'Análisis de uso', enabled: true },
        { label: 'Compartir datos', enabled: false },
        { label: 'Cookies necesarias', enabled: true },
      ]
    },
  ];

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
      />

      {/* Panel */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        className="fixed right-0 top-0 h-full w-96 bg-card border-l border-border shadow-2xl z-50"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">Configuración</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Personaliza tu experiencia
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="hover:bg-accent"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          </div>

          {/* Content */}
          <ScrollArea className="flex-1">
            <div className="p-6 space-y-8">
              {settings.map((section, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="space-y-4"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                      <section.icon className="w-4 h-4 text-primary" />
                    </div>
                    <h3 className="font-medium">{section.category}</h3>
                  </div>

                  <div className="space-y-3 ml-10">
                    {section.items.map((item, itemIndex) => (
                      <div
                        key={itemIndex}
                        className="flex items-center justify-between py-2"
                      >
                        <label className="text-sm text-foreground/90 cursor-pointer">
                          {item.label}
                        </label>
                        <Switch defaultChecked={item.enabled} />
                      </div>
                    ))}
                  </div>

                  {index < settings.length - 1 && (
                    <Separator className="mt-4" />
                  )}
                </motion.div>
              ))}

              {/* Quick Actions */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="space-y-4"
              >
                <h3 className="font-medium flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Zap className="w-4 h-4 text-primary" />
                  </div>
                  Acciones Rápidas
                </h3>

                <div className="space-y-2 ml-10">
                  <Button variant="outline" className="w-full justify-start">
                    <Globe className="w-4 h-4 mr-2" />
                    Cambiar idioma
                  </Button>
                  <Button variant="outline" className="w-full justify-start">
                    <Shield className="w-4 h-4 mr-2" />
                    Exportar datos
                  </Button>
                </div>
              </motion.div>
            </div>
          </ScrollArea>

          {/* Footer */}
          <div className="p-6 border-t border-border">
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={onClose}
              >
                Cancelar
              </Button>
              <Button
                className="flex-1 bg-gradient-to-r from-primary to-primary/90"
                onClick={onClose}
              >
                Guardar
              </Button>
            </div>
          </div>
        </div>
      </motion.div>
    </>
  );
}