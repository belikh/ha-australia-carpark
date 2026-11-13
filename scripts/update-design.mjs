#!/usr/bin/env node
// Download the newest belikh/design release into vendor/design (gitignored) so the docs generator, the site and the PDF
// use the current design system. Nothing from the design system is committed to this repository.
//
//   node scripts/update-design.mjs                  newest release
//   node scripts/update-design.mjs --tag v1.3.3     a fixed release
//   node scripts/update-design.mjs --from <dir>     take the release files from a local folder (a build of scripts/release-assets.sh)
//   node scripts/update-design.mjs --if-missing     do nothing when vendor/design is already filled
//   node scripts/update-design.mjs --require-fonts  fail when the release has no jupiter-fonts.tgz (the site needs the SGI web fonts)
//
// Layout written:
//   vendor/design/node_modules/@belikh/jupiter-<tokens|graphics|ui|github|fonts>   the npm packages, unpacked
//   vendor/design/latex                                                              the jupiter-latex bundle (classes, fonts, graphics, scripts)
//   vendor/design/release.json                                                       { repo, tag, version, files }
// The generator finds them through vendor/design (or $JUPITER_DESIGN_DIR). They are unpacked folders and not npm
// dependencies because npm 12 refuses remote tarball URLs (allow-remote), and a download folder works the same with any npm.
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const REPO = process.env.JUPITER_DESIGN_REPO ?? "belikh/design";
const out = join(root, "vendor/design");
const args = process.argv.slice(2);
const opt = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : undefined; };
const flag = (n) => args.includes(n);

if (flag("--if-missing") && existsSync(join(out, "release.json"))) { console.log("vendor/design is present (run npm run update:design to refresh)"); process.exit(0); }

const PACKAGES = ["tokens", "graphics", "ui", "github", "fonts"];
const OPTIONAL = new Set(flag("--require-fonts") ? [] : ["fonts"]);
const UA = { "user-agent": "jupiter-docs-update-design" };

async function retry(fn, what) {
  let last;
  for (let i = 1; i <= 4; i++) { try { return await fn(); } catch (e) { if (e.fatal) throw e; last = e; await new Promise((r) => setTimeout(r, i * 2000)); } }
  throw new Error(`${what}: ${last.message}`);
}
async function latestTag() {
  const r = await retry(() => fetch(`https://github.com/${REPO}/releases/latest`, { redirect: "manual", headers: UA, signal: AbortSignal.timeout(30000) }), "latest release");
  const m = /\/releases\/tag\/([^/?#]+)/.exec(r.headers.get("location") ?? "");
  if (!m) throw new Error(`${REPO}: no release found`);
  return decodeURIComponent(m[1]);
}
async function download(tag, file) {
  return retry(async () => {
    const r = await fetch(`https://github.com/${REPO}/releases/download/${tag}/${file}`, { headers: UA, signal: AbortSignal.timeout(90000) });
    if (r.status === 404) throw Object.assign(new Error("not found"), { fatal: true });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return Buffer.from(await r.arrayBuffer());
  }, `${tag}/${file}`);
}
const local = opt("--from");
const fetchFile = async (tag, file) => {
  if (!local) return download(tag, file);
  const f = join(local, file); if (!existsSync(f)) throw Object.assign(new Error("not found"), { fatal: true }); return readFileSync(f);
};

const work = mkdtempSync(join(tmpdir(), "jpdesign-"));
try {
  const tag = local ? "local" : opt("--tag") ?? process.env.DESIGN_TAG ?? (await latestTag());
  const sums = new Map();
  try { for (const l of (await fetchFile(tag, "SHA256SUMS")).toString().split("\n")) { const m = /^([0-9a-f]{64})\s+\*?(.+)$/.exec(l); if (m) sums.set(m[2], m[1]); } } catch { console.warn("warning: no SHA256SUMS in the release; files are not verified"); }

  const files = [...PACKAGES.map((n) => [n, `jupiter-${n}.tgz`]), ["latex", "jupiter-latex.tgz"]];
  const stage = join(work, "stage"); mkdirSync(join(stage, "node_modules/@belikh"), { recursive: true });
  const got = {};
  for (const [name, file] of files) {
    let buf;
    try { buf = await fetchFile(tag, file); }
    catch (e) {
      if (e.fatal && OPTIONAL.has(name)) { console.warn(`warning: ${REPO} ${tag} has no ${file}; the site falls back to system fonts. Needs a design release that ships the fonts.`); continue; }
      throw new Error(`${file} (${REPO} ${tag}): ${e.message}`);
    }
    const sum = createHash("sha256").update(buf).digest("hex");
    if (sums.has(file) && sums.get(file) !== sum) throw new Error(`${file}: checksum mismatch`);
    const tgz = join(work, file); writeFileSync(tgz, buf);
    const dest = name === "latex" ? join(stage, "latex") : join(stage, "node_modules/@belikh", `jupiter-${name}`);
    mkdirSync(dest, { recursive: true });
    const t = spawnSync("tar", ["-xzf", tgz, "-C", dest, "--strip-components=1"], { encoding: "utf8" });
    if (t.status !== 0) throw new Error(`${file}: tar failed: ${t.stderr}`);
    got[file] = sum.slice(0, 12);
  }
  const tokens = JSON.parse(readFileSync(join(stage, "node_modules/@belikh/jupiter-tokens/package.json"), "utf8"));
  const resolvedTag = local ? `v${tokens.version}` : tag;
  writeFileSync(join(stage, "release.json"), JSON.stringify({ repo: REPO, tag: resolvedTag, version: tokens.version, source: local ? "local" : "github", files: got }, null, 2) + "\n");
  rmSync(out, { recursive: true, force: true }); mkdirSync(dirname(out), { recursive: true });
  cpSync(stage, out, { recursive: true });
  console.log(`design system ${REPO} ${resolvedTag} (${Object.keys(got).length} files) -> vendor/design`);
} finally { rmSync(work, { recursive: true, force: true }); }
