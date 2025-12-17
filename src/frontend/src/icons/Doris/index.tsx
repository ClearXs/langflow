import type React from "react";
import { forwardRef } from "react";
import SvgDoris from "./Doris";

export const DorisIcon = forwardRef<SVGSVGElement, React.PropsWithChildren<{}>>(
  (props, ref) => {
    return <SvgDoris ref={ref} {...props} />;
  },
);
