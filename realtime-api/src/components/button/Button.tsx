import React from 'react';
import { Icon } from 'react-feather';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label?: string;
  icon?: Icon;
  iconPosition?: 'start' | 'end';
  iconColor?: 'red' | 'green' | 'grey';
  iconFill?: boolean;
  buttonStyle?: 'regular' | 'action' | 'alert' | 'flush';
}

export function Button({
  label = 'Okay',
  icon = void 0,
  iconPosition = 'start',
  iconColor = void 0,
  iconFill = false,
  buttonStyle = 'regular',
  ...rest
}: ButtonProps) {
  const StartIcon = iconPosition === 'start' ? icon : null;
  const EndIcon = iconPosition === 'end' ? icon : null;

  const baseClasses = "flex items-center gap-2 font-mono text-xs font-normal border-none rounded-full px-6 min-h-[42px] transition-all duration-100 ease-in-out outline-none";
  
  const styleClasses = {
    regular: "bg-bgSecondary text-[#101010] hover:bg-[#d8d8d8] disabled:text-[#999]",
    action: "bg-[#101010] text-bgSecondary hover:bg-[#404040] disabled:text-[#999]",
    alert: "bg-red-600 text-bgSecondary hover:bg-red-600 disabled:text-[#999]",
    flush: "bg-transparent"
  }[buttonStyle];

  const iconColorClasses = iconColor ? {
    red: "text-[#cc0000]",
    green: "text-[#009900]",
    grey: "text-[#909090]"
  }[iconColor] : "";

  const iconClasses = "flex w-4 h-4";
  const startIconClasses = "flex -ml-2";
  const endIconClasses = "flex -mr-2";
  
  return (
    <button 
      className={`
        ${baseClasses} 
        ${styleClasses}
        ${!rest.disabled && 'cursor-pointer active:translate-y-[1px]'}
      `}
      {...rest}
    >
      {StartIcon && (
        <span className={`${iconClasses} ${startIconClasses} ${iconColorClasses}`}>
          <StartIcon className={iconFill ? "fill-current" : ""} />
        </span>
      )}
      <span>{label}</span>
      {EndIcon && (
        <span className={`${iconClasses} ${endIconClasses} ${iconColorClasses}`}>
          <EndIcon className={iconFill ? "fill-current" : ""} />
        </span>
      )}
    </button>
  );
}
