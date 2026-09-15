export type ExtractIdTaskInput = {
  imageUrl: string;
  instruction: string;
  idempotencyKey?: string;
};

export type ExtractIdTaskResult = {
  firstName: string;
  lastName: string;
  dob: string;
  driverLicenceNumber: string;
};

export type TaskRunRequest = {
  task: "extract_id";
  input: ExtractIdTaskInput;
};

export type TaskRunErrorShape = {
  code: string;
  message: string;
  retriable: boolean;
};

export type TaskRunMeta = {
  requestId: string;
  provider: string;
  cached: boolean;
  idempotencyKey: string;
  durationMs: number;
  createdAt: string;
};

export type TaskRunResponse = {
  status: boolean;
  message: string;
  task: "extract_id";
  result: ExtractIdTaskResult | null;
  meta: TaskRunMeta;
  errors: TaskRunErrorShape[];
};
