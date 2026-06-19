/**
 * @module types/index.ts
 * @description Shared TypeScript types mirroring backend Pydantic schemas.
 *              Single source of truth for all domain entities used across
 *              the frontend — components, stores, and API call helpers.
 * @dependencies none
 */

export type Plan = "free" | "pro" | "unlimited";
export type ApplicationStatus =
  | "pending" | "generated" | "sent" | "opened" | "replied" | "rejected" | "offer";

export interface User { id: string; email: string; name: string | null;
  avatar_url: string | null; plan: Plan; created_at: string; }
export interface TokenPair { access_token: string; refresh_token: string; token_type: string; }
export interface Job { id: string; source: string; company: string; role: string;
  jd_url: string | null; location: string | null; salary_range: string | null;
  match_score: number | null; posted_at: string | null; status: string; }
export interface JobList { items: Job[]; total: number; page: number; page_size: number; }
export interface Resume { id: string; filename: string; storage_url: string; created_at: string; }
export interface Application {
  id: string; job_id: string; status: ApplicationStatus;
  email_subject: string | null; email_body: string | null; cover_letter: string | null;
  linkedin_msg: string | null; recruiter_email: string | null; recruiter_linkedin: string | null;
  sent_at: string | null; follow_up_at: string | null; reply_at: string | null;
  created_at: string; job: Job;
}
export interface DashboardStats { total_applications: number;
  by_status: Record<string, number>; reply_rate: number; recent: Application[]; }
