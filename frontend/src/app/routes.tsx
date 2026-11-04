import { Navigate, Route, Routes } from "react-router";
import { ProtectedRoute } from "@/features/auth/components/protected-route";
import { HomePage } from "@/features/auth/pages/home-page";
import { LoginPage } from "@/features/auth/pages/login-page";
import { ResetPasswordPage } from "@/features/auth/pages/reset-password-page";
import { CreateOrderPage } from "@/features/orders/pages/admin/create-order-page";
import { EditOrderPage } from "@/features/orders/pages/admin/edit-order-page";
import { OrderDetailPage } from "@/features/orders/pages/admin/order-detail-page";
import { OrdersPage } from "@/features/orders/pages/admin/orders-page";
import { ReviewQueuePage } from "@/features/orders/pages/manager/review-queue-page";
import { NotificationsPage } from "@/features/orders/pages/notifications-page";
import { JobPage } from "@/features/orders/pages/technician/job-page";
import { MyJobsPage } from "@/features/orders/pages/technician/my-jobs-page";
import { CreateUserPage } from "@/features/users/pages/create-user-page";
import { EditUserPage } from "@/features/users/pages/edit-user-page";
import { UsersPage } from "@/features/users/pages/users-page";

// Declares public routes and the role-gated route groups.
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
      </Route>
      <Route element={<ProtectedRoute roles={["admin"]} />}>
        <Route path="/users" element={<UsersPage />} />
        <Route path="/users/new" element={<CreateUserPage />} />
        <Route path="/users/:userId/edit" element={<EditUserPage />} />
        <Route path="/orders/new" element={<CreateOrderPage />} />
        <Route path="/orders/:orderId/edit" element={<EditOrderPage />} />
      </Route>
      <Route element={<ProtectedRoute roles={["admin", "manager"]} />}>
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/orders/:orderId" element={<OrderDetailPage />} />
      </Route>
      <Route element={<ProtectedRoute roles={["manager"]} />}>
        <Route path="/review" element={<ReviewQueuePage />} />
      </Route>
      <Route element={<ProtectedRoute roles={["technician"]} />}>
        <Route path="/jobs" element={<MyJobsPage />} />
        <Route path="/jobs/:orderId" element={<JobPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
