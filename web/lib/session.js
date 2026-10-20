"use client";
import { createContext, useContext } from "react";

export const SessionContext = createContext({ user: null, health: null, setUser: () => {}, refreshHealth: () => {} });

export function useSession() {
  return useContext(SessionContext);
}
