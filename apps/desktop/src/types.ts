export type Post = {
  id: string;
  platform: string;
  url: string;
  author_name: string;
  content: string;
  lead_score: number;
  intent_score: number;
  spam_score: number;
  urgency: string;
  phone_extracted: string | null;
  posted_at: string;
  is_saved: boolean;
};
export type Person = {
  id: string;
  display_name: string;
  phones: string[];
  is_customer: boolean;
  source_type: string;
  contact_quality_score: number;
};
export type Profile = {
  id: string;
  display_name: string;
  customer_id: string | null;
  phones: {
    normalized_phone: string;
    source_type: string;
    source_url: string | null;
    is_verified: boolean;
  }[];
  notes: { id: string; content: string; created_at: string }[];
  labels: string[];
  timeline: { id: string; title: string; created_at: string }[];
  permission: {
    marketing_allowed: boolean;
    zalo_allowed: boolean;
    opt_out: boolean;
    do_not_contact: boolean;
  };
};
export type Customer = {
  id: string;
  person_id: string;
  display_name: string;
  phones: string[];
  status: string;
  need_type: string | null;
  lead_score: number;
  next_care_date: string | null;
};
export type Opportunity = {
  id: string;
  title: string;
  stage: string;
  expected_revenue: number;
};
export type Customer360 = {
  id: string;
  person_id: string;
  display_name: string;
  status: string;
  need_type: string | null;
  property_type: string | null;
  province: string | null;
  urgency: string | null;
  opportunities: Opportunity[];
  timeline: { id: string; title: string; created_at: string }[];
};
export type Task = {
  id: string;
  customer_id: string;
  title: string;
  description: string | null;
  scheduled_at: string;
  status: string;
  priority: string;
  is_overdue: boolean;
};
export type Job = {
  id: string;
  platform: string;
  keywords: string[];
  status: string;
  scanned_count: number;
  matched_count: number;
  qualified_count: number;
  spam_count: number;
  error_message: string | null;
};
export type Analysis = {
  score: {
    overall_lead_score: number;
    intent_score: number;
    urgency_score: number;
    opportunity_score: number;
    spam_score: number;
    contact_quality_score: number;
    next_best_action: string;
    action_reason: string;
    breakdown: { category: string; points: number; reason: string }[];
  };
  need: {
    need_type: string;
    province: string | null;
    property_type: string;
    urgency: string;
  };
  phones: {
    normalized_phone: string;
    source_url: string;
    is_verified: boolean;
  }[];
};
export type Comment = {
  id: string;
  author_name: string;
  content: string;
  detected_phone: string | null;
  intent_score: number;
};
export type Rule = {
  id: string;
  entity_type: string;
  value: string;
  mode: string;
  reason: string;
};
export type Conversation = {
  id: string;
  title: string;
  person_id: string;
  external_conversation_id: string;
};
export type Message = {
  id: string;
  sender_type: string;
  content: string;
  sent_at: string;
};
export const stages = [
  "NEW",
  "QUALIFIED",
  "CONTACTED",
  "INTERESTED",
  "QUOTED",
  "APPOINTMENT",
  "WON",
  "LOST",
  "PAUSED",
];
export const labels: Record<string, string> = {
  NEW: "Mới",
  QUALIFIED: "Đủ điều kiện",
  CONTACTED: "Đã liên hệ",
  INTERESTED: "Quan tâm",
  QUOTED: "Đã báo giá",
  APPOINTMENT: "Đã hẹn",
  WON: "Thành công",
  LOST: "Không thành công",
  PAUSED: "Tạm dừng",
  PENDING: "Chờ xử lý",
  COMPLETED: "Hoàn thành",
  RUNNING: "Đang chạy",
  FAILED: "Lỗi",
  STOPPED: "Đã dừng",
  HIGH: "Cao",
  MEDIUM: "Vừa",
  LOW: "Thấp",
  WIFI: "WiFi",
  CAMERA: "Camera",
  TV: "Truyền hình",
  COMBO: "Combo",
  OTHER: "Khác",
  FACEBOOK: "Facebook",
  THREADS: "Threads",
  MANUAL: "Thủ công",
};
