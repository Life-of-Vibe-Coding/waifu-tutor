import axios from "axios";

const apiBaseUrl =
  typeof import.meta.env?.VITE_API_BASE_URL === "string" && import.meta.env.VITE_API_BASE_URL
    ? import.meta.env.VITE_API_BASE_URL
    : "";

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});
