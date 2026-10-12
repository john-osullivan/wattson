import { readFile, writeFile } from "node:fs/promises";
import { parseNote, renderNote, RenderError } from "./render.js";
import { renderDoc, DocRenderError } from "./render-doc.js";

const USAGE =
  "usage: etk render <note.json> [-o out.md]\n" +
  "       etk validate <note.json>\n" +
  "       etk render-doc <context.json> --template <name> [-o out.md]";

async function readJson(file: string): Promise<unknown> {
  let raw: string;
  try {
    raw = await readFile(file, "utf8");
  } catch {
    throw new DocRenderError(`cannot read ${file}`);
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new DocRenderError(`not valid JSON in ${file}: ${(err as Error).message}`);
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
  let json: unknown;
  try {
    json = await readJson(file);
  } catch (err) {
    if (err instanceof DocRenderError) {
      throw new RenderError([{ path: "(file)", message: (err as Error).message }]);
    }
    throw err;
  }
  const { markdown } = await renderNote(json);
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
    } else if (err instanceof DocRenderError) {
      console.error(err.message);
    }
    process.exit(1);
  }
}

async function runRenderDoc(args: string[]): Promise<void> {
  let file: string | undefined;
  let template: string | undefined;
  let out: string | undefined;
  let outFlag = false;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--template") {
      template = args[++i];
    } else if (arg === "-o") {
      out = args[++i];
      outFlag = true;
    } else if (arg.startsWith("-")) {
      throw new DocRenderError(`unknown option: ${arg}`);
    } else if (!file) {
      file = arg;
    } else {
      throw new DocRenderError(`unexpected argument: ${arg}`);
    }
  }
  if (!file || !template || (outFlag && !out)) {
    console.error(USAGE);
    process.exit(2);
  }
  const markdown = await renderDoc(template, await readJson(file));
  if (out) {
    await writeFile(out, markdown, "utf8");
    console.log(`wrote ${out}`);
  } else {
    process.stdout.write(markdown);
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
    case "render-doc":
      await runRenderDoc(rest);
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
  if (err instanceof DocRenderError) {
    console.error(err.message);
    process.exit(1);
  }
  throw err;
});
