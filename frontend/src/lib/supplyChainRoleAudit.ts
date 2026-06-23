export interface SupplyChainRoleIdentity {
  key: string | null | undefined;
  label: string | null | undefined;
}

export interface SupplyChainRoleAudit {
  hasOverlap: boolean;
  warning: "Role Overlap Detected" | null;
  displayController: string;
  displayBeneficiary: string;
}

function normalizeRoleKey(role: SupplyChainRoleIdentity): string {
  return String(role.key || role.label || "").trim().toUpperCase();
}

function displayRole(role: SupplyChainRoleIdentity): string {
  return String(role.label || role.key || "Unavailable").replace(/^company:/i, "").trim() || "Unavailable";
}

export function auditSupplyChainRoles(input: {
  controller: SupplyChainRoleIdentity;
  beneficiary: SupplyChainRoleIdentity;
}): SupplyChainRoleAudit {
  const controllerKey = normalizeRoleKey(input.controller);
  const beneficiaryKey = normalizeRoleKey(input.beneficiary);
  const hasOverlap = Boolean(controllerKey && beneficiaryKey && controllerKey === beneficiaryKey);

  return {
    hasOverlap,
    warning: hasOverlap ? "Role Overlap Detected" : null,
    displayController: displayRole(input.controller),
    displayBeneficiary: displayRole(input.beneficiary),
  };
}
