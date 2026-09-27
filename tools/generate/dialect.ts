// Intermediate representation + strict interpretation of the hand-edited ETK
// field dialect (schemas/etk/*.yaml, documented in schemas/etk/README.md).
//
// This module is the fail-closed boundary: any dialect violation throws a
// DialectError so a malformed source can never silently produce a contract.

export type FieldKind =
  | "string"
  | "date"
  | "uri"
  | "boolean"
  | "enum"
  | "string_list"
  | "tags"
  | "links"
  | "relations"
  | "tasks"
  | "list"
  | "ref";

export interface Field {
  name: string;
  /** The `type:` value exactly as written in the YAML. */
  rawType: string;
  kind: FieldKind;
  required: boolean;
  description: string;
  /** notes.yaml only: where the template places the field. */
  render?: "frontmatter" | "body";
  // string-ish
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  values?: string[];
  // list-ish
  minItems?: number;
  maxItems?: number;
  uniqueItems?: boolean;
  itemPattern?: string;
  /** kind "list": the named type of each element. */
  itemRef?: string;
  // tags only
  includeTag?: string;
  sortItems?: boolean;
}

export interface UnionMember {
  name: string;
  description: string;
  fields: Field[];
}

export interface NamedType {
  name: string;
  description: string;
  isUnion: boolean;
  /** Plain-object fields (empty for unions). */
  fields: Field[];
  /** Union: the discriminator field name. */
  discriminator?: string;
  /** Union: fields shared by every member. */
  baseFields: Field[];
  /** Union members (empty for plain objects). */
  members: UnionMember[];
}

export interface AliasEntry {
  term: string;
  aliases: string[];
  tags: string[];
}

export interface Contract {
  version: number;
  types: NamedType[];
  /** Closed tag enum (no leading "#"). */
  tags: string[];
  /** Closed relation-type vocabulary (authored order). */
  relationTypes: string[];
  aliasIndex: AliasEntry[];
}

/** Everything the emitters need, loaded from schemas/etk/. */
export interface Sources {
  notes: { version: number; note: unknown };
  proposal: {
    version: number;
    proposal_source: unknown;
    proposal: unknown;
    proposal_envelope: unknown;
  };
  tags: string[];
  relationTypes: string[];
  aliasIndex: AliasEntry[];
}

export class DialectError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DialectError";
  }
}

const SCALAR_KINDS = new Set<string>([
  "string",
  "date",
  "uri",
  "boolean",
  "enum",
  "string_list",
  "tags",
  "links",
  "relations",
  "tasks",
  "list",
]);

function fail(message: string): never {
  throw new DialectError(message);
}

function asStr(value: unknown, where: string, key: string): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string") fail(`${where}: '${key}' must be a string`);
  return value;
}

function asInt(value: unknown, where: string, key: string): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isInteger(value)) {
    fail(`${where}: '${key}' must be an integer`);
  }
  return value;
}

function asBool(value: unknown, where: string, key: string): boolean | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "boolean") fail(`${where}: '${key}' must be a boolean`);
  return value;
}

function asStrList(value: unknown, where: string, key: string): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value) || value.some((v) => typeof v !== "string")) {
    fail(`${where}: '${key}' must be a list of strings`);
  }
  return value;
}

function interpretField(name: string, raw: unknown): Field {
  const where = `field '${name}'`;
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    fail(`${where}: must be a mapping`);
  }
  const r = raw as Record<string, unknown>;
  const rawType = r.type;
  if (typeof rawType !== "string" || rawType.length === 0) {
    fail(`${where}: missing string 'type'`);
  }
  const kind: FieldKind = SCALAR_KINDS.has(rawType) ? (rawType as FieldKind) : "ref";
  if (typeof r.required !== "boolean") fail(`${where}: 'required' must be a boolean`);

  const f: Field = {
    name,
    rawType,
    kind,
    required: r.required,
    description: typeof r.description === "string" ? r.description : "",
  };
  if (r.render !== undefined) {
    if (r.render !== "frontmatter" && r.render !== "body") {
      fail(`${where}: 'render' must be 'frontmatter' or 'body'`);
    }
    f.render = r.render;
  }
  f.minLength = asInt(r.min_length, where, "min_length");
  f.maxLength = asInt(r.max_length, where, "max_length");
  f.pattern = asStr(r.pattern, where, "pattern");
  f.values = asStrList(r.values, where, "values");
  f.minItems = asInt(r.min_items, where, "min_items");
  f.maxItems = asInt(r.max_items, where, "max_items");
  f.uniqueItems = asBool(r.unique_items, where, "unique_items");
  f.itemPattern = asStr(r.item_pattern, where, "item_pattern");
  f.includeTag = asStr(r.include_tag, where, "include_tag");
  f.sortItems = asBool(r.sort_items, where, "sort_items");
  if (r.item !== undefined) {
    if (typeof r.item !== "string") fail(`${where}: 'item' must be a string`);
    f.itemRef = r.item;
  }
  validateField(f, where);
  return f;
}

/** Enforce the dialect's type/constraint compatibility rules (fail-closed). */
function validateField(f: Field, where: string): void {
  const has = (v: unknown) => v !== undefined;
  const listish =
    f.kind === "string_list" ||
    f.kind === "tags" ||
    f.kind === "links" ||
    f.kind === "relations" ||
    f.kind === "tasks" ||
    f.kind === "list";

  if (f.kind === "enum" && !has(f.values)) fail(`${where}: 'enum' requires 'values'`);
  if (f.kind === "list" && !has(f.itemRef)) fail(`${where}: 'list' requires 'item'`);
  if (has(f.values) && f.kind !== "enum") fail(`${where}: 'values' is only valid for 'enum'`);
  if (has(f.itemRef) && f.kind !== "list") fail(`${where}: 'item' is only valid for 'list'`);
  if (has(f.includeTag) && f.kind !== "tags") fail(`${where}: 'include_tag' is only valid for 'tags'`);
  if (has(f.sortItems) && f.kind !== "tags") fail(`${where}: 'sort_items' is only valid for 'tags'`);
  if (has(f.itemPattern) && f.kind !== "string_list" && f.kind !== "links") {
    fail(`${where}: 'item_pattern' is only valid for 'string_list' or 'links'`);
  }
  const hasLen = has(f.minLength) || has(f.maxLength);
  if (hasLen && !listish && f.kind !== "string") {
    fail(`${where}: 'min_length'/'max_length' are only valid for 'string'`);
  }
  const hasListC = has(f.minItems) || has(f.maxItems) || has(f.uniqueItems) || has(f.itemPattern);
  if (hasListC && !listish) fail(`${where}: list constraints are only valid for list types`);
  if (f.kind === "boolean" && (hasLen || has(f.pattern) || hasListC)) {
    fail(`${where}: 'boolean' takes no constraints`);
  }
  if (f.kind === "ref" && (hasLen || has(f.pattern) || hasListC || has(f.values))) {
    fail(`${where}: references take no inline constraints`);
  }
}

function fieldsFrom(raw: unknown, where: string): Field[] {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    fail(`${where}: 'fields' must be a mapping`);
  }
  return Object.entries(raw as Record<string, unknown>).map(([name, f]) =>
    interpretField(name, f),
  );
}

function interpretObject(name: string, raw: unknown): NamedType {
  const where = `named type '${name}'`;
  if (typeof raw !== "object" || raw === null) fail(`${where}: must be a mapping`);
  const r = raw as Record<string, unknown>;
  if (r.discriminator !== undefined) {
    fail(`${where}: 'discriminator' is only valid for unions (use base_fields/members)`);
  }
  return {
    name,
    description: typeof r.description === "string" ? r.description : "",
    isUnion: false,
    fields: fieldsFrom(r.fields, where),
    baseFields: [],
    members: [],
  };
}

function interpretUnion(name: string, raw: unknown): NamedType {
  const where = `union '${name}'`;
  if (typeof raw !== "object" || raw === null) fail(`${where}: must be a mapping`);
  const r = raw as Record<string, unknown>;
  const discriminator = r.discriminator;
  if (typeof discriminator !== "string" || discriminator.length === 0) {
    fail(`${where}: missing string 'discriminator'`);
  }
  if (r.members === undefined || typeof r.members !== "object" || r.members === null) {
    fail(`${where}: missing 'members' mapping`);
  }
  const baseFields = fieldsFrom(r.base_fields, where);
  const members: UnionMember[] = Object.entries(r.members as Record<string, unknown>).map(
    ([mName, mRaw]) => {
      if (typeof mRaw !== "object" || mRaw === null) fail(`${where}: member '${mName}' must be a mapping`);
      const mr = mRaw as Record<string, unknown>;
      return {
        name: mName,
        description: typeof mr.description === "string" ? mr.description : "",
        fields: fieldsFrom(mr.fields ?? {}, `${where}: member '${mName}'`),
      };
    },
  );
  if (members.length === 0) fail(`${where}: at least one member is required`);
  return {
    name,
    description: typeof r.description === "string" ? r.description : "",
    isUnion: true,
    fields: [],
    discriminator,
    baseFields,
    members,
  };
}

/**
 * Interpret the loaded sources into a Contract. Validates that every
 * reference resolves to a known named type (fail-closed).
 */
export function interpret(s: Sources): Contract {
  const types: NamedType[] = [
    interpretUnion("note", s.notes.note),
    interpretObject("proposal_source", s.proposal.proposal_source),
    interpretObject("proposal", s.proposal.proposal),
    interpretObject("proposal_envelope", s.proposal.proposal_envelope),
  ];
  const names = new Set(types.map((t) => t.name));
  const allFields = (t: NamedType): Field[] => [
    ...t.fields,
    ...t.baseFields,
    ...t.members.flatMap((m) => m.fields),
  ];
  for (const t of types) {
    for (const f of allFields(t)) {
      if (f.kind === "ref" && !names.has(f.rawType)) {
        fail(`field '${f.name}' references unknown type '${f.rawType}'`);
      }
      if (f.kind === "list" && f.itemRef && !names.has(f.itemRef)) {
        fail(`field '${f.name}' item references unknown type '${f.itemRef}'`);
      }
    }
  }
  if (typeof s.notes.version !== "number") fail("'version' must be a number");
  return {
    version: s.notes.version,
    types,
    tags: s.tags,
    relationTypes: s.relationTypes,
    aliasIndex: s.aliasIndex,
  };
}

/** All fields of a type, in a stable order (plain, base, then member fields). */
export function allFields(t: NamedType): Field[] {
  return [...t.fields, ...t.baseFields, ...t.members.flatMap((m) => m.fields)];
}

/** Dependency order: referenced types are emitted before their referrers. */
export function topoSort(types: NamedType[]): NamedType[] {
  const byName = new Map(types.map((t) => [t.name, t]));
  const seen = new Set<string>();
  const order: NamedType[] = [];
  const visit = (t: NamedType) => {
    if (seen.has(t.name)) return;
    seen.add(t.name);
    for (const f of allFields(t)) {
      if (f.kind === "ref") byName.get(f.rawType) && visit(byName.get(f.rawType)!);
      if (f.kind === "list" && f.itemRef) byName.get(f.itemRef) && visit(byName.get(f.itemRef)!);
    }
    order.push(t);
  };
  for (const t of types) visit(t);
  return order;
}
