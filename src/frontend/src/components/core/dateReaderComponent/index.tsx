import { convertUTCToLocalTimezone } from "@/utils/utils";

export default function DateReader({
  date: dateString,
}: {
  date: string;
}): JSX.Element {
  const formattedDate = convertUTCToLocalTimezone(dateString);

  return <span>{formattedDate}</span>;
}
