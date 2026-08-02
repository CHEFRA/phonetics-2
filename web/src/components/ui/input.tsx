import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "rounded-md border border-neutral-300 bg-white px-2.5 py-1.5 text-sm",
        "focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500",
        className,
      )}
      {...props}
    />
  );
}
