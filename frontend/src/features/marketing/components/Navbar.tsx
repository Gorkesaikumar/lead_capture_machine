import { Link } from 'react-router-dom';
import { useState } from 'react';
import { ArrowRight, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

const NAV_LINKS = [
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Features',     href: '#features' },
  { label: 'Pricing',      href: '#pricing' },
  { label: 'FAQ',          href: '#faq' },
  { label: 'Resources',    href: '#resources' },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-outline-variant/30 bg-surface/80 backdrop-blur-xl">
      <div className="mx-auto max-w-8xl px-margin-mobile md:px-margin-desktop flex h-20 items-center justify-between">

        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 group shrink-0">
          <img src="/lead.png" alt="Nextora" className="h-14 w-auto object-contain shrink-0 drop-shadow-[0_2px_8px_rgba(123,47,255,0.3)]" />
        </Link>

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-md text-body-md">
          {NAV_LINKS.map(l => (
            <a
              key={l.label}
              href={l.href}
              className="text-on-surface-variant hover:text-primary transition-colors duration-200 font-medium"
            >
              {l.label}
            </a>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-sm">
          <Link to="/login" className="text-body-sm font-semibold text-on-surface-variant hover:text-primary transition-colors">
            Login
          </Link>
          <Link to="/signup">
            <button className="flex items-center gap-2 bg-primary text-on-primary px-5 py-2.5 rounded-lg text-body-sm font-semibold hover:bg-primary-container transition-colors shadow-md">
              Get Started Free
              <ArrowRight className="h-4 w-4" />
            </button>
          </Link>
        </div>

        {/* Mobile hamburger */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <button className="md:hidden p-2 text-on-surface-variant hover:text-on-surface transition-colors" aria-label="Open menu">
              <Menu className="h-6 w-6" />
            </button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[280px] bg-white p-6 flex flex-col gap-8">
            <div className="flex flex-col gap-4 text-base font-medium text-on-surface-variant mt-8">
              {NAV_LINKS.map(l => (
                <a key={l.label} href={l.href} onClick={() => setMobileOpen(false)} className="hover:text-primary transition-colors">
                  {l.label}
                </a>
              ))}
            </div>
            <div className="flex flex-col gap-3 border-t border-outline-variant pt-6">
              <Link to="/login" onClick={() => setMobileOpen(false)}>
                <Button variant="outline" className="w-full border-outline-variant">Login</Button>
              </Link>
              <Link to="/signup" onClick={() => setMobileOpen(false)}>
                <button className="w-full bg-primary text-on-primary py-2.5 rounded-lg font-semibold hover:bg-primary-container transition-colors">
                  Get Started Free
                </button>
              </Link>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  );
}
