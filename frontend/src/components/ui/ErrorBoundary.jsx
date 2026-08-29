import { Component } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

/**
 * Catches render errors in child trees so one panel failure does not blank the app.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary]", this.props.name || "panel", error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    const { hasError, error } = this.state;
    if (hasError) {
      if (this.props.fallback) {
        return typeof this.props.fallback === "function"
          ? this.props.fallback({ error, retry: this.handleRetry })
          : this.props.fallback;
      }

      return (
        <div
          role="alert"
          className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6 text-sm text-slate-300"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-white">
                {this.props.title || "Something went wrong"}
              </h3>
              <p className="mt-1 text-slate-400">
                {this.props.message ||
                  "This section could not be displayed. Other parts of the investigation workspace remain available."}
              </p>
              {import.meta.env.DEV && error?.message && (
                <p className="mt-2 font-mono text-xs text-amber-200/80">{error.message}</p>
              )}
              <button
                type="button"
                onClick={this.handleRetry}
                className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[#1F2937] bg-[#111827] px-3 py-1.5 text-xs text-slate-200 transition hover:border-cyan-500/40"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Try again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
