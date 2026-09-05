import { renderToStaticMarkup } from 'react-dom/server';
import { StaticRouter } from 'react-router-dom';
import PrivacyPolicy from './PrivacyPolicy';
export { privacyPolicy } from './privacy-content';

export function renderPrivacyPolicy() {
  return renderToStaticMarkup(<StaticRouter location="/privacy-policy"><PrivacyPolicy /></StaticRouter>);
}
