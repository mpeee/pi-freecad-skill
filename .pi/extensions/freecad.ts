/**
 * FreeCAD pi Extension
 *
 * Provides direct tools for the LLM to communicate with FreeCAD without
 * going through a bash wrapper, and manages a persistent script library
 * with project-local and global scopes.
 *
 * Tools registered:
 *   freecad_run          — execute Python code in FreeCAD
 *   freecad_screenshot   — capture 3D view as PNG
 *   freecad_script_save  — save a script to the library
 *   freecad_script_list  — list available scripts
 *   freecad_script_run   — execute a named script from the library
 *   freecad_script_show  — print source code of a named script
 *   freecad_script_delete— delete a script from the library
 *
 * Commands:
 *   /freecad:status      — check connection and show library stats
 *   /freecad:setup       — interactive setup wizard
 *
 * Script library locations:
 *   project:  <cwd>/fc-scripts/          (tracked per project, e.g. in git)
 *   global:   ~/.pi/freecad-scripts/     (cross-project reusable scripts)
 *
 * Environment variables:
 *   FC_HOST   — FreeCAD host (auto-detected in WSL2 if unset)
 *   FC_PORT   — FreeCAD port (default: 7978)
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import * as net from "node:net";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FreeCADResponse {
  result: unknown;
  output: string;
  stderr: string;
  error: string | null;
}

interface ScriptEntry {
  name: string;
  description: string;
  file: string;
  scope: "project" | "global";
  created: string;
  modified: string;
}

// ─── Connection ───────────────────────────────────────────────────────────────

function detectHost(): string {
  if (process.env.FC_HOST) return process.env.FC_HOST;
  // WSL2: try resolv.conf nameserver (gateway = Windows host)
  try {
    const resolv = fs.readFileSync("/etc/resolv.conf", "utf8");
    const match = resolv.match(/^nameserver\s+(\S+)/m);
    if (match?.[1] && match[1] !== "127.0.0.1") return match[1];
  } catch {
    // not on Linux/WSL2
  }
  // Fallback: host.docker.internal (Docker Desktop / some WSL2 configs)
  return "host.docker.internal";
}

function getPort(): number {
  return parseInt(process.env.FC_PORT ?? "7978", 10);
}

function sendToFreeCAD(
  host: string,
  port: number,
  code: string,
  timeoutMs = 15000
): Promise<FreeCADResponse> {
  return new Promise((resolve, reject) => {
    const client = net.createConnection({ host, port }, () => {
      client.write(JSON.stringify({ code }) + "\n");
    });

    let buffer = "";
    client.on("data", (chunk) => {
      buffer += chunk.toString();
      if (buffer.includes("\n")) {
        client.destroy();
        try {
          resolve(JSON.parse(buffer.trim()) as FreeCADResponse);
        } catch (e) {
          reject(new Error(`Invalid JSON from FreeCAD: ${buffer.slice(0, 200)}`));
        }
      }
    });

    client.on("error", (err) => reject(new Error(`Connection to FreeCAD failed: ${err.message}`)));
    client.setTimeout(timeoutMs, () => {
      client.destroy();
      reject(new Error(`FreeCAD connection timed out after ${timeoutMs / 1000}s`));
    });
  });
}

function formatResponse(resp: FreeCADResponse): string {
  const parts: string[] = [];
  if (resp.error) {
    parts.push(`ERROR:\n${resp.error.trim()}`);
  }
  if (resp.output?.trim()) {
    parts.push(`OUTPUT:\n${resp.output.trim()}`);
  }
  if (resp.stderr?.trim()) {
    parts.push(`STDERR:\n${resp.stderr.trim()}`);
  }
  if (resp.result !== null && resp.result !== undefined) {
    parts.push(`RESULT: ${JSON.stringify(resp.result)}`);
  }
  return parts.length > 0 ? parts.join("\n\n") : "(no output)";
}

// ─── Script Library ───────────────────────────────────────────────────────────

const INDEX_FILE = "_index.json";

function getScriptDir(scope: "project" | "global", cwd: string): string {
  return scope === "global"
    ? path.join(os.homedir(), ".pi", "freecad-scripts")
    : path.join(cwd, "fc-scripts");
}

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function loadIndex(dir: string): ScriptEntry[] {
  const indexPath = path.join(dir, INDEX_FILE);
  if (!fs.existsSync(indexPath)) return [];
  try {
    return JSON.parse(fs.readFileSync(indexPath, "utf8")) as ScriptEntry[];
  } catch {
    return [];
  }
}

function saveIndex(dir: string, index: ScriptEntry[]): void {
  fs.writeFileSync(
    path.join(dir, INDEX_FILE),
    JSON.stringify(index, null, 2),
    "utf8"
  );
}

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function saveScript(
  name: string,
  description: string,
  code: string,
  scope: "project" | "global",
  cwd: string
): { file: string; dir: string } {
  const dir = getScriptDir(scope, cwd);
  ensureDir(dir);

  const slug = slugify(name);
  const file = `${slug}.py`;
  const filePath = path.join(dir, file);
  fs.writeFileSync(filePath, code, "utf8");

  const index = loadIndex(dir);
  const now = new Date().toISOString();
  const existing = index.findIndex((e) => e.name === slug);
  const entry: ScriptEntry = {
    name: slug,
    description,
    file,
    scope,
    created: existing >= 0 ? index[existing]!.created : now,
    modified: now,
  };
  if (existing >= 0) {
    index[existing] = entry;
  } else {
    index.push(entry);
  }
  saveIndex(dir, index);
  return { file, dir };
}

function findScript(
  name: string,
  cwd: string
): { entry: ScriptEntry; dir: string; code: string } | null {
  const slug = slugify(name);
  // Check project first, then global
  for (const scope of ["project", "global"] as const) {
    const dir = getScriptDir(scope, cwd);
    const index = loadIndex(dir);
    const entry = index.find((e) => e.name === slug);
    if (entry) {
      const filePath = path.join(dir, entry.file);
      if (fs.existsSync(filePath)) {
        const code = fs.readFileSync(filePath, "utf8");
        return { entry, dir, code };
      }
    }
  }
  return null;
}

function listAllScripts(cwd: string): ScriptEntry[] {
  const seen = new Set<string>();
  const results: ScriptEntry[] = [];
  // project first — takes precedence over global on name collision
  for (const scope of ["project", "global"] as const) {
    const dir = getScriptDir(scope, cwd);
    const index = loadIndex(dir);
    for (const e of index) {
      if (!seen.has(e.name)) {
        seen.add(e.name);
        results.push({ ...e, scope });
      }
    }
  }
  return results;
}

// ─── Extension ────────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // ── Status footer ──────────────────────────────────────────────────────────

  async function updateStatus(ctx: ExtensionContext) {
    const host = detectHost();
    const port = getPort();
    try {
      await sendToFreeCAD(host, port, "'ping'", 3000);
      ctx.ui.setStatus("freecad", `⬡ FreeCAD ${host}:${port}`);
    } catch {
      ctx.ui.setStatus("freecad", `⬡ FreeCAD offline`);
    }
  }

  pi.on("session_start", async (_event, ctx) => {
    // Fire-and-forget: don't block startup if FreeCAD is offline
    updateStatus(ctx).catch(() => {
      ctx.ui.setStatus("freecad", "⬡ FreeCAD offline");
    });
  });

  // ── /freecad:status command ────────────────────────────────────────────────

  pi.registerCommand("freecad:status", {
    description: "Check FreeCAD connection and show script library stats",
    handler: async (_args, ctx) => {
      const host = detectHost();
      const port = getPort();

      let connectionMsg: string;
      try {
        const resp = await sendToFreeCAD(host, port, "'.'.join(FreeCAD.Version()[:2])", 5000);
        const version = resp.result ?? "?";
        connectionMsg = `✓ Connected — FreeCAD ${version} at ${host}:${port}`;
        ctx.ui.setStatus("freecad", `⬡ FreeCAD ${host}:${port}`);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        connectionMsg = `✗ Offline — ${msg}`;
        ctx.ui.setStatus("freecad", `⬡ FreeCAD offline`);
      }

      const scripts = listAllScripts(ctx.cwd);
      const projectCount = scripts.filter((s) => s.scope === "project").length;
      const globalCount = scripts.filter((s) => s.scope === "global").length;

      ctx.ui.notify(
        [
          connectionMsg,
          `Scripts — project: ${projectCount}, global: ${globalCount}`,
          `Project dir: ${getScriptDir("project", ctx.cwd)}`,
          `Global dir:  ${getScriptDir("global", ctx.cwd)}`,
        ].join("\n"),
        connectionMsg.startsWith("✓") ? "success" : "error"
      );
    },
  });

  // ── Tool: freecad_run ──────────────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_run",
    label: "FreeCAD Run",
    description:
      "Execute Python code in the running FreeCAD instance. " +
      "Returns stdout output, result value, stderr, and any error traceback. " +
      "FreeCAD modules (Part, Sketcher, etc.) are NOT pre-imported — always add import statements. " +
      "App and FreeCAD are available without import. " +
      "Use for any Python code: single expressions, property reads, or multi-line geometry scripts. " +
      "To run a previously saved script by name, use freecad_script_run instead.",
    parameters: Type.Object({
      code: Type.String({
        description: "Python code or expression to execute inside FreeCAD",
      }),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const host = detectHost();
      const port = getPort();
      try {
        const resp = await sendToFreeCAD(host, port, params.code);
        const text = formatResponse(resp);
        const isError = !!resp.error;
        return {
          content: [{ type: "text" as const, text }],
          details: resp,
          isError,
        };
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        ctx.ui.setStatus("freecad", "⬡ FreeCAD offline");
        return {
          content: [{ type: "text" as const, text: `Connection error: ${msg}\nMake sure freecad_server.py is running as a macro in FreeCAD.` }],
          isError: true,
        };
      }
    },
  });

  // ── Tool: freecad_screenshot ───────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_screenshot",
    label: "FreeCAD Screenshot",
    description:
      "Save a PNG screenshot of the active FreeCAD 3D view. " +
      "The path must be a valid Windows path (FreeCAD runs on Windows). " +
      "Use forward slashes or double backslashes.",
    parameters: Type.Object({
      windows_path: Type.Optional(
        Type.String({
          description: "Windows file path for the PNG, e.g. C:/Users/Public/fc_check.png. Defaults to C:/Users/Public/fc_screenshot.png",
        })
      ),
    }),
    async execute(_id, params, _signal, _onUpdate, _ctx) {
      const winPath = (params.windows_path ?? "C:/Users/Public/fc_screenshot.png")
        .replace(/\\/g, "/")   // normalise backslashes → forward slashes
        .replace(/'/g, "\\'");       // escape single quotes for Python string safety
      const code = `FreeCADGui.ActiveDocument.ActiveView.saveImage('${winPath}', 1920, 1080)\nprint('Screenshot saved: ${winPath}')`;
      const host = detectHost();
      const port = getPort();
      try {
        const resp = await sendToFreeCAD(host, port, code);
        const text = formatResponse(resp);
        return {
          content: [{ type: "text" as const, text }],
          details: { path: winPath, response: resp },
          isError: !!resp.error,
        };
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text" as const, text: `Connection error: ${msg}` }],
          isError: true,
        };
      }
    },
  });

  // ── Tool: freecad_script_save ──────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_script_save",
    label: "FreeCAD Save Script",
    description:
      "Save a Python script to the FreeCAD script library for later reuse. " +
      "Project scope saves to <cwd>/fc-scripts/ (per-project, can be git-tracked). " +
      "Global scope saves to ~/.pi/freecad-scripts/ (cross-project reuse). " +
      "If a script with the same name already exists it will be overwritten. " +
      "Use descriptive names: part_box_with_holes, util_validate_model, etc.",
    parameters: Type.Object({
      name: Type.String({
        description: "Script name (snake_case). Used as filename and lookup key.",
      }),
      description: Type.String({
        description: "One-line description of what the script does and when to use it.",
      }),
      code: Type.String({
        description: "Complete Python script content.",
      }),
      scope: Type.Optional(
        Type.Union([Type.Literal("project"), Type.Literal("global")], {
          description: "project (default) or global. Use global for reusable utilities.",
        })
      ),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const scope = params.scope ?? "project";
      try {
        const { file, dir } = saveScript(
          params.name,
          params.description,
          params.code,
          scope,
          ctx.cwd
        );
        return {
          content: [
            {
              type: "text" as const,
              text: `Saved: ${file}\nLocation: ${path.join(dir, file)}\nScope: ${scope}\nDescription: ${params.description}`,
            },
          ],
          details: { file, dir, scope },
        };
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text" as const, text: `Failed to save script: ${msg}` }],
          isError: true,
        };
      }
    },
  });

  // ── Tool: freecad_script_list ──────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_script_list",
    label: "FreeCAD List Scripts",
    description:
      "List all available scripts in the FreeCAD script library. " +
      "Shows name, scope (project/global), description, and last modified date.",
    parameters: Type.Object({
      scope: Type.Optional(
        Type.Union([Type.Literal("project"), Type.Literal("global"), Type.Literal("all")], {
          description: "Filter by scope. Defaults to all.",
        })
      ),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const filterScope = params.scope ?? "all";

      let scripts: ScriptEntry[];
      if (filterScope === "all") {
        // Deduplicated: project takes precedence over global on name collision
        scripts = listAllScripts(ctx.cwd);
      } else {
        // Explicit scope: query only that scope, no deduplication
        const dir = getScriptDir(filterScope, ctx.cwd);
        scripts = loadIndex(dir).map((e) => ({ ...e, scope: filterScope }));
      }

      if (scripts.length === 0) {
        return {
          content: [{ type: "text" as const, text: "No scripts found in library." }],
          details: { scripts: [] },
        };
      }

      const lines = scripts.map((s) => {
        const modified = s.modified.slice(0, 10);
        return `[${s.scope}] ${s.name.padEnd(30)} ${modified}  ${s.description}`;
      });

      return {
        content: [
          {
            type: "text" as const,
            text: `Found ${scripts.length} script(s):\n\n${lines.join("\n")}`,
          },
        ],
        details: { scripts },
      };
    },
  });

  // ── Tool: freecad_script_run ───────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_script_run",
    label: "FreeCAD Run Script",
    description:
      "Execute a named script from the FreeCAD script library in the running FreeCAD instance. " +
      "Project scripts take precedence over global scripts with the same name. " +
      "Use freecad_script_list to see available scripts.",
    parameters: Type.Object({
      name: Type.String({
        description: "Script name as shown by freecad_script_list.",
      }),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const found = findScript(params.name, ctx.cwd);
      if (!found) {
        return {
          content: [{ type: "text" as const, text: `Script not found: "${params.name}". Use freecad_script_list to see available scripts.` }],
          isError: true,
        };
      }

      const host = detectHost();
      const port = getPort();
      try {
        const resp = await sendToFreeCAD(host, port, found.code, 30000);
        const text = `Running [${found.entry.scope}] ${found.entry.name}\n\n${formatResponse(resp)}`;
        return {
          content: [{ type: "text" as const, text }],
          details: { script: found.entry, response: resp },
          isError: !!resp.error,
        };
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        return {
          content: [{ type: "text" as const, text: `Connection error: ${msg}` }],
          isError: true,
        };
      }
    },
  });

  // ── Tool: freecad_script_show ──────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_script_show",
    label: "FreeCAD Show Script",
    description: "Print the source code of a named script from the library.",
    parameters: Type.Object({
      name: Type.String({ description: "Script name." }),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const found = findScript(params.name, ctx.cwd);
      if (!found) {
        return {
          content: [{ type: "text" as const, text: `Script not found: "${params.name}"` }],
          isError: true,
        };
      }
      return {
        content: [
          {
            type: "text" as const,
            text: `# [${found.entry.scope}] ${found.entry.name}\n# ${found.entry.description}\n# Modified: ${found.entry.modified}\n\n${found.code}`,
          },
        ],
        details: { entry: found.entry },
      };
    },
  });

  // ── Tool: freecad_script_delete ────────────────────────────────────────────

  pi.registerTool({
    name: "freecad_script_delete",
    label: "FreeCAD Delete Script",
    description: "Delete a named script from the library.",
    parameters: Type.Object({
      name: Type.String({ description: "Script name to delete." }),
      scope: Type.Optional(
        Type.Union([Type.Literal("project"), Type.Literal("global")], {
          description: "Which scope to delete from. If omitted, deletes from the first scope where the script is found (project first).",
        })
      ),
    }),
    async execute(_id, params, _signal, _onUpdate, ctx) {
      const slug = slugify(params.name);
      const scopes: Array<"project" | "global"> = params.scope
        ? [params.scope]
        : ["project", "global"];

      for (const scope of scopes) {
        const dir = getScriptDir(scope, ctx.cwd);
        const index = loadIndex(dir);
        const idx = index.findIndex((e) => e.name === slug);
        if (idx >= 0) {
          const entry = index[idx]!;
          const filePath = path.join(dir, entry.file);
          if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
          index.splice(idx, 1);
          saveIndex(dir, index);
          return {
            content: [{ type: "text" as const, text: `Deleted [${scope}] ${slug}` }],
            details: { name: slug, scope },
          };
        }
      }

      return {
        content: [{ type: "text" as const, text: `Script not found: "${params.name}"` }],
        isError: true,
      };
    },
  });

  // ── Setup Wizard ────────────────────────────────────────────────────────────

  pi.registerCommand("freecad:setup", {
    description: "Setup wizard: find FreeCAD, install server macro, configure firewall, verify connection",
    handler: async (_args, ctx) => {
      const port = getPort();
      const step = (n: number, total: number, msg: string) =>
        ctx.ui.setStatus("freecad", `⬡ Setup ${n}/${total}: ${msg}`);

      ctx.ui.notify(
        [
          "FreeCAD Remote — Setup Wizard",
          "This wizard will:",
          "  1. Detect your environment (WSL2 / Linux / macOS)",
          "  2. Find your FreeCAD installation",
          "  3. Install the server macro into FreeCAD's Macro folder",
          "  4. Configure the Windows firewall (WSL2 only)",
          "  5. Optionally configure FreeCAD autostart",
          "  6. Guide you to start the server and verify the connection",
        ].join("\n"),
        "info"
      );

      // ──────────────────────────────────────────────────────────
      // STEP 1 — Already connected?
      // ──────────────────────────────────────────────────────────
      step(1, 6, "Checking existing connection...");
      const host = detectHost();
      try {
        const resp = await sendToFreeCAD(host, port, "'.'.join(FreeCAD.Version()[:2])", 3000);
        const version = resp.result ?? "?";
        ctx.ui.setStatus("freecad", `⬡ FreeCAD ${host}:${port}`);
        ctx.ui.notify(
          `✓ FreeCAD ${version} is already connected at ${host}:${port}\nSetup is not needed. Use /freecad:status for details.`,
          "success"
        );
        return;
      } catch {
        // Not connected — proceed with setup
      }

      // ──────────────────────────────────────────────────────────
      // STEP 2 — Detect environment
      // ──────────────────────────────────────────────────────────
      step(2, 6, "Detecting environment...");

      let isWSL2 = false;
      let windowsDrives: string[] = [];
      let windowsUser: string | null = null;

      try {
        const procVersion = fs.readFileSync("/proc/version", "utf8").toLowerCase();
        isWSL2 = procVersion.includes("microsoft");
      } catch { /* not Linux */ }

      if (isWSL2) {
        try {
          windowsDrives = fs.readdirSync("/mnt")
            .filter(d => /^[a-z]$/.test(d) && fs.statSync(`/mnt/${d}`).isDirectory());
        } catch { /* /mnt not available */ }

        // Detect Windows username via /mnt/c/Users
        const cDrive = windowsDrives.includes("c") ? "/mnt/c" : `/mnt/${windowsDrives[0]}`;
        try {
          const users = fs.readdirSync(`${cDrive}/Users`)
            .filter(u => !["Public", "Default", "All Users", "Default User"].includes(u)
              && fs.statSync(`${cDrive}/Users/${u}`).isDirectory());
          windowsUser = users[0] ?? null;
        } catch { /* cannot read Users */ }
      }

      const envLabel = isWSL2
        ? `WSL2 — Windows drives: ${windowsDrives.map(d => d + ":").join(" ")}${
            windowsUser ? `  |  Windows user: ${windowsUser}` : ""}`
        : "Native Linux / macOS (no Windows filesystem access)";

      ctx.ui.notify(`Environment: ${envLabel}`, "info");

      // ──────────────────────────────────────────────────────────
      // STEP 3 — Find FreeCAD + macro directory
      // ──────────────────────────────────────────────────────────
      step(3, 6, "Finding FreeCAD...");

      let macroDir: string | null = null;
      let freecadFound = false;

      if (isWSL2 && windowsDrives.length > 0 && windowsUser) {
        // Search common Windows install locations
        const cDrive = windowsDrives.includes("c") ? "/mnt/c" : `/mnt/${windowsDrives[0]}`;
        const searchDirs = [
          `${cDrive}/Program Files`,
          `${cDrive}/Program Files (x86)`,
          `${cDrive}/Users/${windowsUser}/AppData/Local/Programs`,
          `${cDrive}/Users/${windowsUser}/AppData/Local`,
        ];

        const fcInstalls: string[] = [];
        for (const dir of searchDirs) {
          try {
            const entries = fs.readdirSync(dir).filter(e =>
              e.toLowerCase().startsWith("freecad") &&
              fs.statSync(path.join(dir, e)).isDirectory()
            );
            fcInstalls.push(...entries.map(e => path.join(dir, e)));
          } catch { /* dir doesn't exist */ }
        }

        if (fcInstalls.length > 0) {
          freecadFound = true;
          const chosen = fcInstalls.length === 1
            ? fcInstalls[0]!
            : await ctx.ui.select("Multiple FreeCAD installations found:", fcInstalls);

          if (chosen) {
            ctx.ui.notify(`Found FreeCAD at: ${chosen}`, "success");
          }
        }

        // Find / create macro directory
        const macroCandidates = [
          `${cDrive}/Users/${windowsUser}/AppData/Roaming/FreeCAD/Macro`,
          `${cDrive}/Users/${windowsUser}/Documents/FreeCAD/Macro`,
        ];

        for (const candidate of macroCandidates) {
          if (fs.existsSync(candidate)) {
            macroDir = candidate;
            break;
          }
        }

        // Create the standard Roaming/FreeCAD/Macro if none found
        if (!macroDir) {
          const defaultMacroDir = `${cDrive}/Users/${windowsUser}/AppData/Roaming/FreeCAD/Macro`;
          try {
            fs.mkdirSync(defaultMacroDir, { recursive: true });
            macroDir = defaultMacroDir;
            ctx.ui.notify(`Created macro directory: ${defaultMacroDir}`, "info");
          } catch (e) {
            ctx.ui.notify(`Could not create macro directory: ${e}`, "error");
          }
        }
      }

      if (!freecadFound) {
        ctx.ui.notify(
          isWSL2
            ? "FreeCAD installation not found in standard locations."
            : "Cannot search Windows filesystem (not in WSL2).",
          "info"
        );
      }

      // ──────────────────────────────────────────────────────────
      // STEP 4 — Install server macro
      // ──────────────────────────────────────────────────────────
      step(4, 6, "Installing server macro...");

      // Source: relative to cwd (assumes standard project layout)
      const serverSrc = path.join(ctx.cwd, ".pi/skills/freecad-remote/server/freecad_server.py");
      let macroInstalled = false;
      let macroTargetDisplay = "";

      if (macroDir && fs.existsSync(serverSrc)) {
        const target = path.join(macroDir, "freecad_server.py");
        try {
          fs.copyFileSync(serverSrc, target);
          macroInstalled = true;
          macroTargetDisplay = target;
          ctx.ui.notify(`✓ Server macro installed:\n  ${target}`, "success");
        } catch (e) {
          ctx.ui.notify(`Could not copy macro: ${e}`, "error");
        }
      } else if (!fs.existsSync(serverSrc)) {
        ctx.ui.notify(
          `Server script not found at expected path:\n  ${serverSrc}\n` +
          "Ensure you are running pi from the freecad-skill project directory.",
          "error"
        );
      } else {
        // macroDir is null — give manual instructions
        const winPath = serverSrc.replace(/^\/mnt\/([a-z])/, (_, d) => `${d.toUpperCase()}:`);
        ctx.ui.notify(
          `Could not determine FreeCAD macro folder.\n` +
          `Please copy the server script manually:\n` +
          `  Source: ${winPath}\n` +
          `  Destination: C:\\Users\\<you>\\AppData\\Roaming\\FreeCAD\\Macro\\`,
          "info"
        );
      }

      // ──────────────────────────────────────────────────────────
      // STEP 5 — Firewall rule (WSL2 only)
      // ──────────────────────────────────────────────────────────
      step(5, 6, "Configuring firewall...");

      if (isWSL2) {
        // Check if powershell.exe is available
        const psCheck = await pi.exec("which", ["powershell.exe"], { timeout: 3000 }).catch(() => ({ code: 1 }));
        const hasPS = (psCheck as { code: number }).code === 0;

        if (hasPS) {
          // Check if rule already exists
          const checkRule = await pi.exec(
            "powershell.exe",
            ["-Command", `Get-NetFirewallRule -DisplayName 'FreeCAD Remote Server' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Enabled`],
            { timeout: 8000 }
          ).catch(() => ({ stdout: "", code: 1 })) as { stdout: string; code: number };

          if (checkRule.stdout.trim().toLowerCase() === "true") {
            ctx.ui.notify("✓ Firewall rule already exists for port 7978", "success");
          } else {
            const wantFirewall = await ctx.ui.confirm(
              "Firewall Setup",
              `Allow FreeCAD server on port ${port}?\n` +
              "This requires administrator privileges in Windows.\n" +
              "A UAC prompt may appear."
            );

            if (wantFirewall) {
              const fw = await pi.exec(
                "powershell.exe",
                [
                  "-Command",
                  `Start-Process powershell -Verb RunAs -Wait -ArgumentList "-Command New-NetFirewallRule -DisplayName 'FreeCAD Remote Server' -Direction Inbound -Protocol TCP -LocalPort ${port} -Action Allow"`
                ],
                { timeout: 30000 }
              ).catch((e: unknown) => ({ code: 1, stderr: String(e) })) as { code: number; stderr?: string };

              if (fw.code === 0) {
                ctx.ui.notify("✓ Firewall rule created for port " + port, "success");
              } else {
                ctx.ui.notify(
                  `Firewall rule could not be created automatically.\n` +
                  `Run this in Windows PowerShell as Administrator:\n\n` +
                  `  New-NetFirewallRule -DisplayName 'FreeCAD Remote Server' \\\n` +
                  `    -Direction Inbound -Protocol TCP -LocalPort ${port} -Action Allow`,
                  "info"
                );
              }

              // Portproxy: WSL2 NAT mode needs this even with firewall rule
              // Forwards traffic arriving on the WSL2 gateway IP to Windows localhost
              const proxy = await pi.exec(
                "powershell.exe",
                ["-Command",
                  `netsh interface portproxy add v4tov4 listenport=${port} listenaddress=0.0.0.0 connectport=${port} connectaddress=127.0.0.1`
                ],
                { timeout: 10000 }
              ).catch(() => ({ code: 1 })) as { code: number };
              if (proxy.code === 0) {
                ctx.ui.notify("✓ Portproxy configured (WSL2 NAT mode)", "success");
              } else {
                ctx.ui.notify(
                  `Portproxy could not be set automatically.\n` +
                  `If connection fails, run as Administrator:\n\n` +
                  `  netsh interface portproxy add v4tov4 listenport=${port} listenaddress=0.0.0.0 connectport=${port} connectaddress=127.0.0.1`,
                  "info"
                );
              }
            }
          }
        } else {
          ctx.ui.notify(
            `powershell.exe not accessible from WSL2.\n` +
            `Run setup_firewall.ps1 manually in Windows PowerShell as Administrator.`,
            "info"
          );
        }
      } else {
        ctx.ui.notify("Not in WSL2 — skipping Windows firewall setup.", "info");
      }

      // ──────────────────────────────────────────────────────────
      // Optional: Autostart via InitGui.py
      // ──────────────────────────────────────────────────────────
      if (macroInstalled && macroDir) {
        const wantAutostart = await ctx.ui.confirm(
          "Autostart",
          "Configure FreeCAD to start the server automatically at launch?\n" +
          "This writes a small snippet to FreeCAD's InitGui.py."
        );

        if (wantAutostart) {
          const initGuiPath = path.join(path.dirname(macroDir), "InitGui.py");
          const snippet = [
            "",
            "# FreeCAD Remote Server — auto-start (added by pi setup wizard)",
            "import os as _fc_os",
            `_fc_macro = _fc_os.path.join(_fc_os.path.dirname(__file__), 'Macro', 'freecad_server.py')`,
            "if _fc_os.path.exists(_fc_macro):",
            "    exec(open(_fc_macro).read())",
            "del _fc_os, _fc_macro",
            "",
          ].join("\n");

          const MARKER = "# FreeCAD Remote Server — auto-start";
          try {
            const existing = fs.existsSync(initGuiPath) ? fs.readFileSync(initGuiPath, "utf8") : "";
            if (!existing.includes(MARKER)) {
              fs.writeFileSync(initGuiPath, existing + snippet, "utf8");
              ctx.ui.notify(`✓ Autostart configured:\n  ${initGuiPath}`, "success");
            } else {
              ctx.ui.notify("Autostart already configured in InitGui.py", "info");
            }
          } catch (e) {
            ctx.ui.notify(`Could not write InitGui.py: ${e}\nAutostart not configured.`, "error");
          }
        }
      }

      // ──────────────────────────────────────────────────────────
      // STEP 6 — User instructions + wait for connection
      // ──────────────────────────────────────────────────────────
      step(6, 6, "Waiting for FreeCAD...");

      const macroFileName = "freecad_server.py";
      const instructions = macroInstalled
        ? [
            "─── ACTION REQUIRED — Start the FreeCAD server ───",
            "",
            "1. Open FreeCAD on Windows",
            "2. Go to:  Extras → Makros → Makro ausführen…",
            "          (or:  Tools → Macros → Execute Macro…)",
            `3. Select:  ${macroFileName}`,
            "4. Click:  Execute / Ausführen",
            "",
            "FreeCAD console should show:",
            "  FreeCAD-Server gestartet auf 0.0.0.0:7978",
            "",
            "Waiting up to 90 seconds for the connection...",
          ]
        : [
            "─── ACTION REQUIRED — Manual setup ───",
            "",
            "1. Copy the server script into your FreeCAD Macro folder:",
            `     .pi/skills/freecad-remote/server/freecad_server.py`,
            `     → C:\\Users\\<you>\\AppData\\Roaming\\FreeCAD\\Macro\\`,
            "",
            "2. Open FreeCAD → Extras → Makros → Makro ausführen…",
            "3. Select freecad_server.py → Execute",
            "",
            "Waiting up to 90 seconds for the connection...",
          ];

      ctx.ui.notify(instructions.join("\n"), "info");

      // Poll for connection
      const deadline = Date.now() + 90_000;
      const pollInterval = 2000;
      let connected = false;

      while (Date.now() < deadline) {
        await new Promise(r => setTimeout(r, pollInterval));
        const remaining = Math.ceil((deadline - Date.now()) / 1000);
        ctx.ui.setStatus("freecad", `⬡ Waiting for FreeCAD… ${remaining}s`);

        try {
          const resp = await sendToFreeCAD(host, port, "'.'.join(FreeCAD.Version()[:2])", 3000);
          const version = resp.result ?? "?";
          ctx.ui.setStatus("freecad", `⬡ FreeCAD ${host}:${port}`);
          ctx.ui.notify(
            [
              `✓ Connected! FreeCAD ${version} at ${host}:${port}`,
              "",
              "Setup complete. You can now use:",
              "  freecad_run       — execute Python in FreeCAD",
              "  freecad_screenshot — capture 3D view",
              "  freecad_script_*  — manage script library",
              "  /freecad:status   — check status anytime",
            ].join("\n"),
            "success"
          );
          connected = true;
          break;
        } catch {
          // Still waiting...
        }
      }

      if (!connected) {
        ctx.ui.setStatus("freecad", "⬡ FreeCAD offline");
        ctx.ui.notify(
          [
            "✗ Connection timed out after 90 seconds.",
            "",
            "Troubleshooting:",
            "  • Confirm FreeCAD console shows: FreeCAD-Server gestartet auf 0.0.0.0:7978",
            `  • Check firewall: port ${port} TCP inbound must be allowed`,
            `  • Try: FC_HOST=<windows-ip> /freecad:setup`,
            "  • Run manually: python3 cli/fc.py status",
          ].join("\n"),
          "error"
        );
      }
    },
  });
}
