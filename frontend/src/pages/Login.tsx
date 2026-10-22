import { useState } from "react";
import { api, apiUrl, useMocks } from "../api/client";
import { useResource } from "../hooks/useResource";
import { Header, State } from "../components/common";
export function Login() {
    const auth = useResource(api.auth, "auth");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    async function login() {
        setBusy(true);
        try {
            const result = await api.devLogin();
            sessionStorage.setItem("codesentinel_token", result.access_token);
            window.location.assign("/history");
        } catch (e) {
            setError(e instanceof Error ? e.message : "Login failed");
        } finally {
            setBusy(false);
        }
    }
    return (
        <>
            <Header
                eyebrow="ACCESS CONTROL"
                title="Review code. Know the risk."
                description="A shared view of model signals, static findings, and pull request decisions."
            />
            <div className="panel login">
                <h2>Sign in to CodeSentinel</h2>
                <p>For your configured GitHub installation.</p>
                <State loading={auth.loading} error={auth.error}>
                    {auth.data?.github_enabled ? (
                        <a className="button" href={`${apiUrl}/auth/github`}>
                            Continue with GitHub →
                        </a>
                    ) : (
                        <p>GitHub OAuth is not configured.</p>
                    )}
                    {auth.data?.dev_login_enabled && (
                        <button disabled={busy} onClick={() => void login()}>
                            {busy ? "Signing in…" : "DEV-ONLY demo login"}
                        </button>
                    )}
                    {useMocks && (
                        <a href="/history">View SYNTHETIC mock dashboard →</a>
                    )}
                </State>
                {error && <p role="alert">{error}</p>}
                <small>
                    Automated signals support human review. They do not prove
                    code is safe.
                </small>
            </div>
        </>
    );
}
