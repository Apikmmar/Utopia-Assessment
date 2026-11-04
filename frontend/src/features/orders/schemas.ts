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
