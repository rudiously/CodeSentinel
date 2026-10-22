import { api } from "../api/client";
import { useResource } from "../hooks/useResource";
import { Badge, Header, State } from "../components/common";
export function Repos() {
    const repos = useResource(api.repos, "repos");
    return (
        <>
            <Header
                eyebrow="WORKSPACE"
                title="Repositories"
                description="Repositories appear after their first scan. Configure the Action or GitHub App to connect a project."
            />
            <State
                loading={repos.loading}
                error={repos.error}
                empty={repos.data?.length === 0}
            >
                <div className="repo-grid">
                    {repos.data?.map((repo) => (
                        <a
                            className="panel repo-card"
                            key={repo.id}
                            href={`/history?repo=${encodeURIComponent(repo.repository)}`}
                        >
                            <span className="muted">GITHUB REPOSITORY</span>
                            <h2>{repo.repository}</h2>
                            {repo.latest_scan && (
                                <div className="row">
                                    <Badge
                                        decision={repo.latest_scan.decision}
                                    />
                                    <small>
                                        {repo.latest_scan.artifact_kind}
                                    </small>
                                </div>
                            )}
                            <span>View scan history →</span>
                        </a>
                    ))}
                </div>
            </State>
        </>
    );
}
