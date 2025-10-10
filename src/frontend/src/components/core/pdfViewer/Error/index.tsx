import { useMessageLocale } from "@/i18n/locale";
import IconComponent from "../../../common/genericIconComponent";

export default function ErrorComponent(): JSX.Element {
  const messageLocale = useMessageLocale()
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-muted">
      <div className="chat-alert-box">
        <span className="flex gap-2">
          <IconComponent name="FileX2" />
          <span className="langflow-chat-span">{messageLocale.PDF_LOAD_ERROR_TITLE}</span>
        </span>
        <br />
        <div className="langflow-chat-desc">
          <span className="langflow-chat-desc-span">{messageLocale.PDF_CHECK_FLOW} </span>
        </div>
      </div>
    </div>
  );
}
