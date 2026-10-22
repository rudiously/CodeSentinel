import { useState } from "react";
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    CartesianGrid,
    XAxis,
    YAxis,
    Tooltip,
    PieChart,
    Pie,
    Cell,
} from "recharts";
import { api } from "../api/client";
import { useResource } from "../hooks/useResource";
import { Header, State, Provenance, percent } from "../components/common";
import type { Decision } from "../api/types";
const colors: Record<Decision, string> = {
    PASS: "#75d8a0",
    WARN: "#f6c76d",
    BLOCK: "#fa9090",
    ERROR: "#a8b0ba",
};
export function Analytics() {
    const history = useResource(api.history, "analytics");
    const [repository, setRepository] = useState("ALL");
    const allScans = history.data ?? [];
    const scans = allScans.filter(
        (s) => repository === "ALL" || s.repository === repository,
    );
    const valid = scans.filter((s) => s.risk_score !== null);
    const avg = valid.length
        ? valid.reduce((sum, s) => sum + (s.risk_score ?? 0), 0) / valid.length
        : null;
    const mix = (Object.keys(colors) as Decision[]).map((name) => ({
        name,
        value: scans.filter((s) => s.decision === name).length,
    }));
    const trends = [...scans]
        .reverse()
        .map((s) => ({
            name: new Date(s.timestamp).toLocaleDateString(),
            risk: s.risk_score === null ? null : Math.round(s.risk_score * 100),
        }));
    return (
        <>
            <Header
                eyebrow="OBSERVABILITY"
                title="Risk analytics"
                description="Recent scan activity. These operational statistics are not model accuracy metrics."
            />
            <div className="toolbar">
                <label>
                    Repository{" "}
                    <select
                        value={repository}
                        onChange={(e) => setRepository(e.target.value)}
                    >
                        <option value="ALL">All repositories</option>
                        {[...new Set(allScans.map((s) => s.repository))].map(
                            (repo) => (
                                <option key={repo}>{repo}</option>
                            ),
                        )}
                    </select>
                </label>
            </div>
            <Provenance scan={scans[0]} />
            <State
                loading={history.loading}
                error={history.error}
                empty={scans.length === 0}
            >
                <div className="stats">
                    <div className="panel">
                        <span>RECENT SCANS</span>
                        <strong>{scans.length}</strong>
                    </div>
                    <div className="panel">
                        <span>AVERAGE RISK</span>
                        <strong>{percent(avg)}</strong>
                    </div>
                    <div className="panel">
                        <span>ERROR SCANS</span>
                        <strong>
                            {scans.filter((s) => s.decision === "ERROR").length}
                        </strong>
                    </div>
                </div>
                <div className="charts">
                    <section className="panel">
                        <h2>Risk over time</h2>
                        <ResponsiveContainer width="100%" height={260}>
                            <AreaChart data={trends}>
                                <CartesianGrid stroke="#303840" />
                                <XAxis dataKey="name" stroke="#a8b0ba" />
                                <YAxis domain={[0, 100]} stroke="#a8b0ba" />
                                <Tooltip />
                                <Area
                                    type="monotone"
                                    dataKey="risk"
                                    stroke="#9dbafa"
                                    fill="#293e60"
                                    connectNulls={false}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </section>
                    <section className="panel">
                        <h2>Decision mix</h2>
                        <ResponsiveContainer width="100%" height={260}>
                            <PieChart>
                                <Pie
                                    data={mix.filter((m) => m.value)}
                                    dataKey="value"
                                    nameKey="name"
                                    innerRadius={65}
                                    outerRadius={95}
                                >
                                    {mix
                                        .filter((m) => m.value)
                                        .map((m) => (
                                            <Cell
                                                key={m.name}
                                                fill={colors[m.name]}
                                            />
                                        ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="legend">
                            {mix.map((m) => (
                                <span key={m.name}>
                                    {m.name}: {m.value}
                                </span>
                            ))}
                        </div>
                    </section>
                </div>
                <p className="muted">
                    Showing up to 100 recent scans; repository-level research
                    evaluation is separate.
                </p>
            </State>
        </>
    );
}
