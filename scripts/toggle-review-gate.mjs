#!/usr/bin/env node

/**
 * CLI helper for toggling the stop review gate.
 *
 * Usage:
 *   node scripts/toggle-review-gate.mjs enable    # sets stopReviewGate: true
 *   node scripts/toggle-review-gate.mjs disable   # sets stopReviewGate: false
 *   node scripts/toggle-review-gate.mjs status    # prints current state
 */

import process from "node:process";
import { getConfig, setConfig } from "./lib/state.mjs";

function main() {
  const action = process.argv[2] ?? "status";

  switch (action) {
    case "enable": {
      setConfig("stopReviewGate", true);
      console.log("Stop review gate: enabled");
      console.log(
        "The Stop hook will now run a droid review before Claude stops.",
      );
      console.log(
        "If the review finds issues, the stop will be blocked until they are fixed.",
      );
      break;
    }
    case "disable": {
      setConfig("stopReviewGate", false);
      console.log("Stop review gate: disabled");
      break;
    }
    case "status": {
      const config = getConfig();
      console.log(
        `Stop review gate: ${config.stopReviewGate ? "enabled" : "disabled"}`,
      );
      break;
    }
    default: {
      console.error(`Unknown action: ${action}`);
      console.error("Usage: toggle-review-gate.mjs [enable|disable|status]");
      process.exitCode = 1;
    }
  }
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
