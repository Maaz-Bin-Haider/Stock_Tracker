/** The API checks eligibility again at save time; this state explains the form. */
export interface PurchaseLineEditState {
  id?: number;
  collected?: string;
  refunded?: string;
  can_correct?: boolean;
  correction_block_reason?: string;
}

export function purchaseLineEditState(line: PurchaseLineEditState) {
  const existing = line.id !== undefined;
  const receivedOrRefunded = Number(line.collected ?? "0") > 0 || Number(line.refunded ?? "0") > 0;
  const correctionLocked = existing && !(line.can_correct ?? !receivedOrRefunded);
  return {
    correctionLocked,
    ratesLocked: existing && receivedOrRefunded,
    reason: correctionLocked
      ? line.correction_block_reason || "Review this line's stock movements before correcting it."
      : "",
  };
}
