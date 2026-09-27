import { test } from "node:test";
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { renderNote } from "../src/render.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const GOLDEN_DIR = path.join(TEST_DIR, "golden");
const EXPECTED_DIR = path.join(GOLDEN_DIR, "expected");

/** CRLF-normalize and force exactly one trailing newline before comparing bytes. */
function normalize(md: string): string {
  return md.replace(/\r\n/g, "\n").replace(/\n+$/, "\n");
}

test("golden fixtures render to the expected Markdown", async (t) => {
  const fixtures = (await readdir(GOLDEN_DIR)).filter((f) => f.endsWith(".json")).sort();
  assert.ok(fixtures.length >= 5, `expected at least 5 golden fixtures, found ${fixtures.length}`);
  for (const fixture of fixtures) {
    await t.test(fixture, async () => {
      const json = JSON.parse(await readFile(path.join(GOLDEN_DIR, fixture), "utf8"));
      const expected = await readFile(path.join(EXPECTED_DIR, fixture.replace(/\.json$/, ".md")), "utf8");
      const { markdown } = await renderNote(json);
      assert.equal(normalize(markdown), normalize(expected), "rendered Markdown does not match the golden file");
    });
  }
});
