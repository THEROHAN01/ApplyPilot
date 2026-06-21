"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signup } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [password, setPassword] = useState(""); const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(null); setLoading(true);
    try { await signup(email, password, name || undefined); router.push("/dashboard"); }
    catch { setError("Could not create account — email may already be registered."); }
    finally { setLoading(false); }
  }
  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm border border-ink bg-surface p-8 shadow-hard space-y-5">
        <h1 className="text-4xl">ApplyPilot</h1>
        <p className="label">Create account</p>
        {error && <p className="font-mono text-[0.8rem] text-[var(--warn)]">{error}</p>}
        <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} disabled={loading} />
        <Input type="email" placeholder="you@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} required disabled={loading} />
        <Input type="password" placeholder="Password (min 8 chars)" value={password}
          onChange={(e) => setPassword(e.target.value)} required minLength={8} disabled={loading} />
        <Button type="submit" variant="primary" disabled={loading} className="w-full justify-center">
          {loading ? "Creating…" : "Create account"}
        </Button>
        <p className="font-mono text-[0.75rem] text-ink-soft">
          Have an account? <Link href="/login" className="text-blueprint">Sign in</Link>
        </p>
      </form>
    </main>
  );
}
