import { useMutation } from "@tanstack/react-query";
import * as api from "./api";

// Sends one question; it is never retried automatically, since each answer may spend a model call.
export function useAskQuestion() {
  return useMutation({ mutationFn: api.askQuestion, retry: false });
}
