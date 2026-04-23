/**
 * Provider dispatcher — routes to droid or opencode based on ProviderName.
 */
import { runDroid } from "./droid.js";
import { runOpencode } from "./opencode.js";
export async function runWithProvider(provider, opts) {
    switch (provider) {
        case "droid":
            return runDroid(opts);
        case "opencode":
            return runOpencode(opts);
    }
}
//# sourceMappingURL=index.js.map