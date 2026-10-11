import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { Ajv2020 } from "ajv/dist/2020.js";
import { zEtkProposalEnvelope } from "../src/generated/zod.js";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIR = path.join(ROOT, "test", "proposal");
const SCHEMA = path.join(ROOT, "schemas", "generated", "json-schema", "etk-proposal.schema.json");

async function load(name: string): Promise<unknown> {
  return JSON.parse(await readFile(path.join(DIR, name), "utf8"));
}

/** The Zod validator and the emitted JSON Schema must agree on the envelope. */
function ajvValidate() {
  const schema = JSON.parse(readFileSync(SCHEMA, "utf8"));
  return new Ajv2020({ allErrors: true }).compile(schema);
}

test("a nested proposal envelope passes Zod and the emitted JSON Schema", async () => {
  const envelope = await load("envelope-valid.json");
  const zod = zEtkProposalEnvelope.safeParse(envelope);
  assert.equal(zod.success, true, `zod errors: ${JSON.stringify(zod.error?.issues)}`);
  const validate = ajvValidate();
  assert.equal(validate(envelope), true, `schema errors: ${JSON.stringify(validate.errors)}`);
});

test("an invalid proposal envelope fails Zod and the emitted JSON Schema", async () => {
  const envelope = await load("envelope-invalid.json");
  assert.equal(zEtkProposalEnvelope.safeParse(envelope).success, false, "Zod accepted an invalid envelope");
  const validate = ajvValidate();
  assert.equal(validate(envelope), false, "JSON Schema accepted an invalid envelope");
});
