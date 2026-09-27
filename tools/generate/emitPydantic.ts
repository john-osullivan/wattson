// Emit Pydantic v2 models (py/wattson/etk/generated/models.py): the Python
// mirror of the Contract. `list[EtkTag]` enforces the closed tag enum per item;
// the note union is a shared-base discriminated union.
//
// Fidelity (v1): list `unique_items` and per-item patterns are carried by the
// JSON Schema and Zod layers only. Pydantic mirrors types plus length, pattern,
// and enum constraints, not item-uniqueness.

import type { Contract, Field, NamedType } from "./dialect.js";
import { topoSort } from "./dialect.js";
import { banner, oneLine, pascal, typeName } from "./common.js";

/** Map one IR field to a Python type expression. */
function pyType(f: Field): string {
  switch (f.kind) {
    case "string":
    case "date":
    case "uri":
      return "str";
    case "boolean":
      return "bool";
    case "enum":
      return `Literal[${f.values!.map((v) => JSON.stringify(v)).join(", ")}]`;
    case "string_list":
      return "list[str]";
    case "tags":
      return "list[EtkTag]";
    case "links":
      return "list[str]";
    case "relations":
      return "list[EtkRelation]";
    case "tasks":
      return "list[EtkTask]";
    case "list":
      return `list[${typeName(f.itemRef!)}]`;
    case "ref":
      return typeName(f.rawType);
  }
}

/** A Python raw-string regex literal: r"..." (r'...' if it holds a quote). */
function pyRegex(pattern: string): string {
  return pattern.includes('"') ? `r'${pattern}'` : `r"${pattern}"`;
}

const LISTISH = new Set<Field["kind"]>([
  "string_list",
  "tags",
  "links",
  "relations",
  "tasks",
  "list",
]);

/** Field(...) constraint args, or "" when the field needs no Field(). */
function pyFieldArgs(f: Field): string {
  const parts: string[] = [];
  if (f.kind === "string") {
    if (f.minLength !== undefined) parts.push(`min_length=${f.minLength}`);
    if (f.maxLength !== undefined) parts.push(`max_length=${f.maxLength}`);
    if (f.pattern !== undefined) parts.push(`pattern=${pyRegex(f.pattern)}`);
  } else if (f.kind === "date" || f.kind === "uri") {
    const pat = f.pattern ?? (f.kind === "date" ? "^\\d{4}-\\d{2}-\\d{2}$" : "^https?://\\S+$");
    parts.push(`pattern=${pyRegex(pat)}`);
  } else if (LISTISH.has(f.kind)) {
    if (f.minItems !== undefined) parts.push(`min_length=${f.minItems}`);
    if (f.maxItems !== undefined) parts.push(`max_length=${f.maxItems}`);
  }
  return parts.join(", ");
}

/** One annotated field line (required or Optional), at class-body indent. */
function pyFieldLine(f: Field): string {
  const t = pyType(f);
  const args = pyFieldArgs(f);
  if (f.required) return args ? `    ${f.name}: ${t} = Field(${args})` : `    ${f.name}: ${t}`;
  return args
    ? `    ${f.name}: ${t} | None = Field(default=None, ${args})`
    : `    ${f.name}: ${t} | None = None`;
}

/** A class docstring (first body line) from a type's description. */
function classDoc(description: string): string[] {
  return description ? [`    """${oneLine(description)}"""`] : [];
}

/** A plain-object named type -> a Pydantic BaseModel. */
function emitPyObject(t: NamedType): string[] {
  const L: string[] = [`class ${typeName(t.name)}(BaseModel):`];
  L.push(...classDoc(t.description));
  L.push(`    model_config = ConfigDict(extra="forbid")`);
  for (const f of t.fields) L.push(pyFieldLine(f));
  return L;
}

/** A discriminated union -> base model + member subclasses + Annotated alias. */
function emitPyUnion(t: NamedType): string[] {
  const baseName = `Etk${pascal(t.name)}Base`;
  const L: string[] = [`class ${baseName}(BaseModel):`];
  L.push(...classDoc(t.description));
  L.push(`    model_config = ConfigDict(extra="forbid")`);
  for (const f of t.baseFields) L.push(pyFieldLine(f));

  // include_tag is a cross-field rule, enforced once on the base (inherited).
  const includeTag = t.baseFields.find((f) => f.kind === "tags" && f.includeTag)?.includeTag;
  if (includeTag) {
    L.push(``, `    @model_validator(mode="after")`, `    def _check_type_tag(self) -> "${baseName}":`);
    L.push(`        required = ${JSON.stringify(includeTag)}.replace("{noteType}", str(self.${t.discriminator}))`);
    L.push(`        if required not in self.tags:`);
    L.push(`            raise ValueError(f"tags must include {required}")`);
    L.push(`        return self`);
  }
  L.push(``);

  for (const m of t.members) {
    const name = `Etk${pascal(m.name)}${pascal(t.name)}`;
    L.push(`class ${name}(${baseName}):`);
    L.push(...classDoc(m.description));
    L.push(`    ${t.discriminator}: Literal[${JSON.stringify(m.name)}]`);
    for (const f of m.fields) L.push(pyFieldLine(f));
    L.push(``);
  }

  const members = t.members.map((m) => `Etk${pascal(m.name)}${pascal(t.name)}`).join(", ");
  L.push(`Etk${pascal(t.name)} = Annotated[Union[${members}], Field(discriminator=${JSON.stringify(t.discriminator)})]`);
  return L;
}

export function emitPydantic(c: Contract): string {
  const note = c.types.find((t) => t.name === "note")!;
  const L: string[] = [
    ...banner("#"),
    ``,
    `from __future__ import annotations`,
    ``,
    `from typing import Annotated, Literal, Union`,
    ``,
    `from pydantic import BaseModel, ConfigDict, Field, model_validator`,
    ``,
    `ETK_VERSION = ${c.version}`,
    ``,
  ];

  L.push(`EtkTag = Literal[`);
  for (const tag of c.tags) L.push(`    ${JSON.stringify(tag)},`);
  L.push(`]`, ``);

  L.push(`EtkRelationType = Literal[${c.relationTypes.map((v) => JSON.stringify(v)).join(", ")}]`, ``);
  L.push(
    `class EtkRelation(BaseModel):`,
    `    model_config = ConfigDict(extra="forbid")`,
    `    type: EtkRelationType`,
    `    target: str`,
    ``,
  );
  L.push(
    `class EtkTask(BaseModel):`,
    `    model_config = ConfigDict(extra="forbid")`,
    `    text: str`,
    `    done: bool`,
    ``,
  );

  for (const t of topoSort(c.types)) L.push(...(t.isUnion ? emitPyUnion(t) : emitPyObject(t)), ``);
  return L.join("\n");
}
