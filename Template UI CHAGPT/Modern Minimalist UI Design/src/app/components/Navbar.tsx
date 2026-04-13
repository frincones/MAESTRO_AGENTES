import { Menu, User } from 'lucide-react';
import { Button } from './ui/button';
import { motion } from 'motion/react';

interface NavbarProps {
  title?: string;
  onShare?: () => void;
  onSettings?: () => void;
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export function Navbar({ onSettings, onToggleSidebar }: NavbarProps) {
  return (
    <motion.nav
      initial={{ y: -10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="h-12 border-b border-border/40 bg-background/95 backdrop-blur-sm sticky top-0 z-10"
    >
      <div className="h-full max-w-full mx-auto px-3 flex items-center justify-between">
        {/* Left Side - Menu */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="hover:bg-accent/50 rounded-lg h-8 w-8"
          >
            <Menu className="w-4 h-4" />
          </Button>
        </div>

        {/* Right Side - User */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={onSettings}
            className="hover:bg-accent/50 rounded-lg h-8 w-8"
          >
            <User className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </motion.nav>
  );
}