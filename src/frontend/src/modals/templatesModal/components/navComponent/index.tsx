/*
 * @Author: dengchao dengchao
 * @Date: 2025-09-23 10:55:29
 * @LastEditors: dengchao dengchao
 * @LastEditTime: 2025-09-24 15:32:38
 * @FilePath: \frontend\src\modals\templatesModal\components\navComponent\index.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { convertTestName } from "@/components/common/storeCardComponent/utils/convert-test-name";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { cn } from "@/utils/utils";
import { useIsMobile } from "../../../../hooks/use-mobile";
import type { NavProps } from "../../../../types/templates/types";
import { useTranslation } from "react-i18next";

export function Nav({ categories, currentTab, setCurrentTab }: NavProps) {
  const isMobile = useIsMobile();
  const { t } = useTranslation();
  return (
    <Sidebar collapsible={isMobile ? "icon" : "none"} className="max-w-[230px]">
      <SidebarContent className="gap-0 p-2">
        <div
          className={cn("relative flex items-center gap-2 px-2 py-3 md:px-4")}
          data-testid="modal-title"
        >
          <SidebarTrigger
            className={cn(
              "flex h-8 shrink-0 items-center rounded-md text-lg font-semibold leading-none tracking-tight text-primary outline-none ring-ring transition-[margin,opa] duration-200 ease-linear focus-visible:ring-1 md:hidden [&>svg]:size-4 [&>svg]:shrink-0",
            )}
          />
          <div
            className={cn(
              "text-base-semibold flex h-8 shrink-0 items-center rounded-md leading-none tracking-tight text-primary outline-none ring-ring transition-[margin,opa] duration-200 ease-linear focus-visible:ring-1 [&>svg]:size-4 [&>svg]:shrink-0",
              "group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0",
            )}
          >
            {t("common.templates")}
          </div>
        </div>

        {categories.map((category, index) => (
          <SidebarGroup key={index}>
            <SidebarGroupLabel
              className={`${
                index === 0
                  ? "hidden"
                  : "mb-1 text-sm font-semibold text-muted-foreground"
              }`}
            >
              {category.title}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {category.items.map((link) => (
                  <SidebarMenuItem key={link.id}>
                    <SidebarMenuButton
                      onClick={() => setCurrentTab(link.id)}
                      isActive={currentTab === link.id}
                      data-testid={`side_nav_options_${link.title.toLowerCase().replace(/\s+/g, "-")}`}
                      tooltip={link.title}
                    >
                      <ForwardedIconComponent
                        name={link.icon}
                        className={`h-4 w-4 stroke-2 ${
                          currentTab === link.id
                            ? "text-accent-pink-foreground"
                            : "text-muted-foreground"
                        }`}
                      />
                      <span
                        data-testid={`category_title_${convertTestName(link.title)}`}
                      >
                        {link.title}
                      </span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
    </Sidebar>
  );
}
