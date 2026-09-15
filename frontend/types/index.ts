import { SVGProps } from "react";

export type IconSvgProps = SVGProps<SVGSVGElement> & {
  size?: number;
};

export type {
  ArchitectureLayer,
  BackendDomain,
  CacheScenario,
  DeliveryTrack,
  IntegrationSurface,
  NavItem,
  Principle,
  ProductArea,
  ProofMetric,
  QuickLink,
  SiteConfig,
  WorkflowStep,
  WorkspaceSignal,
} from "@/types/site";
export type {
  ExtractIdTaskInput,
  ExtractIdTaskResult,
  TaskRunErrorShape,
  TaskRunMeta,
  TaskRunRequest,
  TaskRunResponse,
} from "@/types/task";
