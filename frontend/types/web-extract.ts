export type WebExtractInput = {
  url: string;
  prompt: string;
  idempotencyKey?: string;
};

export type WebExtractCommand = {
  attr: string;
  many: boolean;
  name: string;
  selector: string;
};

export type WebExtractResult = {
  commands: WebExtractCommand[];
  confidence: number;
  data: Record<string, unknown>;
  url: string;
};

export type WebExtractErrorShape = {
  code: string;
  message: string;
  retriable: boolean;
};

export type WebExtractMeta = {
  cached: boolean;
  createdAt: string;
  durationMs: number;
  idempotencyKey: string;
  provider: string;
  regionPasses: number;
  requestId: string;
  siteType: string;
  toolsUsed: string[];
  truncated: boolean;
  confidence: number;
  checkAttempts: number;
};

export type WebExtractResponse = {
  errors: WebExtractErrorShape[];
  message: string;
  meta: WebExtractMeta;
  result: WebExtractResult | null;
  status: boolean;
  task: "extract_page";
};
