import { UserPlus, Users } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

export default function TeamPage() {
  const { t } = useTranslation();

  return (
    <div className="h-full flex flex-col items-center justify-center py-20 px-8">
      <div className="rounded-full bg-muted p-6 mb-6">
        <Users className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-xl font-semibold mb-3">{t("spaces.team.title")}</h3>
      <p className="text-muted-foreground text-center max-w-md mb-8 text-base">
        {t("spaces.team.description")}
      </p>
      <Button size="lg">
        <UserPlus className="mr-2 h-5 w-5" />
        {t("spaces.team.inviteMembers")}
      </Button>
    </div>
  );
}
