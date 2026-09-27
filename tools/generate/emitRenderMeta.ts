// Emit render metadata (src/generated/render-meta.ts): per note type, the
// ordered frontmatter field names (assembled into the `fm` object) and body
// field names, plus the template file. render.ts is data-driven from this so
// notes.yaml stays the single source of truth for field placement (decision D4).

import type { Contract } from "./dialect.js";
import { banner } from "./common.js";

export function emitRenderMeta(c: Contract): string {
  const note = c.types.find((t) => t.name === "note")!;
  const L: string[] = [
    ...banner("//"),
    "",
    `export interface NoteRenderMeta {`,
    `  noteType: string;`,
    `  /** Template file under templates/. */`,
    `  template: string;`,
    `  /** Frontmatter field names, in declaration order (builds the fm object). */`,
    `  frontmatter: string[];`,
    `  /** Body field names, in declaration order. */`,
    `  body: string[];`,
    `}`,
    ``,
    `export const NOTE_RENDER_META: Record<string, NoteRenderMeta> = {`,
  ];

  for (const m of note.members) {
    const all = [...note.baseFields, ...m.fields];
    const fm = all.filter((f) => f.render === "frontmatter").map((f) => f.name);
    const body = all.filter((f) => f.render === "body").map((f) => f.name);
    L.push(`  ${JSON.stringify(m.name)}: {`);
    L.push(`    noteType: ${JSON.stringify(m.name)},`);
    L.push(`    template: ${JSON.stringify(`${m.name}.knap.md`)},`);
    L.push(`    frontmatter: [${fm.map((n) => JSON.stringify(n)).join(", ")}],`);
    L.push(`    body: [${body.map((n) => JSON.stringify(n)).join(", ")}],`);
    L.push(`  },`);
  }
  L.push(`};`);
  return L.join("\n");
}
