export type Decision = "PASS" | "WARN" | "BLOCK" | "ERROR";
export interface Finding {
    file: string;
    rule: string;
    severity: "High" | "Medium" | "Low";
    line: number;
    message: string;
}
export interface FunctionReport {
    name: string;
    file: string;
    start_line: number;
    end_line: number;
    probability: number | null;
    risk_score: number | null;
    decision: Decision;
    code: string;
    token_importance: { token: string; line: number; importance: number }[];
}
export interface ScanReport {
    scan_id: string;
    repository: string;
    decision: Decision;
    risk_score: number | null;
    functions: FunctionReport[];
    findings: Finding[];
    reasons: string[];
    model_version: string;
    model_mode: "stub" | "real" | "unavailable";
    artifact_kind: "STUB" | "SMOKE" | "TRAINED" | "UNAVAILABLE";
    synthetic: boolean;
    timestamp: string;
    errors: string[];
    analysis: {
        static_analyzer_mode: string;
        extractor_modes: string[];
        ablation_mode: string;
    };
}
export interface ModelInfo {
    model_version: string;
    model_mode: string;
    artifact_kind: string;
    metrics: Record<string, number> | null;
    thresholds: Record<string, number>;
    limitations: string[];
}
export interface Repo {
    id: number;
    repository: string;
    latest_scan?: {
        decision: Decision;
        risk_score: number | null;
        artifact_kind: string;
        timestamp: string;
    } | null;
}
export interface AuthConfig {
    dev_login_enabled: boolean;
    github_enabled: boolean;
    auth_required: boolean;
}
