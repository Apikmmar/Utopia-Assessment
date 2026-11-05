import { apiRequest } from "@/lib/api-client";
import { aiAnswerSchema, type AiAnswer } from "./schemas";

// Asks the operations assistant one question and returns its answer with the database facts behind it.
export async function askQuestion(question: string): Promise<AiAnswer> {
  return aiAnswerSchema.parse(await apiRequest("/ai/query", { method: "POST", body: { question } }));
}
