import React from "react";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-slate-900 text-white hover:bg-slate-800 active:bg-slate-950 border border-slate-900 shadow-xs",
  secondary: "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 border border-blue-600 shadow-xs",
  outline: "bg-white text-slate-700 hover:bg-slate-50 active:bg-slate-100 border border-slate-200/90 shadow-xs",
  ghost: "bg-transparent text-slate-600 hover:bg-slate-100/80 hover:text-slate-900",
  danger: "bg-rose-600 text-white hover:bg-rose-700 active:bg-rose-800 border border-rose-600 shadow-xs",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "text-xs px-2.5 py-1.5 rounded-md gap-1.5 font-medium",
  md: "text-xs px-3.5 py-2 rounded-lg gap-2 font-medium",
  lg: "text-sm px-4 py-2.5 rounded-lg gap-2.5 font-medium",
};

export const Button: React.FC<ButtonProps> = ({
  variant = "outline",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  children,
  disabled,
  className = "",
  ...rest
}) => {
  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center transition-colors disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...rest}
    >
      {isLoading ? (
        <Loader2 size={13} className="animate-spin" />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};

export default Button;
