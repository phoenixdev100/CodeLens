import { Suspense } from "react";

import AnalyzeClient from "./AnalyzeClient";

export default function AnalyzePage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-1 items-center justify-center px-6 py-20">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-zinc-700 border-t-indigo-500" />
        </div>
      }
    >
      <AnalyzeClient />
    </Suspense>
  );
}
