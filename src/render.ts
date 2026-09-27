import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { createEngine, standardFilters } from "knap";
import { zEtkNote } from "./generated/zod.js";
import type { EtkNote } from "./generated/types.js";
import { NOTE_RENDER_META } from "./generated/render-meta.js";

const TEMPLATE_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "templates");
const engine = createEngine({ filters: standardFilters });

export interface RenderIssue {
  path: string;
  message: string;
}

/** Validation failure carrying the structured Zod issues (nothing was rendered). */
export class RenderError extends Error {
  readonly issues: RenderIssue[];
  constructor(issues: RenderIssue[]) {
    super("Invalid ETK note: " + issues.map((i) => `[${i.path}] ${i.message}`).join("; "));
    this.name = "RenderError";
    this.issues = issues;
  }
}

/** Validate unknown input against the ETK note contract; throw RenderError on failure. */
export function parseNote(json: unknown): EtkNote {
  const result = zEtkNote.safeParse(json);
  if (!result.success) {
    const issues = result.error.issues.map((i) => ({
      path: i.path.join(".") || "(root)",
      message: i.message,
    }));
    throw new RenderError(issues);
  }
  return result.data as EtkNote;
}

/** Build the frontmatter object in render-meta key order: tags sorted, absent optionals skipped. */
export function buildFm(note: EtkNote): Record<string, unknown> {
  const meta = NOTE_RENDER_META[note.noteType];
  const fm: Record<string, unknown> = {};
  for (const key of meta.frontmatter) {
    const value = (note as unknown as Record<string, unknown>)[key];
    if (value === undefined) continue;
    fm[key] = key === "tags" ? [...(value as string[])].sort() : value;
  }
  return fm;
}

/** Type-checked variables handed to Knap: the note's own fields plus the assembled fm object. */
function buildVariables(note: EtkNote): Record<string, unknown> {
  return { ...(note as unknown as Record<string, unknown>), fm: buildFm(note) };
}

/** Validate then deterministically render a note to Markdown. */
export async function renderNote(json: unknown): Promise<{ markdown: string; note: EtkNote }> {
  const note = parseNote(json);
  const meta = NOTE_RENDER_META[note.noteType];
  const template = await readFile(path.join(TEMPLATE_DIR, meta.template), "utf8");
  const markdown = await engine.renderOrThrow(template, { variables: buildVariables(note) });
  return { markdown, note };
}
