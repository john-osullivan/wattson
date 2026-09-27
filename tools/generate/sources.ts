// Load the hand-edited YAML sources and derive the closed vocabularies.
// This is the only layer that touches schemas/etk/ on disk.

import { readFileSync } from "node:fs";
import { parse } from "yaml";
import type { AliasEntry, Sources } from "./dialect.js";

export interface OntologyRaw {
  version: number;
  axes: Record<string, { values: string[] }>;
  areas: Record<string, unknown>;
  aliases: Record<string, { aliases: string[]; tags: string[] }>;
}

export interface RelationsRaw {
  version: number;
  relations: string[];
  policy?: string[];
}

export function loadYaml<T>(path: string): T {
  return parse(readFileSync(path, "utf8")) as T;
}

/**
 * Closed tag enum: every axis value (`<axis>/<value>`) plus every node and
 * leaf of the Area tree (`area/<path>`). A leading "#" is stripped: frontmatter
 * tags are stored without it (see wattson-handoff/reference/02 §6 example).
 */
export function deriveTags(ontology: OntologyRaw): string[] {
  const tags = new Set<string>();
  for (const [axis, spec] of Object.entries(ontology.axes)) {
    for (const value of spec.values) tags.add(`${axis}/${value}`);
  }
  const walk = (node: Record<string, unknown>, path: string[]) => {
    for (const [key, child] of Object.entries(node)) {
      const here = [...path, key];
      tags.add(`area/${here.join("/")}`);
      if (Array.isArray(child)) {
        for (const leaf of child) tags.add(`area/${[...here, leaf].join("/")}`);
      } else if (child && typeof child === "object") {
        walk(child as Record<string, unknown>, here);
      }
    }
  };
  walk(ontology.areas, []);
  return [...tags].sort();
}

/** Relation-type vocabulary, in authored order. */
export function deriveRelationTypes(relations: RelationsRaw): string[] {
  return relations.relations.slice();
}

/** Alias index with leading "#" stripped so entries match the tag enum. */
export function deriveAliasIndex(ontology: OntologyRaw): AliasEntry[] {
  return Object.entries(ontology.aliases).map(([term, entry]) => ({
    term,
    aliases: entry.aliases.slice(),
    tags: entry.tags.map((t) => t.replace(/^#/, "")),
  }));
}

/** Read all five ETK sources and derive the closed vocabularies. */
export function loadSources(etkDir: string): Sources {
  const p = (f: string) => `${etkDir}/${f}`;
  const notes = loadYaml<Sources["notes"]>(p("notes.yaml"));
  const proposal = loadYaml<Sources["proposal"]>(p("proposal.yaml"));
  const ontology = loadYaml<OntologyRaw>(p("ontology.yaml"));
  const relations = loadYaml<RelationsRaw>(p("relations.yaml"));
  // note-types.yaml: parsed for presence only (human reference; not
  // machine-consumed in v1 per schemas/etk/README.md).
  loadYaml(p("note-types.yaml"));
  return {
    notes,
    proposal,
    tags: deriveTags(ontology),
    relationTypes: deriveRelationTypes(relations),
    aliasIndex: deriveAliasIndex(ontology),
  };
}
