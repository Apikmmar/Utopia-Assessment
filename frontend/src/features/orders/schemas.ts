import { z } from "zod";

export const serviceTypeSchema = z.object({
  serviceTypeId: z.string(),
  code: z.string(),
  name: z.string(),
});

export const serviceTypeListSchema = z.object({
  items: z.array(serviceTypeSchema),
});

export type ServiceType = z.infer<typeof serviceTypeSchema>;
export type ServiceTypeList = z.infer<typeof serviceTypeListSchema>;

export const notificationSchema = z.object({
  notificationId: z.string(),
  orderId: z.string(),
  orderNo: z.string(),
  notificationType: z.string(),
  channel: z.string(),
  recipientType: z.string(),
  recipientName: z.string(),
  recipientPhone: z.string(),
  message: z.string().nullable(),
  deepLink: z.string().nullable(),
  status: z.string(),
  readyAt: z.string().nullable(),
  openedAt: z.string().nullable(),
  openedBy: z.object({ userId: z.string(), name: z.string() }).nullable(),
  canSend: z.boolean(),
  createdAt: z.string(),
});

export const notificationListSchema = z.object({
  items: z.array(notificationSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
});

export const notificationEnvelopeSchema = z.object({ notification: notificationSchema });

export type OrderNotification = z.infer<typeof notificationSchema>;
export type NotificationList = z.infer<typeof notificationListSchema>;

export const CUSTOMER_NAME_MAX_LENGTH = 100;
export const ADDRESS_MAX_LENGTH = 500;
export const PROBLEM_MAX_LENGTH = 2000;
export const ADMIN_NOTES_MAX_LENGTH = 2000;
export const PHONE_MIN_DIGITS = 8;
export const PHONE_MAX_DIGITS = 15;

const serviceTypeRefSchema = z.object({ serviceTypeId: z.string(), code: z.string(), name: z.string() });

export const orderSchema = z.object({
  orderId: z.string(),
  orderNo: z.string(),
  customerName: z.string(),
  customerPhone: z.string(),
  address: z.string(),
  problemDescription: z.string(),
  serviceType: serviceTypeRefSchema,
  quotedPrice: z.string(),
  technician: z.object({ userId: z.string(), name: z.string(), phone: z.string().nullable() }).nullable(),
  adminNotes: z.string().nullable(),
  status: z.string(),
  statusChangedAt: z.string(),
  startedAt: z.string().nullable(),
  jobDoneAt: z.string().nullable(),
  reviewedAt: z.string().nullable(),
  closedAt: z.string().nullable(),
  createdAt: z.string(),
});

export const orderListItemSchema = z.object({
  orderId: z.string(),
  orderNo: z.string(),
  customerName: z.string(),
  address: z.string(),
  serviceType: serviceTypeRefSchema,
  quotedPrice: z.string(),
  technician: z.object({ userId: z.string(), name: z.string() }).nullable(),
  status: z.string(),
  createdAt: z.string(),
});

export const orderEventSchema = z.object({
  eventType: z.string(),
  fromStatus: z.string().nullable(),
  toStatus: z.string().nullable(),
  actor: z.object({ userId: z.string(), name: z.string() }),
  detail: z.record(z.string(), z.unknown()),
  createdAt: z.string(),
});

export const orderListSchema = z.object({ items: z.array(orderListItemSchema), total: z.number(), page: z.number(), pageSize: z.number() });
export const orderDetailSchema = z.object({ order: orderSchema, events: z.array(orderEventSchema) });
export const orderEnvelopeSchema = z.object({ order: orderSchema });
export const orderWithNotificationSchema = z.object({ order: orderSchema, notification: notificationSchema.nullable() });
export const technicianListSchema = z.object({
  items: z.array(z.object({ userId: z.string(), name: z.string(), phone: z.string().nullable() })),
});

export type Order = z.infer<typeof orderSchema>;
export type OrderListItem = z.infer<typeof orderListItemSchema>;
export type OrderEvent = z.infer<typeof orderEventSchema>;
export type OrderList = z.infer<typeof orderListSchema>;
export type OrderDetail = z.infer<typeof orderDetailSchema>;
export type OrderWithNotification = z.infer<typeof orderWithNotificationSchema>;
export type Technician = z.infer<typeof technicianListSchema>["items"][number];

// Normalises a customer phone the way the server does: strip separators and a leading plus, and turn a local 0 into 60.
export function normaliseCustomerPhone(value: string) {
  const digits = value.trim().replace(/[\s\-()]/g, "").replace(/^\+/, "");
  return digits.startsWith("0") ? `60${digits.slice(1)}` : digits;
}

const AMOUNT_PATTERN = /^\d{1,8}(\.\d{1,2})?$/;

// Builds a required trimmed text rule with a length limit.
function requiredText(message: string, max: number) {
  return z.string().trim().min(1, message).max(max, `Use at most ${max} characters.`);
}

export const orderFormSchema = z.object({
  customerName: requiredText("Enter the customer's name.", CUSTOMER_NAME_MAX_LENGTH),
  customerPhone: z.string().refine((value) => {
    const digits = normaliseCustomerPhone(value);
    return /^[0-9]+$/.test(digits) && digits.length >= PHONE_MIN_DIGITS && digits.length <= PHONE_MAX_DIGITS;
  }, "Enter a valid phone number."),
  address: requiredText("Enter the service address.", ADDRESS_MAX_LENGTH),
  problemDescription: requiredText("Describe the problem.", PROBLEM_MAX_LENGTH),
  serviceTypeId: z.string().min(1, "Choose a service type."),
  quotedPrice: z.string().trim().regex(AMOUNT_PATTERN, "Enter an amount such as 150 or 150.50."),
  technicianId: z.string(),
  adminNotes: z.string().max(ADMIN_NOTES_MAX_LENGTH, `Use at most ${ADMIN_NOTES_MAX_LENGTH} characters.`),
});

export type OrderFormValues = z.infer<typeof orderFormSchema>;

export type CreateOrderPayload = {
  customerName: string;
  customerPhone: string;
  address: string;
  problemDescription: string;
  serviceTypeId: string;
  quotedPrice: string;
  technicianId?: string;
  adminNotes?: string;
};

export type UpdateOrderPayload = Partial<Omit<CreateOrderPayload, "technicianId" | "adminNotes">> & { adminNotes?: string | null };
