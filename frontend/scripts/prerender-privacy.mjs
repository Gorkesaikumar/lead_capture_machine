// Generate crawler-readable legal HTML from the same React component used by the app.
import { createServer } from 'vite';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
try {
  const { renderPrivacyPolicy, privacyPolicy } = await server.ssrLoadModule('/src/features/legal/privacy-render.tsx');
  let html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
  const escape = value => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  html = html.replace(/<title>.*?<\/title>/s, `<title>${escape(privacyPolicy.title)}</title>`)
    .replace(/<meta name="description" content="[^"]*"\s*\/?>/, `<meta name="description" content="${escape(privacyPolicy.description)}" />`)
    .replace('</head>', `<link rel="canonical" href="${privacyPolicy.canonical}" />\n<meta name="robots" content="index,follow" />\n<meta property="og:title" content="${escape(privacyPolicy.title)}" />\n<meta property="og:description" content="${escape(privacyPolicy.description)}" />\n<meta property="og:url" content="${privacyPolicy.canonical}" />\n<meta property="og:type" content="website" />\n</head>`)
    .replaceAll('<meta property="og:', '<meta data-privacy-policy property="og:')
    .replace('<div id="root"></div>', `<div id="root">${renderPrivacyPolicy()}</div>`);
  await mkdir(new URL('../dist/privacy-policy/', import.meta.url), { recursive: true });
  await writeFile(new URL('../dist/privacy-policy/index.html', import.meta.url), html);
  console.log('Pre-rendered /privacy-policy with full public content and metadata.');
} finally { await server.close(); }
