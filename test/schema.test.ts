import { test } from "node:test";
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { Ajv2020 } from "ajv/dist/2020.js";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const GOLDEN_DIR = path.join(ROOT, "test", "golden");
const NOTE_SCHEMA = path.join(ROOT, "schemas", "generated", "json-schema", "etk-note.schema.json");

test("golden fixtures validate against the emitted JSON Schema", async (t) => {
  const schema = JSON.parse(await readFile(NOTE_SCHEMA, "utf8"));
  const ajv = new Ajv2020({ allErrors: true });
  const validate = ajv.compile(schema);
  const fixtures = (await readdir(GOLDEN_DIR)).filter((f) => f.endsWith(".json")).sort();
  assert.ok(fixtures.length >= 5, "no golden fixtures found");
  for (const fixture of fixtures) {
    await t.test(fixture, async () => {
      const json = JSON.parse(await readFile(path.join(GOLDEN_DIR, fixture), "utf8"));
      assert.equal(validate(json), true, `schema errors: ${JSON.stringify(validate.errors)}`);
    });
  }
});
