import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-outline-variant/20 py-[80px] px-margin-mobile md:px-margin-desktop text-body-sm text-on-surface-variant" id="resources">
      <div className="max-w-8xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-xl mb-[60px]">

          {/* Brand */}
          <div className="col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2 mb-sm">
              <img src="/lead.png" alt="Nextora" className="h-10 w-auto object-contain shrink-0 drop-shadow-[0_1px_4px_rgba(123,47,255,0.25)]" />
            </div>
            <p className="text-on-surface-variant text-body-sm leading-relaxed mb-sm">
              The Lead Capture Machine.
            </p>
            <p className="text-on-surface-variant text-label-sm">
              © {new Date().getFullYear()} Nextora Lead Capture Machine. All rights reserved.
            </p>
          </div>

          {/* Product */}
          <div>
            <h4 className="font-semibold text-on-surface text-body-sm mb-sm">Product</h4>
            <ul className="space-y-sm">
              <li><a href="#features" className="hover:text-primary transition-colors focus:outline-none focus:text-primary">Features</a></li>
              <li><a href="#how-it-works" className="hover:text-primary transition-colors focus:outline-none focus:text-primary">How It Works</a></li>
              <li><a href="#pricing" className="hover:text-primary transition-colors focus:outline-none focus:text-primary">Pricing</a></li>
              <li><a href="#faq" className="hover:text-primary transition-colors focus:outline-none focus:text-primary">FAQ</a></li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-semibold text-on-surface text-body-sm mb-sm">Resources</h4>
            <ul className="space-y-sm">
              <li><Link to="#" className="hover:text-primary transition-colors">FAQ</Link></li>
              <li><Link to="#" className="hover:text-primary transition-colors">Documentation</Link></li>
              <li><Link to="#" className="hover:text-primary transition-colors">Support</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="font-semibold text-on-surface text-body-sm mb-sm">Company</h4>
            <ul className="space-y-sm">
              <li><Link to="#" className="hover:text-primary transition-colors">About</Link></li>
              <li><Link to="#" className="hover:text-primary transition-colors">Contact</Link></li>
              <li><Link to="/admin" className="hover:text-primary transition-colors">Admin</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-semibold text-on-surface text-body-sm mb-sm">Legal</h4>
            <ul className="space-y-sm">
              <li><Link to="#" className="hover:text-primary transition-colors">Privacy Policy</Link></li>
              <li><Link to="#" className="hover:text-primary transition-colors">Terms of Service</Link></li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}
