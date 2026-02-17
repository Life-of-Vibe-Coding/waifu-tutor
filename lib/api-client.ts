import axios from "axios";

const apiBaseUrl = typeof window !== "undefined" ? "" : process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000";

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});
