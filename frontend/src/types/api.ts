import type { MeetingStatus } from "@/lib/meeting-status";

export type SummaryStatus = "none" | "pending" | "ready" | "stale" | "failed";
export type IndexStatus = "none" | "pending" | "ready" | "stale" | "failed";
export type SharePermission = "viewer" | "editor";
export type ActionItemStatus = "pending" | "completed";
export type ChatRole = "user" | "assistant" | "tool";
export type ChatMessageStatus = "ok" | "error";
export type ExportFormat = "docx" | "txt" | "srt" | "vtt" | "json";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterResult {
  user: User;
  tokens: TokenPair;
}

export interface ChangePasswordResult {
  tokens: TokenPair;
}

export interface Meeting {
  id: string;
  title: string;
  status: MeetingStatus;
  duration_seconds: number;
  created_by: string | null;
  share_token: string | null;
  share_permission: SharePermission;
  is_deleted: boolean;
  summary_status: SummaryStatus;
  index_status: IndexStatus;
  transcript_revision: number;
  failure_stage: string | null;
  failure_reason: string | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface MeetingShareLink {
  meeting_id: string;
  share_token: string;
  share_url: string;
  share_permission: SharePermission;
}

export interface AudioUploadResult {
  meeting_id: string;
  audio_file_id: string;
  file_name: string;
  file_size_bytes: number;
  status: string;
}

export interface AudioStreamUrl {
  url: string;
  expires_at: number;
}

export interface TranscriptSegment {
  id: string;
  meeting_id: string;
  speaker_label: string;
  start_time: number;
  end_time: number;
  content: string;
  sequence_order: number;
  version?: number;
  created_at: string;
}

export interface Summary {
  id: string;
  meeting_id: string;
  executive_summary: string;
  key_points: string[];
  created_at: string;
}

export interface ActionItem {
  id: string;
  meeting_id: string;
  description: string;
  assignee: string;
  status: ActionItemStatus;
  due_date: string | null;
  created_at: string;
}

export interface Citation {
  segment_id?: string;
  speaker_label?: string;
  start_time: number;
  end_time?: number;
  quote?: string;
}

export interface ToolCall {
  name: string;
  args?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  citations: Citation[];
  tool_calls?: ToolCall[];
  status: ChatMessageStatus;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  my_role: string | null;
  members_count: number;
  meetings_count: number;
  created_at: string;
}

export interface ProjectMember {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export interface ProjectDetail {
  project: Project;
  my_role: string | null;
  members: ProjectMember[];
  meetings: Meeting[];
}

export interface CreateProjectPayload {
  name: string;
  description: string | null;
}

export interface Plan {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  price_amount: number;
  currency: string;
  billing_interval: string;
  total_duration_limit_minutes: number;
  features: Record<string, unknown>;
  is_default: boolean;
  is_active: boolean;
}

export interface Subscription {
  id: string;
  plan_slug: string;
  plan_name: string;
  status: string;
  current_period_end: string;
  total_duration_limit_minutes: number;
  used_duration_minutes: number;
  remaining_duration_minutes: number;
}

export interface CheckoutDetails {
  order_id: string;
  order_code: string;
  amount: number;
  currency: string;
  bank_code: string;
  account_number: string;
  account_name: string;
  transfer_content: string;
  qr_url: string;
  expires_at: string;
  status: string;
}

export interface OrderStatus {
  order_code: string;
  status: string;
  paid_at: string | null;
}

export type AgentActionKind = "transcript_ops" | "action_item_ops" | "summary_regenerate";
export type AgentActionStatus =
  | "proposed"
  | "approved"
  | "rejected"
  | "applied"
  | "failed"
  | "expired";

export interface SegmentSnapshot {
  id: string;
  speaker_label: string;
  start_time: number;
  end_time: number;
  content: string;
  sequence_order: number;
}

export interface SegmentDiff {
  op: "update" | "delete" | "insert";
  segment_id: string;
  before: SegmentSnapshot | null;
  after: SegmentSnapshot | null;
  order_only: boolean;
}

export interface ActionItemDiff {
  op: "create" | "update" | "delete";
  action_item_id: string | null;
  before: Record<string, string | null> | null;
  after: Record<string, string | null> | null;
}

export interface AgentActionPreview {
  changes?: Array<SegmentDiff | ActionItemDiff>;
  summary?: string;
  base_revision?: number;
}

export interface AgentAction {
  id: string;
  conversation_id: string;
  meeting_id: string;
  kind: AgentActionKind;
  status: AgentActionStatus;
  base_revision: number;
  payload: Record<string, unknown>;
  preview: AgentActionPreview;
  result: Record<string, unknown> | null;
  change_set_id: string | null;
  created_at: string;
  decided_at: string | null;
}

export type TranscriptOperationPayload =
  | { op: "update_text"; segment_id: string; new_text: string }
  | { op: "reassign_speaker"; segment_ids: string[]; new_label: string }
  | { op: "delete_segments"; segment_ids: string[] };

export interface ApproveActionInput {
  operations?: TranscriptOperationPayload[];
}

export interface ChangeSetSummary {
  id: string;
  revision: number;
  actor_type: "user" | "agent" | "system";
  actor_user_id: string | null;
  summary: string;
  reverts_change_set_id: string | null;
  reverted: boolean;
  created_at: string;
}

export interface ChangeSetDetail extends ChangeSetSummary {
  operations: Array<Record<string, unknown>>;
  changes: SegmentDiff[];
}

export interface ChangeSetResult {
  change_set_id: string;
  revision: number;
  affected_segment_ids: string[];
}

export type ArtifactKind = "minutes_docx" | "email_draft" | "srt" | "custom_md";

export interface MeetingArtifact {
  id: string;
  meeting_id: string;
  kind: ArtifactKind;
  title: string;
  mime_type: string;
  size_bytes: number;
  source_revision: number;
  created_at: string;
}

export type AssistantEvent =
  | { type: "token"; data: { text: string } }
  | { type: "tool_start"; data: { name: string; args?: Record<string, unknown> } }
  | { type: "tool_end"; data: { name: string; summary?: string } }
  | { type: "proposal"; data: AgentAction }
  | { type: "citation"; data: Citation }
  | { type: "done"; data: { message_id: string } }
  | { type: "error"; data: { code: string; message: string } };
