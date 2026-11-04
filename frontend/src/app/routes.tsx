import { Navigate, Route, Routes } from "react-router";
import { ProtectedRoute } from "@/features/auth/components/protected-route";
import { HomePage } from "@/features/auth/pages/home-page";
import { LoginPage } from "@/features/auth/pages/login-page";
import { ResetPasswordPage } from "@/features/auth/pages/reset-password-page";
import { CreateUserPage } from "@/features/users/pages/create-user-page";
import { NotificationsPage } from "@/features/orders/pages/notifications-page";
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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
