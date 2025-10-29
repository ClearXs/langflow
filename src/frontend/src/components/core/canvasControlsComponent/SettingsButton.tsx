import { useNavigate } from "react-router-dom";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";

const SettingsButton = () => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate("/settings/datasources");
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      className="group flex items-center justify-center px-2 rounded-none"
      title="Settings"
      onClick={handleClick}
    >
      <IconComponent
        name="Settings"
        aria-hidden="true"
        className="text-muted-foreground group-hover:text-primary !h-5 !w-5"
      />
    </Button>
  );
};

export default SettingsButton;
