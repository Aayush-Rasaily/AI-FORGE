import { motion } from "framer-motion";
import { CheckCircle } from "lucide-react";

function SignalList({ signals = [], title = "Detected Signals" }) {
  if (!signals || signals.length === 0) {
    return (
      <p className="text-sm text-slate-500 italic">
        No forensic signals detected.
      </p>
    );
  }

  return (
    <div>
      <h5 className="mb-3 text-sm font-semibold text-slate-300">{title}</h5>
      <ul className="space-y-2">
        {signals.map((signal, index) => (
          <motion.li
            key={index}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08 }}
            className="flex items-start gap-2.5 rounded-xl border border-orange-500/20 bg-orange-500/5 px-4 py-3 text-sm text-orange-200"
          >
            <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-orange-400" />
            <span>{signal}</span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

export default SignalList;
