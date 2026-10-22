import type { ReactNode } from "react";
import type { Decision, ScanReport } from "../api/types";
export function Badge({ decision }: { decision: Decision }) {
    return (
        <span className={`badge ${decision.toLowerCase()}`}>{decision}</span>
    );
}
export function State({
    loading,
    error,
    empty,
    children,
}: {
    loading: boolean;
    error: string;
    empty?: boolean;
    children: ReactNode;
}) {
    if (loading)
        return (
            <div role="status" className="panel state">
                Loading data…
            </div>
        );
    if (error)
        return (
            <div role="alert" className="panel state">
                {error}
                <p>Check the API connection and session, then reload.</p>
            </div>
        );
    if (empty)
        return (
            <div className="panel state">
                No scans yet. Submit code to create the first report.
            </div>
        );
    return <>{children}</>;
}
export function Provenance({ scan }: { scan?: ScanReport }) {
    if (!scan) return null;
    return (
        <div className="provenance">
            {scan.model_mode === "stub" && (
                <strong>STUB MODEL · heuristic predictions</strong>
            )}
            {scan.artifact_kind === "SMOKE" && (
                <strong>SMOKE ARTIFACT · pipeline verification only</strong>
            )}
            {scan.synthetic && <strong>SYNTHETIC DEMO DATA</strong>}
            <span>
                {scan.model_version} · {scan.analysis.static_analyzer_mode} ·{" "}
                {scan.analysis.extractor_modes.join(", ")}
            </span>
        </div>
    );
}
export function Header({
    eyebrow,
    title,
    description,
}: {
    eyebrow: string;
    title: string;
    description: string;
}) {
    return (
        <header className="page-heading">
            <span className="eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{description}</p>
        </header>
    );
}
export function percent(value: number | null) {
    return value === null ? "Unavailable" : `${Math.round(value * 100)}%`;
}
