import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

type Variant = "default" | "outline" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  default: "bg-green-600 text-white hover:bg-green-700",
  outline: "border border-neutral-300 text-neutral-700 hover:bg-neutral-100",
  ghost: "text-neutral-600 hover:bg-neutral-100",
  danger: "bg-red-600 text-white hover:bg-red-700",
};

export function Button({
  className,
  variant = "default",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
