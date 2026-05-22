export function sanitizeCompanyName(name: string | null | undefined): string {
  if (!name) return "";

  return name
    .normalize("NFKC")
    .replace(/[\u0000-\u001F\u007F-\u009F\uFFFD]/g, "")
    .replace(/[^\x20-\x7E]/g, " ")
    .replace(/\s+-\s+/g, " ")
    .replace(/\s+,/g, ",")
    .replace(/,/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatTickerCompanyLabel(ticker: string, companyName: string | null | undefined): string {
  const cleanedTicker = ticker.trim().toUpperCase();
  const cleanedCompany = sanitizeCompanyName(companyName);
  return cleanedCompany ? `${cleanedTicker} - ${cleanedCompany}` : cleanedTicker;
}
