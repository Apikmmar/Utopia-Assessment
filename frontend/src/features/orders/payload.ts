import type { CreateOrderPayload, Order, OrderFormValues, UpdateOrderPayload } from "./schemas";

// Builds the create payload from validated form values, leaving out an empty technician and empty instructions.
export function toCreatePayload(values: OrderFormValues): CreateOrderPayload {
  return {
    customerName: values.customerName.trim(),
    customerPhone: values.customerPhone.trim(),
    address: values.address.trim(),
    problemDescription: values.problemDescription.trim(),
    serviceTypeId: values.serviceTypeId,
    quotedPrice: values.quotedPrice.trim(),
    technicianId: values.technicianId || undefined,
    adminNotes: values.adminNotes.trim() || undefined,
  };
}

// Builds the edit payload from validated form values; blank instructions clear them.
export function toUpdatePayload(values: OrderFormValues): UpdateOrderPayload {
  const { technicianId: _technicianId, ...payload } = toCreatePayload(values);
  return { ...payload, adminNotes: values.adminNotes.trim() || null };
}

// Returns the form values that show an existing order in the edit form.
export function toFormValues(order: Order): OrderFormValues {
  return {
    customerName: order.customerName,
    customerPhone: order.customerPhone,
    address: order.address,
    problemDescription: order.problemDescription,
    serviceTypeId: order.serviceType.serviceTypeId,
    quotedPrice: order.quotedPrice,
    technicianId: order.technician?.userId ?? "",
    adminNotes: order.adminNotes ?? "",
  };
}
