import type React from "react";
import { forwardRef } from "react";
import SvgNeo4j from "./Neo4j";

export const Neo4jIcon = forwardRef<SVGSVGElement, React.PropsWithChildren<{}>>(
  (props, ref) => {
    return <SvgNeo4j ref={ref} {...props} />;
  },
);
