import { readFile, writeFile } from "node:fs/promises";
import { parseNote, renderNote, RenderError } from "./render.js";

const USAGE = "usage: etk render <note.json> [-o out.md]\n       etk validate <note.json>";

async function readJson(file: string): Promise<unknown> {
  const raw = await readFile(file, "utf8");
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new RenderError([{ path: "(file)", message: `not valid JSON: ${(err as Error).message}` }]);
  }
}

function printIssues(err: RenderError): void {
  console.error(err.message);
  for (const issue of err.issues) console.error(`  [${issue.path}] ${issue.message}`);
}

async function runRender(args: string[]): Promise<void> {
  const file = args[0];
  const outIdx = args.indexOf("-o");
  const out = outIdx >= 0 ? args[outIdx + 1] : undefined;
  if (!file || (outIdx >= 0 && !out)) {
    console.error(USAGE);
    process.exit(2);
  }
  const { markdown } = await renderNote(await readJson(file));
  if (out) {
    await writeFile(out, markdown, "utf8");
    console.log(`wrote ${out}`);
  } else {
    process.stdout.write(markdown);
  }
}

async function runValidate(args: string[]): Promise<void> {
  const file = args[0];
  if (!file) {
    console.error(USAGE);
    process.exit(2);
  }
  try {
    parseNote(await readJson(file));
    console.log(`valid: ${file}`);
  } catch (err) {
    if (err instanceof RenderError) {
      console.error(`invalid: ${file}`);
      for (const issue of err.issues) console.error(`  [${issue.path}] ${issue.message}`);
    }
    process.exit(1);
  }
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  const [command, ...rest] = argv;
  switch (command) {
    case "render":
      await runRender(rest);
      return;
    case "validate":
      await runValidate(rest);
      return;
    default:
      console.error(USAGE);
      process.exit(2);
  }
}

main().catch((err: unknown) => {
  if (err instanceof RenderError) {
    printIssues(err);
    process.exit(1);
  }
  throw err;
});
