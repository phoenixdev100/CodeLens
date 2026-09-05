"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

export default function ImpactMapClient() {
  const params = useSearchParams();
  const router = useRouter();
  const prUrl = params.get("pr") ?? "";

  useEffect(() => {
    if (prUrl) {
      router.replace(`/dashboard?pr=${encodeURIComponent(prUrl)}`);
    } else {
      router.replace("/");
    }
  }, [prUrl, router]);

  return (
    <div className="flex flex-1 items-center justify-center bg-slate-50 px-6 py-20">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
    </div>
  );
}
