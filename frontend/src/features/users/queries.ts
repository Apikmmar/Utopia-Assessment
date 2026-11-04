import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";
import type { UpdateUserPayload, User } from "./schemas";
import type { UserListFilters } from "./types";

export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  list: (filters: UserListFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail: (userId: string) => [...userKeys.details(), userId] as const,
};

// Reads one filtered page of users, keeping the previous page visible while the next loads.
export function useUsers(filters: UserListFilters) {
  return useQuery({
    queryKey: userKeys.list(filters),
    queryFn: ({ signal }) => api.listUsers(filters, signal),
    placeholderData: keepPreviousData,
  });
}

// Reads one user for the edit form.
export function useUser(userId: string) {
  return useQuery({
    queryKey: userKeys.detail(userId),
    queryFn: ({ signal }) => api.getUser(userId, signal),
  });
}

// Creates a user and refreshes cached user lists.
export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.lists() }),
  });
}

// Updates a user, stores the returned record, and refreshes cached user lists.
export function useUpdateUser(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateUserPayload) => api.updateUser(userId, payload),
    onSuccess: (user: User) => {
      queryClient.setQueryData(userKeys.detail(userId), user);
      return queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
