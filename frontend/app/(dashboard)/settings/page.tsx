/**
 * @module app/(dashboard)/settings/page.tsx
 * @description Settings page with resume upload via hidden file input.
 *              Shows upload status, error state, and list of existing resumes.
 * @dependencies @/components/ui/card, button, @/hooks/useResumes
 */

"use client";
import { useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useResumes, useUploadResume } from "@/hooks/useResumes";

export default function SettingsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: resumes, isLoading } = useResumes();
  const upload = useUploadResume();
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl mb-6">Settings</h1>
      <Card className="shadow-hard">
        <p className="label mb-4">Resume</p>
        <input ref={inputRef} type="file" accept=".pdf,.doc,.docx" hidden
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); }} />
        <Button variant="primary" disabled={upload.isPending} onClick={() => inputRef.current?.click()}>
          {upload.isPending ? "Uploading…" : "Upload resume"}
        </Button>
        {upload.isError && <p className="font-mono text-[0.8rem] text-[var(--warn)] mt-3">Upload failed.</p>}
        <div className="mt-6 space-y-2">
          {isLoading && <p className="font-mono text-ink-soft">Loading…</p>}
          {resumes?.map((r) => (
            <p key={r.id} className="font-mono text-[0.8rem]">{r.filename}
              <span className="text-ink-mute"> · {new Date(r.created_at).toLocaleDateString()}</span></p>
          ))}
          {resumes && resumes.length === 0 && <p className="font-mono text-ink-mute">No resume uploaded.</p>}
        </div>
      </Card>
    </div>
  );
}
