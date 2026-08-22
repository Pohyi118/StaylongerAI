type WhatsAppOptions = {
  message: string;
  phone?: string | null;
};

function digitsOnly(value?: string | null): string {
  return (value ?? "").replace(/\D/g, "");
}

export function buildWhatsAppUrl({ message, phone }: WhatsAppOptions): string {
  const recipient = digitsOnly(phone);
  const chatPath = recipient ? `/${recipient}` : "/";
  return `https://wa.me${chatPath}?text=${encodeURIComponent(message.trim())}`;
}

export function openWhatsApp(options: WhatsAppOptions): void {
  const url = buildWhatsAppUrl(options);

  // Open the final WhatsApp URL during the original click event. Opening a
  // blank tab first and navigating it afterwards is commonly blocked by
  // embedded previews and popup protection, which made the quick actions look
  // unresponsive.
  const popup = window.open(url, "_blank");

  if (popup) {
    try {
      popup.opener = null;
    } catch {
      // A browser can prevent access to the new tab once it starts navigating.
      // The WhatsApp navigation itself has already been requested.
    }
    return;
  }

  // If a new tab is disallowed (for example inside an iframe preview), keep
  // the action useful by taking the current tab straight to WhatsApp.
  if (!navigator.userAgent.includes("jsdom")) {
    window.location.assign(url);
  }
}
