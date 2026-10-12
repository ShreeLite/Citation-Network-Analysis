// Precomputed data from analysis/run_all.py (bundled at build time so the site works from file://).
import papersJson from "./data/papers.json";
import preprintsJson from "./data/preprints.json";
import facultyJson from "./data/faculty.json";
import coauthorJson from "./data/coauthor_graph.json";
import citationGraphJson from "./data/citation_graph.json";
import requiredJson from "./data/required.json";
import collaborationJson from "./data/collaboration.json";
import centralJson from "./data/central.json";
import findingsJson from "./data/findings.json";
import indianJson from "./data/indian.json";
import metaJson from "./data/meta.json";

export type Inst = "IIIT-H" | "IIIT-D";
export const INSTS: Inst[] = ["IIIT-H", "IIIT-D"];

export interface Paper {
  paper_id: string; title: string; year: number; type: "journal" | "conference" | "preprint";
  journal_name?: string; acronym?: string; doi?: string | null; citations?: number | null;
  quartile?: string; core_rank?: string; field?: string; subfield?: string;
  our_institutions: string; faculty?: string[]; cites_indian_inst?: boolean; cited_by_indian_inst?: boolean;
}
export interface Faculty {
  faculty_id: string; name: string; institution: Inst; unit: string; units_secondary: string; designation: string; status: string;
  joining_year?: string; papers: number; journal: number; conference: number; citations: number; h_index_dataset: number;
  h_index_lifetime?: number | null; top_venue: string; q1: number; core_astar_a: number; per_year: Record<string, number>;
  fields: Record<string, number>; venues: Record<string, number>; degree?: number; degree_internal?: number;
  weighted_degree?: number; betweenness?: number; betweenness_internal?: number; community?: string;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export const papers = papersJson as unknown as Paper[];
export const preprints = preprintsJson as unknown as Paper[];
export const faculty = facultyJson as unknown as Faculty[];
export const coauthor = coauthorJson as any;
export const citationGraph = citationGraphJson as any;
export const required = requiredJson as any;
export const collaboration = collaborationJson as any;
export const central = centralJson as any;
export const findings = findingsJson as any;
export const indian = indianJson as any;
export const meta = metaJson as any;

export const facultyById: Record<string, Faculty> = Object.fromEntries(faculty.map((f) => [f.faculty_id, f]));
export const PARTIAL_YEAR: number = meta.partial_year ?? 2026;
export const YEAR_MIN: number = meta.year_start ?? 2016;
export const YEAR_MAX: number = meta.year_end ?? 2026;
