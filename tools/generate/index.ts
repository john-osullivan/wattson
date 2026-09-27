// CLI entry: interpret schemas/etk/*.yaml into the Contract and (re)generate
// the ETK contract artifacts, or --check them against what is committed.
//
//   tsx tools/generate/index.ts           # write artifacts
//   tsx tools/generate/index.ts --check   # fail (exit 1) on drift
//   tsx tools/generate/index.ts --out <d> # write under <d> instead

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { interpret } from "./dialect.js";
import type { Contract } from "./dialect.js";
import { loadSources } from "./sources.js";
import { emitTagSchema, emitNoteSchema, emitProposalSchema } from "./emitJsonSchema.js";
import { emitTypes } from "./emitTypescript.js";
import { emitZod } from "./emitZod.js";
import { emitRenderMeta } from "./emitRenderMeta.js";
import { emitPydantic } from "./emitPydantic.js";

// tools/generate/index.ts -> repo root is two levels up.
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");

const HELP = `Usage: tsx tools/generate/index.ts [options]

Regenerate the ETK contract artifacts from schemas/etk/*.yaml.

Options:
  --check            Compare generated output against committed files; exit 1 on drift.
  --only <group>     Generate only one group: 'schemas' (JSON Schema) or 'types' (TS/Zod/Pydantic).
  --out <dir>        Write to <dir> instead of the repo's canonical locations.
  --help, -h         Show this help.
`;

interface Args {
  check: boolean;
  out?: string;
  only?: "schemas" | "types";
}

function parseArgs(argv: string[]): Args {
  const args: Args = { check: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--check") args.check = true;
    else if (a === "--only") {
      const v = argv[++i];
      if (v !== "schemas" && v !== "types") throw new Error("--only must be 'schemas' or 'types'");
      args.only = v;
    } else if (a === "--out") {
      args.out = argv[++i];
      if (!args.out) throw new Error("--out requires a directory");
    } else if (a === "--help" || a === "-h") {
      process.stdout.write(HELP);
      process.exit(0);
    } else throw new Error(`unknown argument: ${a} (see --help)`);
  }
  return args;
}

/** The seven generated artifacts, as [relative path, in-memory content]. */
function buildFiles(c: Contract): Array<[string, string]> {
  return [
    ["schemas/generated/json-schema/etk-tag.schema.json", emitTagSchema(c)],
    ["schemas/generated/json-schema/etk-note.schema.json", emitNoteSchema(c)],
    ["schemas/generated/json-schema/etk-proposal.schema.json", emitProposalSchema(c)],
    ["src/generated/types.ts", emitTypes(c)],
    ["src/generated/zod.ts", emitZod(c)],
    ["src/generated/render-meta.ts", emitRenderMeta(c)],
    ["py/wattson/etk/generated/models.py", emitPydantic(c)],
  ];
}

/** JSON Schema artifacts live under schemas/; the rest are the language contracts. */
function filterByGroup(files: Array<[string, string]>, group: "schemas" | "types"): Array<[string, string]> {
  const isSchema = (rel: string) => rel.startsWith("schemas/generated/");
  return files.filter(([rel]) => (group === "schemas") === isSchema(rel));
}

/** Under --check: report drift without writing; exit 1 if any file differs. */
function checkFiles(base: string, files: Array<[string, string]>): void {
  const drifted: string[] = [];
  for (const [rel, content] of files) {
    const abs = join(base, rel);
    if (!existsSync(abs)) {
      drifted.push(`missing: ${rel}`);
    } else if (readFileSync(abs, "utf8") !== content) {
      drifted.push(`stale: ${rel}`);
    }
  }
  if (drifted.length > 0) {
    process.stderr.write(
      "generated artifacts out of date:\n  " + drifted.join("\n  ") + "\nrun: just generate\n",
    );
    process.exit(1);
  }
  process.stdout.write(`generated artifacts up to date (${files.length})\n`);
}

/** Write every artifact, creating parent directories as needed. */
function writeFiles(base: string, files: Array<[string, string]>): void {
  for (const [rel, content] of files) {
    const abs = join(base, rel);
    mkdirSync(dirname(abs), { recursive: true });
    writeFileSync(abs, content);
    process.stdout.write(`wrote ${rel}\n`);
  }
  process.stdout.write(`\ngenerated ${files.length} artifacts\n`);
}

function main(): void {
  const args = parseArgs(process.argv.slice(2));
  const contract = interpret(loadSources(join(ROOT, "schemas", "etk")));
  const base = args.out ? resolve(args.out) : ROOT;
  const files = args.only ? filterByGroup(buildFiles(contract), args.only) : buildFiles(contract);
  if (args.check) checkFiles(base, files);
  else writeFiles(base, files);
}

main();
