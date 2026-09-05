import { Suspense } from "react";

import DashboardClient from "./DashboardClient";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-1 items-center justify-center px-6 py-20">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
        </div>
      }
    >
      <DashboardClient />
    </Suspense>
  );
}
