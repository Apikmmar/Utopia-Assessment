import { Link } from "react-router";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { usePrepareTimeout } from "../hooks/use-prepare-timeout";
import { safeWhatsappLink } from "../notifications";
import { useOpenNotification } from "../queries";
import type { OrderNotification } from "../schemas";

type WhatsappButtonProps = { notification: OrderNotification; className?: string; showLaterLink?: boolean };

// Sends one notification through WhatsApp; remounts per status so the preparing timeout restarts after a retry.
export function WhatsappButton(props: WhatsappButtonProps) {
  return <WhatsappButtonState key={`${props.notification.notificationId}:${props.notification.status}`} {...props} />;
}

// Shows "preparing" while queued, a WhatsApp link once ready that records the opening, and a later-send note when it fails or stalls.
function WhatsappButtonState({ notification, className, showLaterLink = true }: WhatsappButtonProps) {
  const open = useOpenNotification();
  const isQueued = notification.status === "queued";
  const stalled = usePrepareTimeout(isQueued);
  const link = safeWhatsappLink(notification);

  if (notification.status === "failed" || stalled) {
    return (
      <p role="status" className={cn("text-sm text-muted", className)}>
        The WhatsApp message could not be prepared yet.
        {showLaterLink ? (
          <>
            {" "}
            You can send it later from the{" "}
            <Link to="/notifications" className="font-medium text-foreground underline underline-offset-4">
              Notifications page
            </Link>
            .
          </>
        ) : null}
      </p>
    );
  }
  if (isQueued) {
    return (
      <button type="button" disabled aria-live="polite" className={cn(buttonVariants({ variant: "outline" }), className)}>
        Preparing WhatsApp message…
      </button>
    );
  }
  if (!notification.canSend || !link) return null;
  const label = notification.status === "opened" ? "Send again" : `Send WhatsApp to ${notification.recipientName}`;
  return (
    <a
      href={link}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => open.mutate(notification.notificationId)}
      className={cn(buttonVariants({ variant: notification.status === "opened" ? "outline" : "default" }), className)}
    >
      {label}
    </a>
  );
}
