export const privacyPolicy = {
  title: 'Privacy Policy | Nextora Lead Capture Machine',
  description: 'How Nextora Creations handles account, customer, Instagram and WhatsApp messaging data, authorized integrations, security, retention and deletion requests.',
  canonical: 'https://studio.nextoracreations.co.in/privacy-policy',
  updated: '2026-09-05',
  updatedLabel: 'September 5, 2026',
  // Official operator contact supplied by the project owner.
  contactEmail: 'support@nextoracreations.co.in',
};

export interface PrivacySection { id: string; title: string; paragraphs: string[]; bullets?: string[] }

export const privacySections: PrivacySection[] = [
  { id: 'introduction', title: 'Introduction', paragraphs: [
    'Nextora Lead Capture Machine (“Nextora”, “the platform”) is operated by Nextora Creations (“we”, “us”, “our”). We provide businesses with lead capture, customer relationship management (CRM), messaging, connected-channel integrations and business-configured automation services.',
    'This Privacy Policy explains how information is collected, processed, stored, used, shared and deleted when you visit or use the platform, connect an authorized account, or communicate with a business that uses Nextora.',
    'Businesses decide which channels to connect and how to use their customer information. We process that information to provide the service for the business. For our own account administration, billing, security and support, Nextora Creations determines the purposes of processing. A business’s own privacy notice may also apply to its customer interactions.',
  ]},
  { id: 'information-collected', title: 'Information we collect', paragraphs: [
    'The information processed depends on the features you use, the information you or your business provide, and the permissions you grant to connected services. We receive information directly from account holders and workspace members, from customers communicating with a connected business or submitting a form, and from authorized integration providers.',
  ], bullets: [
    'Account information: name, email address, authentication records, workspace membership, roles and account preferences. Nextora account passwords are handled through the platform’s password authentication system; they are separate from third-party account passwords.',
    'Business information: organization name, business contact details where supplied, team settings, services and other workspace configuration.',
    'Integration and application configuration: connected account identifiers, permitted basic profile information, authorization status, granted permissions, lead-trigger keywords, automation rules and notification preferences.',
    'Customer and CRM information: customer identifiers, names or usernames where available, contact details voluntarily supplied, leads, tags, priorities, service interests, bookings and interaction history.',
    'Conversation information: messages, supported attachments or media references, conversation participants, message identifiers, timestamps, delivery/read information and webhook events.',
    'Billing information: selected subscription, currency, amounts, payment-provider references, payment status and billing history. Payment checkout is handled by Razorpay; payment instruments are entered with the payment provider rather than in Nextora’s own CRM forms.',
    'Technical information: request and security logs, IP addresses and user-agent information where available, error records and operational events needed to protect, diagnose and run the service.',
  ]},
  { id: 'instagram', title: 'Meta and Instagram integration', paragraphs: [
    'A business may voluntarily connect an Instagram Professional account through Meta/Instagram’s official authorization flow. Nextora does not request or store your Instagram password. You authorize the connection with Meta/Instagram and may revoke it through the available account settings.',
    'Nextora processes the account and messaging information made available within the permissions the business grants. Our current requested Instagram permissions are:',
  ], bullets: [
    'instagram_business_basic — identifies and associates the authorized Instagram Professional account with the appropriate Nextora workspace and obtains basic account information needed for the integration, such as account identifiers and the account’s username.',
    'instagram_business_manage_messages — enables authorized businesses to receive, view, manage and respond to Instagram Direct conversations through Nextora’s inbox, subject to Meta’s applicable permissions and platform policies.',
    'Incoming Instagram messages may be evaluated against the business’s active lead-trigger rules. A matching conversation can be identified as a potential CRM lead. The business chooses these rules and remains responsible for its customer interactions and use of the results.',
  ]},
  { id: 'webhooks', title: 'Meta webhook data', paragraphs: [
    'Meta may deliver webhook events to Nextora when messaging or related integration events occur for an authorized account. These events may include account and customer identifiers, message content, message identifiers, timestamps and delivery or read information.',
    'We use webhook information as necessary to provide connected messaging, CRM, lead capture and automation features, route events to the correct workspace, prevent duplicate processing, diagnose delivery problems and maintain the integration. Webhook records can contain customer information and are handled as part of the service’s data.',
  ]},
  { id: 'access-tokens', title: 'Authorization and access tokens', paragraphs: [
    'Authorization tokens may be stored to maintain the integrations a business has authorized and perform permitted operations on its behalf. Integration credentials are encrypted in storage and access is restricted by the application’s authorization and workspace controls.',
    'Nextora does not expose a business’s access tokens to other customers. Tokens are used for authorized communication with the connected provider. Never include an Instagram password, access token or other secret in a support or privacy request.',
  ]},
  { id: 'messages-and-leads', title: 'Customer messages, leads and automations', paragraphs: [
    'Businesses may use Nextora to process customer identifiers, names or usernames when available, messages, conversation details, lead information, business-defined tags and priorities, service interests and lead-trigger results. This information enables the inbox, CRM, customer management, lead capture and automation features.',
    'Business-configured rules can evaluate incoming text or interaction events and perform configured actions, such as identifying a lead, applying a tag, changing a lead’s status or preparing/sending an allowed response. Businesses control their configuration and should review it for accuracy, appropriateness and compliance with applicable messaging rules.',
    'If you are a customer of a business using Nextora, contact that business about its own purposes for collecting your information or the decisions it makes about you. You may also contact Nextora Creations as described below for requests concerning our processing.',
  ]},
  { id: 'use-of-information', title: 'How we use information', paragraphs: [
    'We process information to operate the service and fulfil the purposes described in this policy. Where applicable law requires a legal basis, the basis depends on the processing: performing our agreement with account holders, legitimate operational and security interests where permitted, meeting legal obligations, or consent where required. Businesses are responsible for the appropriate basis and notices for customer information they process through Nextora.',
  ], bullets: [
    'Provide and administer Nextora, authenticate users and manage workspaces, team permissions and subscriptions.',
    'Connect authorized third-party accounts, display conversations and enable permitted message management and replies.',
    'Create and manage CRM leads, customer records and bookings, and run business-configured automations.',
    'Provide account and service communications, respond to requests and troubleshoot problems.',
    'Maintain security, prevent abuse and unauthorized access, and improve operational reliability.',
    'Meet applicable legal or compliance obligations, resolve disputes and enforce our service agreements.',
  ]},
  { id: 'sharing', title: 'How information is shared', paragraphs: [
    'Information in a workspace is available to its authorized members according to their access permissions. Actions taken by those members, such as replying to a customer, share the relevant information with the intended recipient through the connected channel.',
    'Third-party platforms receive information necessary to support an authorized integration or an action you request. Infrastructure and service providers may process information where necessary to host, operate, secure or support Nextora, including payment processing and delivery of service communications, subject to applicable access restrictions and safeguards.',
    'Information may also be disclosed where required by applicable law or a valid legal process, or where reasonably necessary to protect rights, safety and service security. If a business transfer affects the service, relevant information may be transferred subject to applicable privacy requirements.',
    'Nextora does not offer customer messages or CRM records for sale to advertising data brokers. This policy does not authorize an independent advertising use of connected messaging data.',
  ]},
  { id: 'security', title: 'Data security', paragraphs: [
    'We use reasonable technical and organizational measures designed to protect information. The application supports HTTPS in production, authenticated access, role-based authorization, workspace access controls, encrypted integration credentials and operational logging. Application secrets are kept in server-side configuration rather than published in public pages.',
    'Access is limited according to the needs of the service. Account holders should protect their login credentials, assign workspace access carefully and revoke access that is no longer needed. No system or method of transmission or storage can guarantee absolute security.',
  ]},
  { id: 'retention', title: 'Data retention', paragraphs: [
    'We retain information for as long as reasonably necessary to provide the service, maintain requested records and integrations, meet applicable obligations, resolve disputes, prevent abuse and maintain security. Relevant factors include whether the account or integration remains in use, the type and purpose of the record, a valid deletion request and any legal requirement to retain it.',
    'Disconnecting a channel prevents further authorized integration use but is not, by itself, a request to erase every previously received customer record. Use the deletion process below when you want associated information removed. Some information may need to remain for applicable legal, accounting, dispute or security purposes.',
  ]},
  { id: 'data-deletion', title: 'Data Deletion and User Requests', paragraphs: [
    'To request deletion of your Nextora account and associated data, contact Nextora Creations using the privacy contact in the Contact section below. Identify the account email and workspace or connected business concerned, and explain whether you want account deletion, connected-platform data deletion or removal of specified records. Do not send passwords, tokens or unnecessary message content.',
    'We may ask for information reasonably necessary to verify your identity and authority over the account or data. Where a business controls the relevant customer information, we may coordinate with that business or direct your request to it. Requests are handled subject to applicable law, identity verification and any permitted retention obligations. The time needed depends on the scope of the request and applicable requirements.',
    'Meta/Instagram users may revoke Nextora’s authorization through their Meta/Instagram account settings where available. Nextora handles provider deauthorization and data-deletion requests through its configured Meta integration endpoints. These provider callbacks do not require you to disclose access tokens to Nextora support. Revoking authorization and deleting previously stored data are distinct actions.',
  ]},
  { id: 'third-parties', title: 'Third-party services and processing locations', paragraphs: [
    'Nextora connects to third-party services such as Meta/Instagram and WhatsApp, and uses Razorpay for payment checkout. Their own terms, permissions and privacy policies may apply to their processing. Review those notices when authorizing an integration or making a payment.',
    'Our site loads its typeface through Google Fonts. Your browser may send technical information, such as its IP address and request headers, when requesting those font files. This supports the site’s appearance and is separate from your connected account or message data.',
    'Connected platforms and infrastructure providers may process information in locations outside your jurisdiction. The applicable requirements and safeguards depend on the services used and where processing occurs. Contact Nextora Creations for information relevant to your use of the service; this policy does not promise storage in a particular country.',
  ]},
  { id: 'session-technologies', title: 'Cookies and browser storage', paragraphs: [
    'The web application uses browser local storage to retain its Nextora authentication token and selected workspace so that signed-in functionality can operate. These values are used for account access and workspace selection; they are not your Instagram password. Signing out clears the application’s stored login and workspace selection.',
    'Django administrative or session-based functionality may use session and security cookies, including protection against cross-site request forgery. Connected providers’ authorization and payment pages may use their own cookies or similar technologies under their own policies.',
    'The privacy page is available without signing in and does not set advertising or analytics cookies. You can control browser storage and cookies through your browser settings, although restricting necessary storage can affect signed-in features.',
  ]},
  { id: 'children', title: 'Children', paragraphs: [
    'Nextora is a business SaaS platform intended for business account holders and their authorized users, not for use by children as account holders. Businesses must ensure they have appropriate authority and a lawful basis for any customer information they submit, including information relating to children. If you believe information has been provided improperly, contact us using the details below.',
  ]},
  { id: 'rights', title: 'Your privacy rights', paragraphs: [
    'Depending on your jurisdiction and the circumstances, you may have rights to request access to, correction or deletion of personal information; restrict or object to processing; receive certain information in a portable format; or withdraw consent or integration authorization where applicable. You may also have a right to complain to the relevant privacy authority.',
    'These rights are subject to applicable law and relevant exceptions. Withdrawing authorization does not automatically undo processing already performed lawfully. Account holders can update available profile and workspace settings, and can use the contact process below for other requests. Customers of a business using Nextora should generally contact that business first about the information it controls.',
  ]},
  { id: 'policy-changes', title: 'Changes to this Privacy Policy', paragraphs: [
    'We may update this Privacy Policy to reflect changes to the service, how information is processed or applicable requirements. The “Last Updated” date identifies the current version. Where required, we will provide additional notice of material changes. Review this page periodically for the current policy.',
  ]},
];
