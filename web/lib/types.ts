export interface Brief {
  brand: string;
  product: string;
  audience: string;
  tone: string;
  goal: string;
}

export type VariantType = "headline" | "body" | "cta";

export interface Scores {
  hook_strength: number;
  brand_alignment: number;
  clarity: number;
  conversion_intent: number;
  weighted_average: number;
  rationale?: string;
}

export interface Output {
  variant_type: VariantType;
  content: string;
  scores: Scores;
}

export interface Feedback {
  promoted_to_golden: string[];
  flagged_for_review: string[];
  golden_threshold: number;
  flag_threshold: number;
}

export interface RunResponse {
  run_id: number;
  brief: Brief;
  prompt_version: string;
  retrieved_count: number;
  retrieved_examples: number;
  outputs: Output[];
  feedback: Feedback;
}

export interface Stats {
  runs: number;
  golden: number;
  flagged: number;
}
