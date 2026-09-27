// Emit pure TypeScript types (src/generated/types.ts). No runtime code, no
// imports: this file is the type-level mirror of the Contract.

import type { Contract, Field, NamedType } from "./dialect.js";
import { topoSort } from "./dialect.js";
import { banner, oneLine, pascal, typeName } from "./common.js";

/** Map one IR field to a TS type expression. */
function tsType(f: Field): string {
  switch (f.kind) {
    case "string":
    case "date":
    case "uri":
      return "string";
    case "boolean":
      return "boolean";
    case "enum":
      return f.values!.map((v) => JSON.stringify(v)).join(" | ");
    case "string_list":
      return "string[]";
    case "tags":
      return "EtkTag[]";
    case "links":
      return "string[]";
    case "relations":
      return "EtkRelation[]";
    case "tasks":
      return "EtkTask[]";
    case "list":
      return `${typeName(f.itemRef!)}[]`;
    case "ref":
      return typeName(f.rawType);
  }
}

function fieldLines(f: Field): string[] {
  const lines: string[] = [];
  if (f.description) lines.push(`  /** ${oneLine(f.description)} */`);
  lines.push(`  ${f.name}${f.required ? "" : "?"}: ${tsType(f)};`);
  return lines;
}

function docLines(t: NamedType): string[] {
  return t.description ? [`/** ${oneLine(t.description)} */`] : [];
}

function emitObject(t: NamedType): string[] {
  const L: string[] = [...docLines(t)];
  L.push(`export interface ${typeName(t.name)} {`);
  for (const f of t.fields) L.push(...fieldLines(f));
  L.push(`}`);
  return L;
}

function emitUnion(t: NamedType): string[] {
  const L: string[] = [];
  const baseName = `Etk${pascal(t.name)}Base`;
  L.push(...docLines(t));
  L.push(`export interface ${baseName} {`);
  for (const f of t.baseFields) L.push(...fieldLines(f));
  L.push(`}`, "");
  for (const m of t.members) {
    const name = `${pascal(m.name)}${pascal(t.name)}`;
    L.push(`export interface ${name} extends ${baseName} {`);
    L.push(`  /** Discriminator. */`);
    L.push(`  noteType: ${JSON.stringify(m.name)};`);
    for (const f of m.fields) L.push(...fieldLines(f));
    L.push(`}`, "");
  }
  const memberNames = t.members.map((m) => `${pascal(m.name)}${pascal(t.name)}`);
  L.push(`export type ${typeName(t.name)} = ${memberNames.join(" | ")};`);
  return L;
}

export function emitTypes(c: Contract): string {
  const note = c.types.find((t) => t.name === "note")!;
  const L: string[] = [...banner("//"), "", `export const ETK_VERSION = ${c.version};`, ""];

  L.push(`export type EtkTag =`);
  for (const tag of c.tags) L.push(`  | ${JSON.stringify(tag)}`);
  L.push(";", "");

  L.push(
    `export type EtkRelationType = ${c.relationTypes.map((v) => JSON.stringify(v)).join(" | ")};`,
    "",
  );
  L.push(`export interface EtkRelation {`, `  type: EtkRelationType;`, `  target: string;`, `}`, "");
  L.push(`export interface EtkTask {`, `  text: string;`, `  done: boolean;`, `}`, "");
  L.push(
    `export type NoteType = ${note.members.map((m) => JSON.stringify(m.name)).join(" | ")};`,
    "",
  );

  for (const t of topoSort(c.types)) {
    L.push(...(t.isUnion ? emitUnion(t) : emitObject(t)), "");
  }
  return L.join("\n");
}
