import { apiRequest } from "@/lib/api-client";
import { serviceTypeListSchema, type ServiceType } from "./schemas";

// Fetches the active service types in display order.
export async function listServiceTypes(signal?: AbortSignal): Promise<ServiceType[]> {
  return serviceTypeListSchema.parse(await apiRequest("/service-types", { signal })).items;
}
