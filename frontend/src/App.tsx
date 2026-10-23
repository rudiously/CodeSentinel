import { useEffect, useState } from "react";
import { api, useMocks } from "./api/client";
import { Login } from "./pages/Login";
import { Repos } from "./pages/Repos";
import { ScanHistory } from "./pages/ScanHistory";
import { ScanDetail } from "./pages/ScanDetail";
import { Analytics } from "./pages/Analytics";
import { ModelInfo } from "./pages/ModelInfo";
export default function App() {
    const path = window.location.pathname;
    const [mode, setMode] = useState("");
    useEffect(() => {
        const token = new URLSearchParams(window.location.hash.slice(1)).get(
            "token",
        );
        if (token) {
            sessionStorage.setItem("codesentinel_token", token);
            window.history.replaceState(null, "", "/history");
            window.location.replace("/history");
        }
        void api
            .model()
            .then((info) => setMode(info.artifact_kind))
            .catch(() => setMode("unavailable"));
    }, []);
    const page = path.startsWith("/scans/") ? (
        <ScanDetail id={path.split("/")[2] ?? ""} />
    ) : path === "/repos" ? (
        <Repos />
    ) : path === "/analytics" ? (
        <Analytics />
    ) : path === "/model" ? (
        <ModelInfo />
    ) : path === "/login" ||
      (!useMocks && !sessionStorage.getItem("codesentinel_token")) ? (
        <Login />
    ) : (
        <ScanHistory />
    );
    return (
        <div className="shell">
            <aside>
                <a href="/history" className="brand">
                    <span className="brand-icon">CS</span>
                    <span>
                        CodeSentinel<small>AI-ASSISTED SECURITY</small>
                    </span>
                </a>
                <div className="nav-label">WORKSPACE</div>
                <nav aria-label="Main navigation">
                    {[
                        ["/history", "Scan history"],
                        ["/repos", "Repositories"],
                        ["/analytics", "Analytics"],
                        ["/model", "Model info"],
                    ].map(([href, label]) => (
                        <a
                            key={href}
                            className={path === href ? "active" : ""}
                            href={href}
                        >
                            {label}
                            <span>↗</span>
                        </a>
                    ))}
                </nav>
                <div className="sidebar-note">
                    Security signals.
                    <br />
                    Human decisions.
                    <p>Review every automated finding before acting.</p>
                </div>
                <button
                    className="logout"
                    onClick={() => {
                        sessionStorage.removeItem("codesentinel_token");
                        window.location.assign("/login");
                    }}
                >
                    Sign out
                </button>
            </aside>
            <div className="main">
                <div className="topbar">
                    <span>CODE REVIEW / WORKSPACE</span>
                    <span>Hybrid security gate</span>
                </div>
                {(useMocks || mode === "STUB" || mode === "SMOKE") && (
                    <div className="global-banner" role="status">
                        {useMocks ? "SYNTHETIC MOCK DATA · " : ""}
                        {mode === "SMOKE"
                            ? "SMOKE ARTIFACT · pipeline verification only"
                            : "STUB MODEL · deterministic heuristic, not trained ML"}
                    </div>
                )}
                <main>{page}</main>
                <footer>
                    CodeSentinel · Automated review assists; it does not
                    guarantee safety.
                </footer>
            </div>
        </div>
    );
}
