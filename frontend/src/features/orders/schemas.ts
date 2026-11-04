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
