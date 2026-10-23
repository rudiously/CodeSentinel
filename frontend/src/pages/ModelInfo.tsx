import { api } from "../api/client";
import { useResource } from "../hooks/useResource";
import { Header, State } from "../components/common";
export function ModelInfo() {
    const model = useResource(api.model, "model");
    return (
        <>
            <Header
                eyebrow="MODEL REGISTRY"
                title="Model information"
                description="Artifact identity, provenance, thresholds, and measured evaluation status."
            />
            <State loading={model.loading} error={model.error}>
                {model.data && (
                    <>
                        <div className="provenance">
                            <strong>
                                {model.data.artifact_kind} ·{" "}
                                {model.data.model_mode.toUpperCase()}
                            </strong>
                            <span>{model.data.model_version}</span>
                        </div>
                        <section className="panel">
                            <h2>Evaluation</h2>
                            <p>
                                <a
                                    href={
                                        (import.meta.env.VITE_MLFLOW_URL as
                                            | string
                                            | undefined) ||
                                        "http://localhost:5001"
                                    }
                                >
                                    Open MLflow runs and registry →
                                </a>
                            </p>
                            {model.data.metrics ? (
                                <dl>
                                    {Object.entries(model.data.metrics).map(
                                        ([key, value]) => (
                                            <div key={key}>
                                                <dt>{key}</dt>
                                                <dd>{value}</dd>
                                            </div>
                                        ),
                                    )}
                                </dl>
                            ) : (
                                <p>PENDING: requires trained model artifact</p>
                            )}
                            <p>
                                Earlier reported model metrics: earlier run, not
                                reproduced.
                            </p>
                        </section>
                        <section className="panel">
                            <h2>Classification thresholds</h2>
                            {Object.entries(model.data.thresholds).map(
                                ([key, value]) => (
                                    <p key={key}>
                                        {key}: {value}
                                    </p>
                                ),
                            )}
                            <h2>Limitations</h2>
                            <ul>
                                {model.data.limitations.map((item) => (
                                    <li key={item}>{item}</li>
                                ))}
                            </ul>
                            <p>
                                CodeBERT and Devign are existing research.
                                CodeSentinel integrates learned signals, static
                                tools, and a decision framework.
                            </p>
                        </section>
                    </>
                )}
            </State>
        </>
    );
}
