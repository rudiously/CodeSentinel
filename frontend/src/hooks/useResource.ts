import { useEffect, useState } from "react";
export function useResource<T>(loader: () => Promise<T>, key: string) {
    const [data, setData] = useState<T>();
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        let active = true;
        setLoading(true);
        setError("");
        void loader()
            .then((value) => {
                if (active) setData(value);
            })
            .catch((reason: unknown) => {
                if (active)
                    setError(
                        reason instanceof Error
                            ? reason.message
                            : "Request failed",
                    );
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, [key]); // loader intentionally keyed by stable endpoint string
    return { data, error, loading };
}
