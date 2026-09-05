import { useEffect } from 'react';
import Navbar from '../marketing/components/Navbar';
import Footer from '../marketing/components/Footer';
import { privacyPolicy, privacySections } from './privacy-content';
import './privacy.css';

export default function PrivacyPolicy() {
  useEffect(() => {
    const previousTitle = document.title === privacyPolicy.title
      ? 'Nextora Lead Capture Machine | Capture Leads From Instagram, WhatsApp & Website'
      : document.title;
    const description = document.querySelector('meta[name="description"]');
    const currentDescription = description?.getAttribute('content');
    const previousDescription = currentDescription === privacyPolicy.description
      ? 'Capture, organize and manage leads from Instagram, WhatsApp and your website in one powerful workspace.'
      : currentDescription;
    document.title = privacyPolicy.title;
    description?.setAttribute('content', privacyPolicy.description);
    const canonical = document.createElement('link');
    canonical.rel = 'canonical';
    canonical.href = privacyPolicy.canonical;
    const existingCanonical = document.querySelector('link[rel="canonical"]');
    if (!existingCanonical) document.head.appendChild(canonical);
    return () => {
      document.title = previousTitle;
      if (previousDescription) description?.setAttribute('content', previousDescription);
      canonical.remove();
      // Pre-rendered head tags also need removing on client-side navigation home.
      if (existingCanonical?.getAttribute('href') === privacyPolicy.canonical) existingCanonical.remove();
      document.querySelectorAll('[data-privacy-policy]').forEach(element => element.remove());
    };
  }, []);

  return (
    <div className="privacy-page min-h-screen bg-white text-slate-800">
      <a href="#policy-content" className="privacy-skip">Skip to privacy policy</a>
      <Navbar legal />
      <main id="policy-content" tabIndex={-1} className="mx-auto max-w-6xl px-6 pb-20 pt-12 sm:px-8 sm:pt-16">
        <header className="border-b border-slate-200 pb-10">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-primary">Nextora Creations · Legal</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">Privacy Policy</h1>
          <p className="mt-4 text-lg text-slate-600">Nextora Lead Capture Machine</p>
          <p className="mt-5 text-sm text-slate-500">Last Updated: <time dateTime={privacyPolicy.updated}>{privacyPolicy.updatedLabel}</time></p>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-700">How we handle information when businesses connect their channels, manage customer conversations and capture leads with Nextora.</p>
        </header>

        <div className="grid gap-12 pt-10 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-16">
          <aside>
            <nav aria-label="Table of contents" className="lg:sticky lg:top-8">
              <h2 className="mb-4 text-sm font-semibold text-slate-950">On this page</h2>
              <ol className="grid gap-x-6 gap-y-2 text-sm leading-6 sm:grid-cols-2 lg:grid-cols-1">
                {privacySections.map((section, index) => <li key={section.id}><a href={`#${section.id}`} className="text-slate-600 hover:text-primary"><span className="mr-2 text-xs tabular-nums text-slate-400">{String(index + 1).padStart(2, '0')}</span>{section.title}</a></li>)}
                <li><a href="#contact" className="text-slate-600 hover:text-primary"><span className="mr-2 text-xs tabular-nums text-slate-400">17</span>Contact</a></li>
              </ol>
            </nav>
          </aside>

          <article aria-label="Privacy policy" className="min-w-0 max-w-[72ch] space-y-10">
            {privacySections.map((section, index) => (
              <section key={section.id} id={section.id} aria-labelledby={`${section.id}-heading`} className="scroll-mt-8">
                <h2 id={`${section.id}-heading`} className="text-xl font-semibold leading-8 tracking-tight text-slate-950"><span className="mr-2 text-sm font-normal text-slate-400">{String(index + 1).padStart(2, '0')}</span>{section.title}</h2>
                <div className="mt-4 space-y-4 text-[15px] leading-7 text-slate-700">
                  {section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}
                  {section.bullets && <ul className="list-disc space-y-3 pl-5 marker:text-primary">{section.bullets.map(item => <li key={item}>{item}</li>)}</ul>}
                  {section.id === 'data-deletion' && <p><a className="font-medium text-primary underline underline-offset-4" href={`mailto:${privacyPolicy.contactEmail}?subject=Privacy%20and%20data%20deletion%20request`}>Send a privacy or deletion request</a></p>}
                </div>
              </section>
            ))}
            <section id="contact" aria-labelledby="contact-heading" className="scroll-mt-8 border-t border-slate-200 pt-8">
              <h2 id="contact-heading" className="text-xl font-semibold text-slate-950"><span className="mr-2 text-sm font-normal text-slate-400">17</span>Contact</h2>
              <p className="mt-4 text-[15px] leading-7 text-slate-700">For questions about this policy or requests relating to your account, personal information or connected-platform data, contact Nextora Creations:</p>
              <address className="mt-5 space-y-2 text-[15px] not-italic leading-7">
                <p className="font-semibold text-slate-950">Nextora Creations</p>
                <p>Operator of Nextora Lead Capture Machine</p>
                <a className="inline-block break-all font-medium text-primary underline underline-offset-4" href={`mailto:${privacyPolicy.contactEmail}`}>{privacyPolicy.contactEmail}</a>
              </address>
              <p className="mt-5 text-sm leading-6 text-slate-600">Please include enough information to identify your account or request. We will not ask you to provide your Instagram password or access tokens.</p>
            </section>
          </article>
        </div>
      </main>
      <Footer legal />
    </div>
  );
}
