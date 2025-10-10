import { useMessageLocale } from "@/i18n/locale";

export default function NoDataPdf(): JSX.Element {

  const messageLocale = useMessageLocale()

  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-muted">
      <div className="chat-alert-box">
        <span>
          📄 <span className="langflow-chat-span">{messageLocale.PDF_ERROR_TITLE}</span>
        </span>
        <br />
        <div className="langflow-chat-desc">
          <span className="langflow-chat-desc-span">{messageLocale.PDF_LOAD_ERROR} </span>
        </div>
      </div>
    </div>
  );
}
