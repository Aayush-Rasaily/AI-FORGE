import React from "react";
import { AlertOctagon } from "lucide-react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-red-500/20 bg-red-500/5">
          <AlertOctagon className="h-12 w-12 text-red-500 mb-4" />
          <h2 className="text-lg font-bold text-white mb-2">Unexpected Render Error</h2>
          <p className="text-sm text-slate-400">
            An unexpected error occurred while displaying the analysis.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
