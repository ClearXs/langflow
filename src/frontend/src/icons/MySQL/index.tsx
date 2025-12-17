import type React from "react";
import { forwardRef } from "react";
import SvgMySQL from "./MySQL";

export const MySQLIcon = forwardRef<SVGSVGElement, React.PropsWithChildren<{}>>(
  (props, ref) => {
    return <SvgMySQL ref={ref} {...props} />;
  },
);
