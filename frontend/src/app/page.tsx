"use strict";

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function IndexPage() {
  const router = useRouter();

  useEffect(() => {
    api.getMe()
      .then(() => {
        router.push("/dashboard");
      })
      .catch(() => {
        router.push("/login");
      });
  }, [router]);

  return (
    <main className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
    </main>
  );
}
