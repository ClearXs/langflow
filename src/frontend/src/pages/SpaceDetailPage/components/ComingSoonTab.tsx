import { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface ComingSoonTabProps {
  title: string;
  description: string;
  icon: ReactNode;
}

export function ComingSoonTab({
  title,
  description,
  icon,
}: ComingSoonTabProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-md">
        {description}
      </p>
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
        {t("spaces.documents.coming_soon")}
      </div>
    </div>
  );
}
