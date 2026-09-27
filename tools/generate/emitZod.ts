// Emit Zod v4 validators (src/generated/zod.ts). Schemas only; the matching
// types live in types.ts and are enforced to agree by render.ts's assignment
// (const note: EtkNote = zEtkNote.parse(...)).

import type { Contract, Field, NamedType } from "./dialect.js";
import { topoSort } from "./dialect.js";
import { banner, pascal, regexLit, typeName } from "./common.js";

/** array .min/.max from a field's list constraints (zod v4 has no .unique()). */
function listMod(f: Field): string {
  let e = "";
  if (f.minItems !== undefined) e += `.min(${f.minItems})`;
  if (f.maxItems !== undefined) e += `.max(${f.maxItems})`;
  return e;
}

/** Map one IR field to a Zod expression (before .optional()). */
function zodExpr(f: Field): string {
  switch (f.kind) {
    case "string": {
      let e = "z.string()";
      if (f.minLength !== undefined) e += `.min(${f.minLength})`;
      if (f.maxLength !== undefined) e += `.max(${f.maxLength})`;
      if (f.pattern !== undefined) e += `.regex(${regexLit(f.pattern)})`;
      return e;
    }
    case "date":
      return `z.string().regex(${regexLit(f.pattern ?? "^\\d{4}-\\d{2}-\\d{2}$")})`;
    case "uri":
      return `z.string().regex(${regexLit(f.pattern ?? "^https?://\\S+$")})`;
    case "boolean":
      return "z.boolean()";
    case "enum":
      return `z.enum([${f.values!.map((v) => JSON.stringify(v)).join(", ")}])`;
    case "string_list":
      return `z.array(z.string().min(1))${listMod(f)}`;
    case "tags":
      return `z.array(zEtkTag)${listMod(f)}`;
    case "links":
      return `z.array(z.string().min(1).regex(${regexLit(f.itemPattern ?? "^[^\\[\\]]+$")}))${listMod(f)}`;
    case "relations":
      return `z.array(zEtkRelation)${listMod(f)}`;
    case "tasks":
      return `z.array(zEtkTask)${listMod(f)}`;
    case "list":
      return `z.array(z${typeName(f.itemRef!)})${listMod(f)}`;
    case "ref":
      return `z${typeName(f.rawType)}`;
  }
}

function zodFieldLine(f: Field): string {
  let expr = zodExpr(f);
  if (!f.required) expr += ".optional()";
  return `  ${f.name}: ${expr},`;
}

function emitObject(t: NamedType): string[] {
  const L: string[] = [];
  L.push(`export const z${typeName(t.name)} = z.object({`);
  for (const f of t.fields) L.push(zodFieldLine(f));
  L.push(`}).strict();`);
  return L;
}

function emitUnion(t: NamedType): string[] {
  const L: string[] = [];
  const baseName = `z${pascal(t.name)}BaseShape`;
  L.push(`const ${baseName} = {`);
  for (const f of t.baseFields) L.push(zodFieldLine(f));
  L.push(`};`, "");

  for (const m of t.members) {
    const name = `z${pascal(m.name)}${pascal(t.name)}`;
    L.push(`export const ${name} = z.object({`);
    L.push(`  ...${baseName},`);
    L.push(`  ${t.discriminator}: z.literal(${JSON.stringify(m.name)}),`);
    for (const f of m.fields) L.push(zodFieldLine(f));
    L.push(`}).strict();`, "");
  }

  const memberSchemas = t.members.map((m) => `z${pascal(m.name)}${pascal(t.name)}`);
  L.push(
    `export const z${typeName(t.name)} = z.discriminatedUnion(${JSON.stringify(t.discriminator)}, [${memberSchemas.join(", ")}])`,
  );
  // include_tag is a cross-field rule (tags must contain type/<noteType>), so
  // it is enforced once on the union rather than per member.
  const includeTag = t.baseFields.find((f) => f.kind === "tags" && f.includeTag)?.includeTag;
  if (includeTag) {
    L.push(`  .superRefine((note, ctx) => {`);
    L.push(
      `    const required = ${JSON.stringify(includeTag)}.replace("{noteType}", note.${t.discriminator});`,
    );
    L.push(
      `    if (!(note.tags as string[]).includes(required)) ctx.addIssue({ code: "custom", path: ["tags"], message: "tags must include " + required });`,
    );
    L.push(`  });`);
  }
  return L;
}

export function emitZod(c: Contract): string {
  const note = c.types.find((t) => t.name === "note")!;
  const L: string[] = [
    ...banner("//"),
    "",
    `import { z } from "zod";`,
    "",
    `export const ETK_VERSION = ${c.version};`,
    "",
  ];

  L.push(`export const zEtkTag = z.enum([`);
  for (const tag of c.tags) L.push(`  ${JSON.stringify(tag)},`);
  L.push(`]);`, "");

  L.push(
    `export const zEtkRelationType = z.enum([${c.relationTypes.map((v) => JSON.stringify(v)).join(", ")}]);`,
    "",
  );
  L.push(
    `export const zNoteType = z.enum([${note.members.map((m) => JSON.stringify(m.name)).join(", ")}]);`,
    "",
  );
  L.push(
    `export const zEtkRelation = z.object({`,
    `  type: zEtkRelationType,`,
    `  target: z.string().min(1),`,
    `}).strict();`,
    "",
  );
  L.push(
    `export const zEtkTask = z.object({`,
    `  text: z.string().min(1),`,
    `  done: z.boolean(),`,
    `}).strict();`,
    "",
  );

  for (const t of topoSort(c.types)) {
    L.push(...(t.isUnion ? emitUnion(t) : emitObject(t)), "");
  }
  return L.join("\n");
}
