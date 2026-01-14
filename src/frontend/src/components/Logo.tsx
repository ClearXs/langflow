"use client";

import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

export const Logo = ({ className }: { className?: string }) => {
  return (
    <Link to="/">
      <img
        src="/icon-128.png"
        className={cn(className)}
        alt="logo"
        width={128}
        height={128}
      />
    </Link>
  );
};
