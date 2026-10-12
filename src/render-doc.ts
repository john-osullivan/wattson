import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { createEngine, standardFilters } from "knap";

const TEMPLATE_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "templates");
const engine = createEngine({ filters: standardFilters });
const NAME_RE = /^[a-z0-9][a-z0-9-]*$/i;

/** Rendering failure for machine documents (no ETK note contract involved). */
export class DocRenderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DocRenderError";
  }
}

/**
 * Render a machine document (vault digest, proposal envelope, ...) with a named
 * Knap template from templates/<name>.knap.md. No ETK validation: the context
 * object's top-level keys are the template variables.
 */
export async function renderDoc(name: string, context: unknown): Promise<string> {
  if (typeof name !== "string" || !NAME_RE.test(name)) {
    throw new DocRenderError(`invalid template name: ${JSON.stringify(name)}`);
  }
  if (typeof context !== "object" || context === null || Array.isArray(context)) {
    throw new DocRenderError("context must be a JSON object; its top-level keys become the template variables");
  }
  let template: string;
  try {
    template = await readFile(path.join(TEMPLATE_DIR, `${name}.knap.md`), "utf8");
  } catch {
    throw new DocRenderError(`template not found: templates/${name}.knap.md`);
  }
  return engine.renderOrThrow(template, { variables: context as Record<string, unknown> });
}
