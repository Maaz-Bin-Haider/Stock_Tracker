"use client";

import { createContext, useContext } from "react";

export type Role = "ADMIN" | "PURCHASE" | "SALE" | "VIEWER";

export interface SessionUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
}

export const AuthContext = createContext<SessionUser | null>(null);

export function useAuth(): SessionUser | null {
  return useContext(AuthContext);
}
