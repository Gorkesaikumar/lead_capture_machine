/**
 * Predefined message templates for the Instagram CRM composer.
 * Single source of truth — import this wherever templates are needed.
 */

export interface MessageTemplate {
  id: string;
  name: string;
  description: string;
  text: string;
}

export const MESSAGE_TEMPLATES: MessageTemplate[] = [
  {
    id: "baby_shoot",
    name: "Baby Shoot Inquiry",
    description: "For customers asking about baby photography",
    text: "Hi! 👋 Thanks for reaching out to us. We'd love to help you with your baby shoot. Please let us know your preferred date and we'll help you find the best available slot.",
  },
  {
    id: "wedding",
    name: "Wedding Inquiry",
    description: "For customers asking about wedding photography",
    text: "Hi! 👋 Thank you for contacting us about your wedding photography. We'd love to understand your requirements and help you choose the right package.",
  },
  {
    id: "general",
    name: "General Inquiry",
    description: "A general welcoming response",
    text: "Hi! 👋 Thanks for contacting us. We'd be happy to help. Please share a few details about what you're looking for.",
  },
  {
    id: "booking_followup",
    name: "Booking Follow-up",
    description: "Following up on a pending booking",
    text: "Hi! 👋 Just following up regarding your photography session. If you'd like to continue, we'd be happy to help you select a date and time that works for you.",
  },
  {
    id: "availability_check",
    name: "Check Availability",
    description: "Ask customer for preferred dates",
    text: "Hi! 👋 Thank you for your interest! To help you book the perfect session, could you please share a few preferred dates? We'll check our availability and get back to you promptly.",
  },
];

export const BOOKING_LINK_TEMPLATE = `Hi! 👋

Thank you for your interest. Here's your personalized booking link to select your preferred date and time:

{BOOKING_URL}

We look forward to seeing you! 📸`;
