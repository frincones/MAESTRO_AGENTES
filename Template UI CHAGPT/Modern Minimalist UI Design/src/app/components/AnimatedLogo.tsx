import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';

interface AnimatedLogoProps {
  size?: 'sm' | 'md' | 'lg';
}

export function AnimatedLogo({ size = 'md' }: AnimatedLogoProps) {
  const sizes = {
    sm: { container: 'w-8 h-8', icon: 'w-4 h-4' },
    md: { container: 'w-16 h-16', icon: 'w-8 h-8' },
    lg: { container: 'w-24 h-24', icon: 'w-12 h-12' },
  };

  const currentSize = sizes[size];

  return (
    <motion.div
      className={`${currentSize.container} rounded-2xl bg-gradient-to-br from-primary to-primary/90 flex items-center justify-center shadow-2xl shadow-primary/30 relative overflow-hidden`}
      whileHover={{ scale: 1.05 }}
      transition={{ type: 'spring', stiffness: 400, damping: 10 }}
    >
      {/* Animated background gradient */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-br from-primary/50 to-transparent"
        animate={{
          rotate: [0, 360],
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'linear',
        }}
      />

      {/* Glow effect */}
      <motion.div
        className="absolute inset-0 bg-primary/20 blur-xl"
        animate={{
          opacity: [0.5, 1, 0.5],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* Icon */}
      <motion.div
        animate={{
          rotate: [0, 5, -5, 0],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="relative z-10"
      >
        <Sparkles className={`${currentSize.icon} text-primary-foreground`} />
      </motion.div>

      {/* Particles */}
      {[...Array(3)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-primary-foreground/50 rounded-full"
          animate={{
            y: [0, -30, 0],
            x: [(i - 1) * 15, (i - 1) * 25, (i - 1) * 15],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            delay: i * 0.8,
            ease: 'easeOut',
          }}
        />
      ))}
    </motion.div>
  );
}
