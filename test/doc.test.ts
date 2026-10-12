import { test } from "node:test";
import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { renderDoc } from "../src/render-doc.js";
import { DocRenderError } from "../src/render-doc.js";

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url));
const DOC_DIR = path.join(TEST_DIR, "doc");

/** CRLF-normalize and force exactly one trailing newline before comparing bytes. */
function normalize(md: string): string {
  return md.replace(/\r\n/g, "\n").replace(/\n+$/, "\n");
}

test("machine documents render to the expected Markdown via their Knap template", async (t) => {
  for (const [docName, template] of [["digest", "digest"], ["proposal", "proposal"]] as const) {
    const dir = path.join(DOC_DIR, docName);
    const expectedDir = path.join(dir, "expected");
    const fixtures = (await readdir(dir)).filter((f) => f.endsWith(".json")).sort();
    assert.ok(fixtures.length >= 2, `expected at least 2 ${docName} fixtures, found ${fixtures.length}`);
    for (const fixture of fixtures) {
      await t.test(`${docName}/${fixture}`, async () => {
        const context = JSON.parse(await readFile(path.join(dir, fixture), "utf8"));
        const expected = await readFile(
          path.join(expectedDir, fixture.replace(/\.json$/, ".md")),
          "utf8",
        );
        const markdown = await renderDoc(template, context);
        assert.equal(normalize(markdown), normalize(expected), "rendered Markdown does not match the golden file");
      });
    }
  }
});

test("renderDoc rejects bad template names and non-object contexts", async () => {
  await assert.rejects(() => renderDoc("../../etc/passwd", {}), DocRenderError);
  await assert.rejects(() => renderDoc("does-not-exist", {}), DocRenderError);
  await assert.rejects(() => renderDoc("digest", ["not", "an", "object"]), DocRenderError);
  await assert.rejects(() => renderDoc("digest", null), DocRenderError);
});
