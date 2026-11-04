import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import * as api from "./api";
import type { AuthUser } from "./schemas";

export const authKeys = {
  all: ["auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
};

// Reads the current session user; null means logged out.
export function useMe() {
  return useQuery({ queryKey: authKeys.me(), queryFn: api.fetchMe });
}

// Logs in, dropping all cached data when a different user takes over.
export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.login,
    onSuccess: (user: AuthUser) => {
      const previous = queryClient.getQueryData<AuthUser | null>(authKeys.me());
      if (previous && previous.userId !== user.userId) queryClient.clear();
      queryClient.setQueryData(authKeys.me(), user);
    },
  });
}

// Logs out, clears every cached query, and returns to the login page.
export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      queryClient.clear();
      queryClient.setQueryData(authKeys.me(), null);
      navigate("/login", { replace: true });
    },
  });
}

// Submits a password reset for any email.
export function useResetPassword() {
  return useMutation({ mutationFn: api.resetPassword });
}
