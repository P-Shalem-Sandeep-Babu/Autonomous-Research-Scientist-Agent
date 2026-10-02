export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "researcher" | "supervisor" | "administrator";
  is_active?: boolean;
  compute_quota_gpu_hours?: number;
  compute_used_gpu_hours?: number;
  subscription_tier?: string;
  balance_usd?: number;
  token_quota?: number;
  token_used?: number;
  mfa_enabled?: boolean;
  created_at?: string;
}

export interface LoginResponse {
  access_token?: string;
  token_type?: string;
  mfa_required?: boolean;
  message?: string;
}

export interface MFASetupResponse {
  secret: string;
  otpauth_url: string;
  message: string;
}

export interface AdminUser extends User {
  is_active: boolean;
  compute_quota_gpu_hours: number;
  compute_used_gpu_hours: number;
  project_count?: number;
}

export interface ApiKeyItem {
  id: number;
  provider: string;
  model_name: string;
  masked_key: string;
  status: "active" | "inactive" | "revoked";
  created_at?: string;
  last_used?: string | null;
}

export interface ApiKeyCreateInput {
  provider: string;
  model_name: string;
  api_key: string;
}

export interface SystemComputeInfo {
  id?: number;
  active_gpus: string;
  allocated_cpu_cores: number;
  memory_limit_gb: number;
  utilization_pct: number;
  scheduler_status: string;
  updated_at?: string;
}

export interface DashboardAnalytics {
  papers_analyzed: number;
  gaps_found: number;
  hypotheses_generated: number;
  experiments_executed: number;
  publications_generated: number;
  total_projects: number;
  compute_allocated?: {
    gpus_active: number;
    gpu_utilization_pct: number;
    vram_allocated_gb: number;
    vram_total_gb: number;
  };
}

export interface ReasoningStep {
  timestamp: string;
  type?: string;
  stage?: string;
  agent?: string;
  message?: string;
  thought?: string;
  action?: string;
}

export interface ConsoleLogEntry {
  timestamp?: string;
  level?: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  type?: string;
  stage?: string;
  message: string;
}

export interface TerminalHistoryItem {
  type: "command" | "output" | "error";
  text: string;
  exitCode?: number;
}

export interface UploadedPaper {
  id: number;
  project_id: number;
  filename: string;
  file_path: string;
  title?: string;
  authors?: string;
  abstract?: string;
  page_count?: number;
  char_count?: number;
  created_at?: string;
}

export interface SandboxFile {
  name: string;
  path: string;
  filepath?: string;
  size?: number;
  is_directory?: boolean;
}

export interface ResearchStage {
  id: number;
  project_id: number;
  stage_name: string;
  status: "pending" | "active" | "completed" | "failed" | "paused";
  output_data?: Record<string, any> | null;
  started_at?: string | null;
  completed_at?: string | null;
  is_approved?: boolean;
  user_feedback?: string | null;
  reasoning_chain?: ReasoningStep[] | null;
}

export interface Project {
  id: number;
  title: string;
  description?: string | null;
  status: "idle" | "running" | "completed" | "failed" | "paused";
  created_at: string;
  updated_at: string;
  owner?: string;
  user?: {
    id?: number;
    full_name?: string;
    email?: string;
  };
  stages?: ResearchStage[];
}

export interface LiteraturePaper {
  id: number;
  project_id: number;
  title: string;
  authors?: string;
  abstract?: string;
  url?: string;
  source?: string;
  methodology?: string;
  findings?: string;
  limitations?: string;
  relevance_score?: number;
}

export interface ResearchGap {
  id: number;
  project_id: number;
  description: string;
  novelty_score?: number;
  opportunity_score?: number;
}

export interface Hypothesis {
  id: number;
  project_id: number;
  statement: string;
  reasoning?: string;
  confidence_level?: number;
  selected?: boolean;
}

export interface DebateData {
  id: number;
  project_id: number;
  hypothesis_id?: number;
  proposal_a?: string;
  proposal_b?: string;
  proposal_c?: string;
  debate_rounds?: Array<{
    speaker?: string;
    persona?: string;
    argument?: string;
    content?: string;
    role?: string;
  }>;
  winner_proposal?: string;
  rationale?: string;
  proposals_detailed?: Record<string, any>;
  created_at?: string | null;
}

export interface DatasetRecommendation {
  id: number;
  project_id: number;
  name: string;
  source?: string;
  url?: string;
  quality_score?: number;
  description?: string;
  metadata_fields?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface ExperimentPlan {
  id?: number;
  project_id?: number;
  title?: string;
  target_hypothesis?: string;
  target_gap?: string;
  ablation_matrix?: Array<{
    component?: string;
    configuration?: string;
    purpose?: string;
    hypothesis?: string;
    expected_delta?: string;
    metric?: string;
  }>;
  roadmap?: Array<{
    step?: string;
    details?: string;
    category?: string;
    milestone?: string;
    inputs?: string;
    algorithm?: string;
    deliverables?: string;
    mitigation?: string;
  }>;
  metrics?: Array<Record<string, any> | string>;
  hardware_requirements?: Record<string, any>;
}

export interface GeneratedFile {
  id: number;
  project_id: number;
  filepath: string;
  content: string;
  explanation?: string;
}

export interface ExperimentRun {
  id: number;
  project_id: number;
  status: string;
  logs?: string;
  metrics_history?: Array<Record<string, any>>;
  plots?: Record<string, any>;
}

export interface ScientificPaper {
  id: number;
  project_id: number;
  title: string;
  abstract?: string;
  sections?: Record<string, string>;
  pdf_path?: string;
  publication_readiness_score?: number;
}

export interface PeerReview {
  id: number;
  paper_id: number;
  score?: number;
  comments?: Record<string, any>;
  suggestions?: string[];
}

export interface ResearchMemory {
  id: number;
  memory_type: "successful_method" | "failed_method" | "key_insight";
  key: string;
  value: Record<string, any> | string;
  created_at?: string;
}

export interface KnowledgeGraphNode {
  id: string;
  type: string;
  label: string;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
}

export interface KnowledgeGraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface KnowledgeGraphData {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
}

