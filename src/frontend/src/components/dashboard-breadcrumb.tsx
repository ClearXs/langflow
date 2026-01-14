"use client";

import { useQuery } from "@tanstack/react-query";
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

interface BreadcrumbItemInterface {
  label: string;
  href?: string;
}

export function DashboardBreadcrumb() {
  const { t } = useTranslation();
  const location = useLocation();
  const pathname = location.pathname;

  // Extract space ID and other segments from pathname
  const segments = pathname.split("/").filter(Boolean);
  const spaceId = segments[0] === "spaces" && segments[1] ? segments[1] : null;

  // TODO: Integrate with Langflow spaces API when available
  const { data: space } = useQuery({
    queryKey: ["spaces", spaceId],
    queryFn: async () => {
      // Placeholder for Langflow spaces API
      // Replace with actual API call when spaces are fully integrated
      return { id: spaceId, name: `Space ${spaceId}` };
    },
    enabled: !!spaceId,
  });

  // State to store document/flow title for breadcrumb
  const [itemTitle, setItemTitle] = useState<string | null>(null);

  // Fetch document/flow title when on detail pages
  useEffect(() => {
    // TODO: Implement title fetching based on Langflow routes
    // This is a placeholder for future integration
    if (segments.length > 2) {
      const itemId = segments[segments.length - 1];
      if (itemId && itemId !== "new") {
        // Placeholder - will be replaced with actual API calls
        setItemTitle(null);
      }
    }
  }, [segments]);

  // Parse the pathname to create breadcrumb items
  const generateBreadcrumbs = (path: string): BreadcrumbItemInterface[] => {
    const segments = path.split("/").filter(Boolean);
    const breadcrumbs: BreadcrumbItemInterface[] = [];

    // Root level routes
    if (segments[0] === "flows") {
      breadcrumbs.push({ label: t("common.flows") || "Flows", href: "/flows" });

      if (segments[1] && segments[1] !== "new") {
        breadcrumbs.push({ label: itemTitle || `Flow ${segments[1]}` });
      } else if (segments[1] === "new") {
        breadcrumbs.push({ label: t("flows.createNew") || "New Flow" });
      }
    } else if (segments[0] === "spaces") {
      breadcrumbs.push({
        label: t("common.spaces") || "Spaces",
        href: "/spaces",
      });

      if (segments[1]) {
        const spaceLabel = space?.name || `Space ${segments[1]}`;
        breadcrumbs.push({
          label: spaceLabel,
          href: `/spaces/${segments[1]}`,
        });

        // Handle space sub-sections
        if (segments[2]) {
          const section = segments[2];

          const sectionLabels: Record<string, string> = {
            chats: t("common.chats") || "Chats",
            documents: t("common.documents") || "Documents",
            connectors: t("common.connectors") || "Connectors",
            logs: t("common.logs") || "Logs",
            settings: t("common.settings") || "Settings",
          };

          const sectionLabel =
            sectionLabels[section] ||
            section.charAt(0).toUpperCase() + section.slice(1);

          if (segments[3]) {
            breadcrumbs.push({
              label: sectionLabel,
              href: `/spaces/${segments[1]}/${section}`,
            });

            if (segments[3] === "new") {
              breadcrumbs.push({ label: t("common.create") || "New" });
            } else {
              breadcrumbs.push({ label: itemTitle || segments[3] });
            }
          } else {
            breadcrumbs.push({ label: sectionLabel });
          }
        }
      }
    } else if (segments[0] === "settings") {
      breadcrumbs.push({
        label: t("common.settings") || "Settings",
        href: "/settings",
      });

      if (segments[1]) {
        const settingLabels: Record<string, string> = {
          "api-keys": "API Keys",
          "global-variables": "Global Variables",
          messages: "Messages",
        };

        const settingLabel = settingLabels[segments[1]] || segments[1];
        breadcrumbs.push({ label: settingLabel });
      }
    } else if (segments[0] === "components") {
      breadcrumbs.push({ label: t("components.title") || "Components" });
    } else if (segments[0] === "store") {
      breadcrumbs.push({ label: t("store.title") || "Store", href: "/store" });
    }

    return breadcrumbs;
  };

  const breadcrumbs = generateBreadcrumbs(pathname);

  if (breadcrumbs.length <= 1) {
    return null; // Don't show breadcrumbs for single-level navigation
  }

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {breadcrumbs.map((item, index) => (
          <React.Fragment key={index}>
            <BreadcrumbItem>
              {index === breadcrumbs.length - 1 ? (
                <BreadcrumbPage>{item.label}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink href={item.href}>{item.label}</BreadcrumbLink>
              )}
            </BreadcrumbItem>
            {index < breadcrumbs.length - 1 && <BreadcrumbSeparator />}
          </React.Fragment>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
