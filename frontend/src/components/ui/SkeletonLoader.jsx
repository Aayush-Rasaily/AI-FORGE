import { motion } from "framer-motion";

function Skeleton({ className = "" }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-gradient-to-r from-[#1F2937] via-[#374151] to-[#1F2937] bg-[length:200%_100%] ${className}`}
      style={{ animation: "shimmer 1.5s ease-in-out infinite" }}
    />
  );
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="glass-card rounded-xl p-6 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={`h-3 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
      ))}
    </div>
  );
}

export function SkeletonStat() {
  return (
    <div className="glass-card rounded-xl p-6">
      <Skeleton className="h-3 w-24 mb-3" />
      <Skeleton className="h-8 w-16 mb-2" />
      <Skeleton className="h-2 w-32" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div className="glass-card rounded-xl p-4 space-y-3">
      <Skeleton className="h-4 w-40 mb-4" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <Skeleton className="h-10 w-10 rounded-full shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-2 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="glass-card rounded-xl p-6">
      <Skeleton className="h-4 w-32 mb-6" />
      <Skeleton className="h-48 w-full rounded-lg" />
    </div>
  );
}

export default Skeleton;
