import type React from "react";
import { forwardRef } from "react";
import SvgHive from "./Hive";

export const HiveIcon = forwardRef<SVGSVGElement, React.PropsWithChildren<{}>>(
  (props, ref) => {
    return <SvgHive ref={ref} {...props} />;
  },
);
