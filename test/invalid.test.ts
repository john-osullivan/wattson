import { test } from "node:test";
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { parseNote, RenderError } from "../src/render.js";

const INVALID_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "invalid");

/** Each invalid fixture must produce an issue at this path whose message contains this text. */
const CASES: Array<{ file: string; path: string; messageIncludes: string }> = [
  { file: "unknown-tag.json", path: "tags.1", messageIncludes: "Invalid option" },
  { file: "missing-type-tag.json", path: "tags", messageIncludes: "tags must include type/atom" },
  { file: "bad-relation-type.json", path: "relations.0.type", messageIncludes: "Invalid option" },
  { file: "empty-title.json", path: "title", messageIncludes: "Too small" },
  { file: "bad-date.json", path: "created", messageIncludes: "must match pattern" },
  { file: "unknown-note-type.json", path: "noteType", messageIncludes: "Invalid discriminator value" },
  { file: "extra-field.json", path: "(root)", messageIncludes: "Unrecognized key" },
  { file: "bad-url.json", path: "url", messageIncludes: "must match pattern" },
  { file: "wrong-type-tag.json", path: "tags", messageIncludes: "tags must include type/project" },
  { file: "duplicate-relation.json", path: "relations", messageIncludes: "items must be unique" },
  { file: "duplicate-tag.json", path: "tags", messageIncludes: "items must be unique" },
];

test("invalid fixtures fail validation with the expected issue", async (t) => {
  const onDisk = (await readdir(INVALID_DIR)).filter((f) => f.endsWith(".json")).sort();
  const expectedFiles = CASES.map((c) => c.file).sort();
  assert.deepEqual(onDisk, expectedFiles, "invalid fixtures on disk do not match the CASES table");
  for (const c of CASES) {
    await t.test(c.file, async () => {
      const json = JSON.parse(await readFile(path.join(INVALID_DIR, c.file), "utf8"));
      let caught: unknown;
      try {
        parseNote(json);
      } catch (err) {
        caught = err;
      }
      assert.ok(caught instanceof RenderError, `expected RenderError, got ${String(caught)}`);
      const issue = (caught as RenderError).issues.find((i) => i.path === c.path);
      assert.ok(issue, `no issue at path "${c.path}"; got paths: ${(caught as RenderError).issues.map((i) => i.path).join(", ")}`);
      assert.ok(issue.message.includes(c.messageIncludes), `message ${JSON.stringify(issue.message)} missing ${JSON.stringify(c.messageIncludes)}`);
    });
  }
});
