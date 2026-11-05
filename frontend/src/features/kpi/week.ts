const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 24 * 60 * 60 * 1000;
const DAYS_PER_WEEK = 7;

// Returns the week anchor from the URL when it is a real YYYY-MM-DD date, or undefined for this week.
export function readWeekDate(params: URLSearchParams) {
  const value = params.get("date");
  if (!value || !ISO_DATE_PATTERN.test(value)) return undefined;
  const time = Date.parse(`${value}T00:00:00Z`);
  return Number.isNaN(time) || new Date(time).toISOString().slice(0, 10) !== value ? undefined : value;
}

// Returns the Monday a whole number of weeks away from a week's Monday.
export function shiftWeek(startDate: string, weeks: number) {
  return new Date(Date.parse(`${startDate}T00:00:00Z`) + weeks * DAYS_PER_WEEK * DAY_MS).toISOString().slice(0, 10);
}
