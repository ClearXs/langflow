/*
 * @Author: dengchao dengchao
 * @Date: 2025-09-23 10:55:29
 * @LastEditors: dengchao dengchao
 * @LastEditTime: 2025-09-24 15:36:10
 * @FilePath: \frontend\src\modals\templatesModal\components\GetStartedComponent\index.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import BaseModal from "@/modals/baseModal";
import useFlowsManagerStore from "@/stores/flowsManagerStore";
import type { CardData } from "@/types/templates/types";
import memoryChatbot from "../../../../assets/temp-pat-1.png";
import vectorRag from "../../../../assets/temp-pat-2.png";
import multiAgent from "../../../../assets/temp-pat-3.png";
import memoryChatbotHorizontal from "../../../../assets/temp-pat-m-1.png";
import vectorRagHorizontal from "../../../../assets/temp-pat-m-2.png";
import multiAgentHorizontal from "../../../../assets/temp-pat-m-3.png";

import TemplateGetStartedCardComponent from "../TemplateGetStartedCardComponent";
import { useTranslation } from "react-i18next";

export default function GetStartedComponent() {
  const examples = useFlowsManagerStore((state) => state.examples);
  const { t } = useTranslation();
  // Define the card data
  const cardData: CardData[] = [
    {
      bgImage: memoryChatbot,
      bgHorizontalImage: memoryChatbotHorizontal,
      icon: "MessagesSquare",
      category: "prompting",
      flow: examples.find((example) => example.name === "Basic Prompting"),
    },
    {
      bgImage: vectorRag,
      bgHorizontalImage: vectorRagHorizontal,
      icon: "Database",
      category: "RAG",
      flow: examples.find((example) => example.name === "Vector Store RAG"),
    },
    {
      bgImage: multiAgent,
      bgHorizontalImage: multiAgentHorizontal,
      icon: "Bot",
      category: "Agents",
      flow: examples.find((example) => example.name === "Simple Agent"),
    },
  ];

  return (
    <div className="flex flex-1 flex-col gap-4 md:gap-8">
      <BaseModal.Header description={t("common.startWithTemplatesShowcasingLangflowPromptingRAGAndAgentUseCases")}>
        {t("common.getStarted")}
      </BaseModal.Header>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-3">
        {cardData.map((card, index) => (
          <TemplateGetStartedCardComponent key={index} {...card} />
        ))}
      </div>
    </div>
  );
}
