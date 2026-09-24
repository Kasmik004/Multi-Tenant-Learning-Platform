import { getApiStatus } from "@/features/health/api";

export default async function Home() {
  const status = await getApiStatus();
  const healthy = status === "ok";

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-6 px-6 py-24">
      <h1 className="text-3xl font-semibold tracking-tight">Learning Platform</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Multi-tenant learning platform for institutes and organizations.
      </p>
      <div className="flex items-center gap-2 text-sm">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${healthy ? "bg-green-500" : "bg-red-500"}`}
        />
        API &amp; database: {healthy ? "connected" : "unreachable"}
      </div>
    </main>
  );
}
