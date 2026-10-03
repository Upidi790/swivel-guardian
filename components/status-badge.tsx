export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const tone = normalized.includes("complete") || normalized.includes("release") || normalized.includes("trusted")
    ? "positive"
    : normalized.includes("cancel") || normalized.includes("high") || normalized.includes("escalat")
      ? "danger"
      : normalized.includes("pending") || normalized.includes("review") || normalized.includes("request")
        ? "warning"
        : "neutral";
  return <span className={`status-badge ${tone}`}>{status.replaceAll("_", " ")}</span>;
}
