import { auditSupplyChainRoles } from "./supplyChainRoleAudit";

export function supplyChainRoleAuditContractTest() {
  const overlap = auditSupplyChainRoles({
    controller: { key: "company:TSMC", label: "TSMC" },
    beneficiary: { key: "company:TSMC", label: "TSMC" },
  });
  const distinct = auditSupplyChainRoles({
    controller: { key: "company:AMAT", label: "Applied Materials" },
    beneficiary: { key: "company:MU", label: "Micron" },
  });

  return {
    roleOverlapDetected:
      overlap.hasOverlap
      && overlap.warning === "Role Overlap Detected"
      && overlap.displayController === "TSMC"
      && overlap.displayBeneficiary === "TSMC",
    distinctRolesDoNotWarn:
      !distinct.hasOverlap
      && distinct.warning === null
      && distinct.displayController === "Applied Materials"
      && distinct.displayBeneficiary === "Micron",
  };
}
