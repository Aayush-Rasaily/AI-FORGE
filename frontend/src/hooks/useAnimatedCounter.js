import { useEffect, useState } from "react";

/**
 * Animates a number from 0 to target over duration ms.
 */
export function useAnimatedCounter(target, duration = 1200) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const goal = Number(target) || 0;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(goal * eased));
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }, [target, duration]);

  return value;
}
