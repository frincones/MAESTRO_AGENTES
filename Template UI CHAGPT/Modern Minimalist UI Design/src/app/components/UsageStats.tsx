import { motion } from 'motion/react';
import { TrendingUp, Zap, MessageSquare } from 'lucide-react';

interface Stat {
  icon: React.ElementType;
  label: string;
  value: string;
  trend?: number;
}

export function UsageStats() {
  const stats: Stat[] = [
    { icon: MessageSquare, label: 'Conversaciones', value: '24', trend: 12 },
    { icon: Zap, label: 'Tokens usados', value: '15.2k', trend: 8 },
    { icon: TrendingUp, label: 'Esta semana', value: '+32%', trend: 32 },
  ];

  return (
    <div className="p-4 space-y-3">
      <h3 className="text-xs font-medium text-muted-foreground px-2">
        ESTADÍSTICAS
      </h3>
      
      <div className="space-y-2">
        {stats.map((stat, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
            className="bg-sidebar-accent/50 rounded-lg p-3 border border-sidebar-border/50"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                  <stat.icon className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-sm font-semibold text-sidebar-foreground">{stat.value}</p>
                </div>
              </div>
              
              {stat.trend && (
                <div className="flex items-center gap-1 text-xs text-green-500">
                  <TrendingUp className="w-3 h-3" />
                  {stat.trend}%
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
