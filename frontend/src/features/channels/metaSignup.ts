type SignupConfig = { app_id: string; config_id: string; graph_version: string; state: string };
type SignupResult = { code: string; waba_id: string; phone_number_id: string };
type FacebookSDK = {
  init: (options: Record<string, unknown>) => void;
  login: (callback: (response: { authResponse?: { code?: string } }) => void, options: Record<string, unknown>) => void;
};
declare global { interface Window { FB?: FacebookSDK } }
let sdkLoading: Promise<void> | undefined;

export async function prepareMetaSignup(config: SignupConfig) {
  if (!window.FB) {
    sdkLoading ||= new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      const timer = window.setTimeout(() => { script.remove(); sdkLoading = undefined; reject(new Error('Meta login could not load. Check your connection and allow the Meta login popup.')); }, 15000);
      script.src = 'https://connect.facebook.net/en_US/sdk.js';
      script.async = true;
      script.onload = () => { clearTimeout(timer); resolve(); };
      script.onerror = () => { clearTimeout(timer); script.remove(); sdkLoading = undefined; reject(new Error('Meta login could not load. Please try again.')); };
      document.head.appendChild(script);
    });
    await sdkLoading;
  }
  if (!window.FB) throw new Error('Meta login is unavailable. Reload and try again.');
  window.FB.init({ appId: config.app_id, version: config.graph_version, cookie: true, xfbml: false });
}

// Call directly from a user click, with SDK/config already loaded, to permit the popup.
export function launchMetaSignup(config: SignupConfig, signal: AbortSignal): Promise<SignupResult> {
  return new Promise((resolve, reject) => {
    let code = '', waba = '', phone = '', settled = false;
    const cleanup = () => { clearTimeout(timer); window.removeEventListener('message', receive); signal.removeEventListener('abort', abort); };
    const fail = (message: string) => { if (settled) return; settled = true; cleanup(); reject(new Error(message)); };
    const finish = () => { if (!settled && code && waba && phone) { settled = true; cleanup(); resolve({ code, waba_id: waba, phone_number_id: phone }); } };
    const abort = () => fail('WhatsApp connection was cancelled.');
    const receive = (event: MessageEvent) => {
      if (!['https://www.facebook.com', 'https://web.facebook.com'].includes(event.origin) || !event.source) return;
      let payload;
      try { payload = typeof event.data === 'string' ? JSON.parse(event.data) : event.data; } catch { return; }
      if (payload?.type !== 'WA_EMBEDDED_SIGNUP') return;
      if (payload.event === 'CANCEL') return fail('WhatsApp connection was cancelled.');
      if (payload.event === 'ERROR') return fail('Meta could not finish WhatsApp onboarding. Please try again.');
      if (payload.event === 'FINISH') {
        const data = payload.data;
        if (!/^\d{1,32}$/.test(String(data?.waba_id || '')) || !/^\d{1,32}$/.test(String(data?.phone_number_id || ''))) {
          return fail('Complete WhatsApp onboarding with a business account and phone number.');
        }
        waba = String(data.waba_id); phone = String(data.phone_number_id); finish();
      }
      if (['FINISH_ONLY_WABA', 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING'].includes(payload.event)) {
        fail('This connection requires standard WhatsApp Cloud API onboarding with a phone number. Ask your administrator to check the Meta signup configuration.');
      }
    };
    const timer = window.setTimeout(() => fail('WhatsApp connection timed out. Start again from Channels.'), 9 * 60 * 1000);
    window.addEventListener('message', receive);
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) return abort();
    try {
      if (!window.FB) return fail('Meta login is unavailable. Reload and try again.');
      window.FB.login(response => {
        if (!response.authResponse?.code) return fail('WhatsApp connection was cancelled.');
        code = response.authResponse.code; finish();
      }, { config_id: config.config_id, response_type: 'code', override_default_response_type: true,
           auth_type: 'rerequest', extras: { setup: {} } });
    } catch { fail('Meta login could not open. Allow popups and try again.'); }
  });
}

export type { SignupConfig };
